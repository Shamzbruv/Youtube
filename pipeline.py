import os
import random
import subprocess
from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# Configuration
CLIP_DURATION = 27
MAX_CREATORS = 5
POST_TIMES = [14, 20]  # 2PM and 8PM UTC


def get_youtube_service(api_key=None):
    """Create YouTube service instance."""
    if api_key:
        return build("youtube", "v3", developerKey=api_key)
    creds = Credentials.from_authorized_user_info({
        "client_id": os.environ['YT_CLIENT_ID'],
        "client_secret": os.environ['YT_CLIENT_SECRET'],
        "refresh_token": os.environ['YT_REFRESH_TOKEN'],
        "token_uri": "https://oauth2.googleapis.com/token",
        "scopes": ["https://www.googleapis.com/auth/youtube.upload"]
    })
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("youtube", "v3", credentials=creds)


def find_viral_streams():
    """Return a list of live stream URLs with >10k viewers."""
    youtube = get_youtube_service(api_key=os.environ.get('YT_API_KEY'))
    TOP_GAMING_CREATORS = [
        "UCX6OQ3DkcsbYNE6H8uQQuVA",
        "UC9Z-xXb0tzX2FSCSDEnJ8eQ",  
        "UCYzPXWLvlOIdkpf5-a6s8rA",
        "UCBJycsmduvYEL83R_U4JriQ",
        "UCiP6wD_tYlYLYh3agzbByWQ"
    ]
    viral_streams = []
    for cid in TOP_GAMING_CREATORS:
        try:
            search = youtube.search().list(
                part="snippet", channelId=cid,
                eventType="live", type="video",
                order="viewCount", maxResults=1
            ).execute()
            items = search.get('items', [])
            if not items:
                continue
            vid = items[0]['id']['videoId']
            stats = youtube.videos().list(
                part="liveStreamingDetails", id=vid
            ).execute()
            viewers = int(stats['items'][0]['liveStreamingDetails'].get('concurrentViewers', 0))
            if viewers > 10000:
                viral_streams.append(f"https://youtu.be/{vid}")
        except Exception as e:
            print(f"⚠️ Couldn't check {cid}: {e}")
    return viral_streams[:MAX_CREATORS]


def create_short(stream_url):
    """Download, caption, and style a 90s clip."""
    print("🎬 Creating Short...")
    subprocess.run([
        'yt-dlp', '-f', 'best[height<=720]',
        '--download-sections', '*00:00:00-00:01:30',
        '-o', 'raw_clip', stream_url
    ], check=True)
    subprocess.run([
        'whisper', 'raw_clip.mp4', '--model', 'tiny',
        '--output_format', 'srt', '--language', 'en'
    ], check=True)
    subprocess.run([
        'ffmpeg', '-i', 'raw_clip.mp4',
        '-vf', (
            "subtitles=raw_clip.srt:"
            "force_style='Fontsize=24,PrimaryColour=&HFFFFFF,"
            "OutlineColour=&H000000,BorderStyle=1,Alignment=10'"
        ),
        '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
        '-c:a', 'copy', '-y', 'final_short.mp4'
    ], check=True)


def upload_short():
    """Upload the styled short to YouTube."""
    youtube = get_youtube_service()
    vid = os.environ.get('SOURCE_VIDEO_ID')
    snippet = youtube.videos().list(part="snippet", id=vid).execute()['items'][0]['snippet']
    channel = youtube.channels().list(
        part="snippet,statistics", id=snippet['channelId']
    ).execute()['items'][0]
    title = f"🔥 {channel['snippet']['title']} GOES VIRAL! #shorts"
    desc = (
        f"🚨 CREDIT: {channel['snippet']['title']} ("
        f"{channel['statistics'].get('subscriberCount', '0')} subs)\n"
        f"📺 Original: https://youtu.be/{vid}\n#shorts #gaming #viral"
    )
    publish_at = datetime.utcnow().replace(
        hour=random.choice(POST_TIMES), minute=30
    ).isoformat() + "Z"
    req = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {"title": title, "description": desc, "categoryId": "20"},
            "status": {"privacyStatus": "public", "publishAt": publish_at}
        },
        media_body=MediaFileUpload("final_short.mp4")
    )
    res = req.execute()
    print(f"✅ Uploaded! ID: {res['id']}")


if __name__ == "__main__":
    print("🔍 Finding trending streams...")
    streams = find_viral_streams()
    if not streams:
        print("⚠️ No trending streams found right now")
        exit(0)
    print(f"🎥 Found {len(streams)} streams")
    # Extract ID from youtu.be URL or watch?v=
    first_url = streams[0].rstrip('/')
    vid = first_url.split('/')[-1] if 'youtu.be/' in first_url else first_url.split('v=')[-1]
    os.environ['SOURCE_VIDEO_ID'] = vid
    create_short(streams[0])
    upload_short()
