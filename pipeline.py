import os
import json
import random
import subprocess
from datetime import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request

# Configuration
CLIP_DURATION = 27
MAX_CREATORS = 5
POST_TIMES = [14, 20]  # 2PM and 8PM UTC


def get_authenticated_service():
    """Handles authentication with proper credential refresh"""
    try:
        creds_file = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
        if creds_file and os.path.exists(creds_file):
            with open(creds_file) as f:
                creds_info = json.load(f)
                creds = Credentials.from_authorized_user_info(creds_info)
        else:
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

    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        raise


def find_viral_streams():
    # Force using API key only (no OAuth) by explicitly clearing credentials
    youtube = build(
        "youtube", "v3",
        developerKey=os.environ['YT_API_KEY'],
        credentials=None
    )

    TOP_GAMING_CREATORS = [
        "UCX6OQ3DkcsbYNE6H8uQQuVA",  # MrBeast Gaming
        "UC9Z-xXb0tzX2FSCSDEnJ8eQ",  # iShowSpeed
        "UCYzPXWLvlOIdkpf5-a6s8rA",  # CaseOh
        "UCBJycsmduvYEL83R_U4JriQ",  # Mongraal
        "UCiP6wD_tYlYLYh3agzbByWQ"   # TypicalGamer
    ]

    viral_streams = []
    for channel_id in TOP_GAMING_CREATORS:
        try:
            search = youtube.search().list(
                part="snippet",
                channelId=channel_id,
                eventType="live",
                type="video",
                order="viewCount",
                maxResults=1
            ).execute()

            if search.get('items'):
                video_id = search['items'][0]['id']['videoId']
                stats = youtube.videos().list(
                    part="liveStreamingDetails",
                    id=video_id
                ).execute()

                viewers = int(stats['items'][0]['liveStreamingDetails'].get('concurrentViewers', 0))
                if viewers > 10000:
                    viral_streams.append(f"https://youtu.be/{video_id}")

        except Exception as e:
            print(f"⚠️ Error checking {channel_id}: {e}")

    return viral_streams[:MAX_CREATORS]


def create_short(stream_url):
    print("🎬 Creating Short with captions...")

    # Download best 90s segment
    subprocess.run([
        'yt-dlp',
        '-f', 'best[height<=720]',
        '--download-sections', '*00:00:00-00:01:30',
        '--write-info-json',
        '-o', 'raw_clip',
        stream_url
    ], check=True)

    # Generate captions (Whisper AI)
    subprocess.run([
        'whisper',
        'raw_clip.mp4',
        '--model', 'tiny',
        '--output_format', 'srt',
        '--language', 'en'
    ], check=True)

    # Burn styled captions onto the clip
    subprocess.run([
        'ffmpeg',
        '-i', 'raw_clip.mp4',
        '-vf', (
            "subtitles=raw_clip.srt:"
            "force_style='Fontsize=24,"
            "PrimaryColour=&HFFFFFF,"
            "OutlineColour=&H000000,"
            "BorderStyle=1,Alignment=10'"
        ),
        '-c:v', 'libx264',
        '-preset', 'fast',
        '-crf', '23',
        '-c:a', 'copy',
        '-y',
        'final_short.mp4'
    ], check=True)


def upload_short():
    youtube = get_authenticated_service()

    source_id = os.environ.get('SOURCE_VIDEO_ID')
    # Fetch video snippet & channel stats
    snippet = youtube.videos().list(
        part="snippet",
        id=source_id
    ).execute()['items'][0]['snippet']
    channel_stats = youtube.channels().list(
        part="statistics",
        id=snippet['channelId']
    ).execute()['items'][0]['statistics']

    creator_title = snippet['channelTitle']
    sub_count = channel_stats.get('subscriberCount', '0')

    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": f"🔥 {creator_title} GOES VIRAL! #shorts",
                "description": (
                    f"🚨 CREDIT: {creator_title} ({sub_count} subs)\n"
                    f"📺 Original: https://youtu.be/{source_id}\n\n"
                    "💬 COMMENT your reaction!\n"
                    "👍 LIKE for more!\n"
                    "🔔 SUBSCRIBE!\n\n"
                    "#shorts #gaming #viral"
                ),
                "categoryId": "20"
            },
            "status": {
                "privacyStatus": "public",
                "publishAt": (
                    datetime.utcnow().replace(
                        hour=random.choice(POST_TIMES),
                        minute=30
                    ).isoformat() + "Z"
                )
            }
        },
        media_body=MediaFileUpload("final_short.mp4")
    )
    response = request.execute()
    print(f"✅ Uploaded! Video ID: {response['id']}")


if __name__ == "__main__":
    try:
        streams = find_viral_streams()
        if not streams:
            raise Exception("No trending streams found")

        os.environ['SOURCE_VIDEO_ID'] = streams[0].split("v=")[1]
        create_short(streams[0])
        upload_short()

    except Exception as e:
        print(f"❌ Failed: {e}")
        raise
