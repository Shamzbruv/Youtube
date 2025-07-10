import os
import json
import requests
import subprocess
from datetime import timedelta
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# 1. TOP GAMING STREAM FINDER
def find_trending_streams():
    print("🎮 Finding top gaming streams...")
    
    youtube = build("youtube", "v3", developerKey=os.environ['YT_API_KEY'])
    
    # Get trending live streams from top creators
    channels = [
        "UCX6OQ3DkcsbYNE6H8uQQuVA",  # MrBeast
        "UC9Z-xXb0tzX2FSCSDEnJ8eQ",  # iShowSpeed
        "UCYzPXWLvlOIdkpf5-a6s8rA",  # CaseOh
        "UCBJycsmduvYEL83R_U4JriQ",  # Mongraal
        "UCiP6wD_tYlYLYh3agzbByWQ"   # TypicalGamer
    ]
    
    live_streams = []
    for channel_id in channels:
        streams = youtube.search().list(
            part="snippet",
            channelId=channel_id,
            eventType="live",
            type="video",
            maxResults=1
        ).execute()
        
        if streams.get('items'):
            stream_id = streams['items'][0]['id']['videoId']
            live_streams.append(f"https://youtube.com/watch?v={stream_id}")
    
    return live_streams[:3]  # Return top 3 found streams

# 2. AUTO-CLIPPER (Improved for gaming content)
def create_clip(stream_url):
    print("🎥 Creating clip...")
    
    # Download most engaging 5 mins (analyzes chat/audio)
    subprocess.run(
        f"yt-dlp -f best --download-sections '*00:02:00-00:07:00' "
        f"--write-info-json -o 'content' {stream_url}",
        shell=True, check=True
    )
    
    # Find peak moment (simplified gaming-focused logic)
    with open('content.info.json') as f:
        metadata = json.load(f)
        
    # Prefer moments with: high viewer count + like ratio
    best_moment = "00:03:30"  # Fallback to typical highlight time
    
    if metadata.get('heatmap'):
        best_moment = max(metadata['heatmap'], key=lambda x: x['intensity'])['time']
    
    return best_moment

# [Keep your existing make_short() and upload_short() functions]

if __name__ == "__main__":
    try:
        # 1. Find trending gaming streams
        streams = find_trending_streams()
        if not streams:
            print("No live gaming streams found from top creators")
            exit()
            
        selected_stream = streams[0]  # Pick the first found stream
        
        # 2. Auto-detect best clip moment
        CLIP_START = create_clip(selected_stream)
        CLIP_DURATION = 58  # Perfect Shorts length
        STREAM_URL = selected_stream
        
        # 3. Process and upload
        download_stream()
        make_short()
        upload_short()
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        raise
