import os
import json
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
    """Create YouTube service instance"""
    if api_key:
        return build("youtube", "v3", developerKey=api_key)
    else:
        creds = Credentials.from_authorized_user_info({
            "client_id": os.environ['YT_CLIENT_ID'],
            "client_secret": os.environ['YT_CLIENT_SECRET'],
            "refresh_token": os.environ['YT_REFRESH_TOKEN'],
            "token_uri": "https://oauth2.googleapis.com/token",
            "scopes": ["https://www.googleapis.com/auth/youtube.upload"]
        })
        if creds.expired:
            creds.refresh(Request())
        return build("youtube", "v3", credentials=creds)

def find_viral_streams():
    try:
        youtube = get_youtube_service(api_key=os.environ['YT_API_KEY'])
        
        TOP_GAMING_CREATORS = [
            "UCX6OQ3DkcsbYNE6H8uQQuVA",
            "UC9Z-xXb0tzX2FSCSDEnJ8eQ", 
            "UCYzPXWLvlOIdkpf5-a6s8rA",
            "UCBJycsmduvYEL83R_U4JriQ",
            "UCiP6wD_tYlYLYh3agzbByWQ"
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
                    
                    viewers = stats['items'][0]['liveStreamingDetails'].get('concurrentViewers', '0')
                    if int(viewers) > 10000:
                        viral_streams.append(f"https://youtu.be/{video_id}")
                        
            except Exception as e:
                print(f"⚠️ Couldn't check {channel_id}: {str(e)}")
                continue
        
        return viral_streams
    
    except Exception as e:
        print(f"❌ Search failed: {str(e)}")
        return []

def create_short(stream_url):
    print("🎬 Creating Short...")
    try:
        # Download clip
        subprocess.run([
            'yt-dlp',
            '-f', 'best[height<=720]',
            '--download-sections', '*00:00:00-00:01:30',
            '--write-info-json',
            '-o', 'raw_clip',
            stream_url
        ], check=True)
        
        # Generate captions
        subprocess.run([
            'whisper',
            'raw_clip.mp4',
            '--model', 'tiny',
            '--output_format', 'srt',
            '--language', 'en'
        ], check=True)
        
        # Burn captions
        subprocess.run([
            'ffmpeg',
            '-i', 'raw_clip.mp4',
            '-vf', "subtitles=raw_clip.srt:force_style='Fontsize=24,PrimaryColour=&HFFFFFF,OutlineColour=&H000000,BorderStyle=1,Alignment=10'",
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-crf', '23',
            '-c:a', 'copy',
            '-y',
            'final_short.mp4'
        ], check=True)
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Clip creation failed: {str(e)}")
        raise

def upload_short():
    try:
        youtube = get_youtube_service()
        
        video_id = os.environ['SOURCE_VIDEO_ID']
        video_info = youtube.videos().list(
            part="snippet",
            id=video_id
        ).execute()['items'][0]['snippet']
        
        channel_info = youtube.channels().list(
            part="snippet,statistics",
            id=video_info['channelId']
        ).execute()['items'][0]
        
        request = youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": f"🔥 {channel_info['snippet']['title']} GOES VIRAL! #shorts",
                    "description": f"🚨 CREDIT: {channel_info['snippet']['title']}\n📺 Original: https://youtu.be/{video_id}\n#shorts #gaming #viral",
                    "categoryId": "20"
                },
                "status": {
                    "privacyStatus": "public",
                    "publishAt": datetime.utcnow().replace(
                        hour=random.choice(POST_TIMES),
                        minute=30
                    ).isoformat() + "Z"
                }
            },
            media_body=MediaFileUpload("final_short.mp4")
        )
        response = request.execute()
        print(f"✅ Uploaded! ID: {response['id']}")
        
    except Exception as e:
        print(f"❌ Upload failed: {str(e)}")
        raise

if __name__ == "__main__":
    try:
        print("🔍 Finding trending streams...")
        streams = find_viral_streams()
        
        if not streams:
            print("⚠️ No trending streams found right now")
            exit(0)
            
        print(f"🎥 Found {len(streams)} streams")
        os.environ['SOURCE_VIDEO_ID'] = streams[0].split("v=")[1]
        
        create_short(streams[0])
        upload_short()
        
    except Exception as e:
        print(f"❌ Critical failure: {str(e)}")
        exit(1)
