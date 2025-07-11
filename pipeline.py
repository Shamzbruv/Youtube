import os
import random
import subprocess
import sys
import time
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# Configuration
CLIP_DURATION = 27
MAX_VIDEOS = 10
MIN_VIEWS = 50000
POST_TIMES = [14, 20, 22]  # 2PM, 8PM, 10PM UTC
HASHTAGS = "#shorts #viral #trending #gamingclips"

def get_youtube_service(api_key=None):
    """Create authenticated YouTube service."""
    if api_key:
        return build("youtube", "v3", developerKey=api_key)
    
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

def download_video(video_url):
    """Download video segment with retries and throttling."""
    try:
        # Random delay to avoid detection
        time.sleep(random.uniform(1.5, 3.5))
        
        # Use yt-dlp with mobile user agent
        subprocess.run([
            'yt-dlp',
            '--user-agent', 'Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36',
            '--throttled-rate', '100K',  # Limit download speed
            '--download-sections', f'*00:00:00-00:00:{CLIP_DURATION}',
            '-f', 'best[height<=720]',
            '-o', 'raw_clip',
            video_url
        ], check=True)
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Download failed: {e}")
        return False

def find_trending_videos():
    """Fetch currently trending gaming videos."""
    youtube = get_youtube_service(api_key=os.environ['YT_API_KEY'])
    
    try:
        results = youtube.videos().list(
            part="snippet,statistics",
            chart="mostPopular",
            regionCode="US",
            maxResults=MAX_VIDEOS,
            videoCategoryId="20"  # Gaming
        ).execute()

        return [
            f"https://youtu.be/{item['id']}"
            for item in results.get('items', [])
            if int(item['statistics'].get('viewCount', 0)) >= MIN_VIEWS
        ]
    except Exception as e:
        print(f"❌ Failed to fetch trending videos: {e}")
        return []

def create_short(video_url):
    """Process video into Short with captions."""
    print(f"🎬 Processing: {video_url}")
    
    try:
        # 1. Download
        if not download_video(video_url):
            raise Exception("Download failed after retries")
        
        # 2. Generate captions
        subprocess.run([
            'whisper', 'raw_clip.mp4',
            '--model', 'tiny',
            '--output_format', 'srt',
            '--language', 'en'
        ], check=True)
        
        # 3. Render final Short
        subprocess.run([
            'ffmpeg',
            '-i', 'raw_clip.mp4',
            '-vf', "subtitles=raw_clip.srt:force_style='Fontsize=24,PrimaryColour=&HFFFFFF,OutlineColour=&H000000,BorderStyle=1,Alignment=10'",
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-crf', '23',
            '-c:a', 'copy',
            '-y', 'final_short.mp4'
        ], check=True)
        
    except Exception as e:
        print(f"❌ Failed to create short: {e}")
        raise

def upload_short(video_url):
    """Upload processed Short to YouTube."""
    youtube = get_youtube_service()
    video_id = video_url.split('/')[-1]
    
    try:
        # Get original video details
        original = youtube.videos().list(
            part="snippet,statistics",
            id=video_id
        ).execute()['items'][0]
        
        # Prepare metadata
        title = f"🔥 {original['snippet']['title'][:50]}! #shorts"
        description = (
            f"🚨 CREDIT: {original['snippet']['channelTitle']}\n"
            f"👀 Original: {video_url}\n"
            f"📈 {original['statistics'].get('viewCount', 'N/A')} views\n\n"
            f"{HASHTAGS}"
        )
        
        # Schedule upload
        publish_time = datetime.utcnow().replace(
            hour=random.choice(POST_TIMES),
            minute=random.randint(15, 45),
            second=0
        ) + timedelta(days=0 if datetime.utcnow().hour < 22 else 1)
        
        # Execute upload
        request = youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": title,
                    "description": description,
                    "categoryId": "20",
                    "tags": ["shorts", "gaming", "viral"]
                },
                "status": {
                    "privacyStatus": "public",
                    "publishAt": publish_time.isoformat() + "Z"
                }
            },
            media_body=MediaFileUpload("final_short.mp4")
        )
        response = request.execute()
        
        print(f"""
✅ Successfully uploaded!
🆔 Video ID: {response['id']}
⏰ Scheduled: {publish_time.strftime('%Y-%m-%d %H:%M UTC')}
🔗 URL: https://youtube.com/shorts/{response['id']}
        """)
        
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        raise

if __name__ == "__main__":
    print("🚀 Starting YouTube Shorts automation")
    
    try:
        # 1. Find trending videos
        videos = find_trending_videos()
        if not videos:
            print("⚠️ No qualifying videos found")
            sys.exit(0)
            
        selected = random.choice(videos)
        print(f"🎯 Selected: {selected}")
        
        # 2. Process and upload
        create_short(selected)
        upload_short(selected)
        
    except Exception as e:
        print(f"❌ Critical error: {e}")
        sys.exit(1)
    finally:
        # Cleanup
        subprocess.run(['rm', '-f', 'raw_clip.*', 'final_short.mp4'])
