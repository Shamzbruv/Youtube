import os
import subprocess
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# 1. SETTINGS (EDIT THESE!)
STREAM_URL = "PASTE_YOUR_LIVESTREAM_URL_HERE"  # e.g., "https://youtube.com/watch?v=abc123"
CLIP_DURATION = 60  # 60 seconds for Shorts
CLIP_START = "00:05:00"  # Start clipping at 5 mins (adjust as needed)

# 2. DOWNLOAD STREAM
def download_stream():
    print("📥 Downloading stream...")
    subprocess.run(f"yt-dlp -f 'best[height<=720]' --download-sections '*{CLIP_START}-{CLIP_START + CLIP_DURATION}' -o stream.mp4 {STREAM_URL}", shell=True)

# 3. MAKE SHORT CLIP
def make_short():
    print("✂️ Cutting Short...")
    subprocess.run(f"ffmpeg -i stream.mp4 -ss 0 -t {CLIP_DURATION} -vf 'scale=1080:1920,setsar=1:1' -c:v libx264 -preset fast -crf 23 -c:a copy short.mp4", shell=True)

# 4. UPLOAD TO YOUTUBE
def upload_short():
    print("⬆️ Uploading to YouTube...")
    creds = Credentials.from_authorized_user_file("token.json")
    youtube = build("youtube", "v3", credentials=creds)
    
    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": "Auto-Generated Short #shorts",
                "description": "Created with GitHub Actions!",
                "tags": ["shorts", "clip"],
            },
            "status": {
                "privacyStatus": "public",  # "private" if testing
            },
        },
        media_body=MediaFileUpload("short.mp4"),
    )
    response = request.execute()
    print("✅ Uploaded! Video ID:", response["id"])

if __name__ == "__main__":
    download_stream()
    make_short()
    upload_short()
