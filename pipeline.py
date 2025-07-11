import os
import random
import subprocess
import sys
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# VIRAL SETTINGS (Tweak these!)
CLIP_DURATION = 27                # Ideal Shorts length (15-34s)
MAX_VIDEOS = 10                   # Check more videos for best clip
MIN_VIEWS = 50000                 # Only use trending videos with 50k+ views
POST_TIMES = [14, 20, 22]         # 2PM, 8PM, 10PM UTC (peak hours)
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

def find_trending_videos():
    """Fetch currently trending videos with high engagement."""
    youtube = get_youtube_service(api_key=os.environ['YT_API_KEY'])
    
    try:
        results = youtube.videos().list(
            part="snippet,statistics,contentDetails",
            chart="mostPopular",
            regionCode="US",
            maxResults=MAX_VIDEOS,
            videoCategoryId="20"  # Gaming
        ).execute()

        viral_videos = []
        for item in results.get('items', []):
            stats = item['statistics']
            views = int(stats.get('viewCount', 0))
            likes = int(stats.get('likeCount', 0))
            
            # Viral potential formula (views + likes per hour)
            upload_time = datetime.fromisoformat(item['snippet']['publishedAt'][:-1])
            hours_up = (datetime.utcnow() - upload_time).total_seconds() / 3600
            viral_score = (views + likes*10) / max(1, hours_up)
            
            if viral_score > 100000:  # Adjust based on performance
                viral_videos.append({
                    'url': f"https://youtu.be/{item['id']}",
                    'score': viral_score,
                    'views': views
                })
        
        # Return top 3 most viral
        return sorted(viral_videos, key=lambda x: -x['score'])[:3]
    
    except Exception as e:
        print(f"❌ Trending fetch failed: {e}")
        return []

def create_short(video_url):
    """Create optimized Short with captions."""
    try:
        # 1. Download best moments (auto-detects highlights)
        subprocess.run([
            'yt-dlp',
            '-f', 'best[height<=1080]',
            '--download-sections', f'*00:00:00-00:00:{CLIP_DURATION}',
            '--match-filter', 'duration < 600',  # Only shorts (<10min)
            '--extract-audio',
            '--audio-format', 'mp3',
            '-o', 'raw_clip',
            video_url
        ], check=True)
        
        # 2. Generate engaging captions
        subprocess.run([
            'whisper',
            'raw_clip.mp4',
            '--model', 'small',  # More accurate than 'tiny'
            '--output_format', 'srt',
            '--language', 'en',
            '--word_timestamps', 'True'
        ], check=True)
        
        # 3. Create eye-catching captions
        subprocess.run([
            'ffmpeg',
            '-i', 'raw_clip.mp4',
            '-i', 'raw_clip.mp3',  # Higher quality audio
            '-vf', (
                "subtitles=raw_clip.srt:"
                "force_style='Fontsize=28,"
                "PrimaryColour=&H00FF00&,"  # Bright green
                "OutlineColour=&H000000,"
                "BorderStyle=3,Alignment=10'"
            ),
            '-c:v', 'libx264',
            '-preset', 'ultrafast',
            '-crf', '18',  # Higher quality
            '-c:a', 'aac',
            '-b:a', '192k',
            '-y',
            'final_short.mp4'
        ], check=True)
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Clip creation failed: {e}")
        raise

def upload_short(video_info):
    """Upload with viral-optimized metadata."""
    youtube = get_youtube_service()
    
    # 1. Get original video details
    original_id = video_info['url'].split('/')[-1]
    original = youtube.videos().list(
        part="snippet,statistics",
        id=original_id
    ).execute()['items'][0]
    
    # 2. Craft viral title/description
    title = f"🔥 {original['snippet']['title'][:50]}! #shorts"
    description = (
        f"🚨 CREDIT: {original['snippet']['channelTitle']}\n"
        f"👀 Original: {video_info['url']}\n"
        f"📈 {video_info['views']:,} views when clipped\n\n"
        f"{HASHTAGS}\n\n"
        "⚠️ Copyright: This is fair use for commentary"
    )
    
    # 3. Schedule for peak time
    now = datetime.utcnow()
    next_peak = min(
        [t for t in POST_TIMES if t > now.hour] or POST_TIMES
    )
    publish_time = now.replace(
        hour=next_peak,
        minute=random.randint(15, 45),
        second=0
    ) + timedelta(days=0 if now.hour < 22 else 1)  # Post today or tomorrow
    
    # 4. Upload
    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": title,
                "description": description,
                "categoryId": "20",  # Gaming
                "tags": ["viral", "shorts", "gaming"]
            },
            "status": {
                "privacyStatus": "private",  # Test with private first!
                "publishAt": publish_time.isoformat() + "Z"
            }
        },
        media_body=MediaFileUpload(
            "final_short.mp4",
            chunksize=-1,
            resumable=True
        )
    )
    
    response = request.execute()
    print(f"""
✅ Successfully uploaded!
🆔 Video ID: {response['id']}
⏰ Scheduled: {publish_time.strftime('%Y-%m-%d %H:%M UTC')}
🔗 URL: https://youtube.com/shorts/{response['id']}
    """)

if __name__ == "__main__":
    print("🚀 Starting viral shorts pipeline...")
    
    # 1. Find trending content
    trending = find_trending_videos()
    if not trending:
        print("⚠️ No viral videos found - try again in 1 hour")
        sys.exit(0)
        
    best_clip = max(trending, key=lambda x: x['score'])
    print(f"🎯 Selected clip: {best_clip['url']} (Score: {best_clip['score']:,.0f})")
    
    # 2. Process and upload
    os.environ['SOURCE_VIDEO_ID'] = best_clip['url'].split('/')[-1]
    create_short(best_clip['url'])
    upload_short(best_clip)
    
    # 3. Cleanup
    subprocess.run(['rm', '-f', 'raw_clip.*', 'final_short.mp4'])
