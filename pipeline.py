import os
import json
import requests
from datetime import datetime
from googleapiclient.discovery import build

# 1. ENHANCED CREATOR CREDIT SYSTEM
def get_creator_details(video_id):
    youtube = build("youtube", "v3", developerKey=os.environ['YT_API_KEY'])
    
    # Get video details
    video = youtube.videos().list(
        part="snippet,statistics",
        id=video_id
    ).execute()["items"][0]
    
    # Get channel details
    channel = youtube.channels().list(
        part="snippet,statistics",
        id=video["snippet"]["channelId"]
    ).execute()["items"][0]
    
    return {
        "channel_name": channel["snippet"]["title"],
        "channel_url": f"https://youtube.com/channel/{channel['id']}",
        "subscribers": f"{int(channel['statistics']['subscriberCount']):,}",
        "original_video_url": f"https://youtu.be/{video_id}",
        "creator_thumbnail": channel["snippet"]["thumbnails"]["high"]["url"],
        "view_count": f"{int(video['statistics']['viewCount']):,}",
        "likes": f"{int(video['statistics'].get('likeCount', 0)):,}"
    }

# 2. VIRAL OPTIMIZED DESCRIPTION GENERATOR
def generate_description(creator):
    return f"""🔥 {creator['channel_name']} JUST DROPPED THIS INSANE CLIP! 🔥

📺 Watch the FULL video: {creator['original_video_url']}
✅ Subscribe: {creator['channel_url']} ({creator['subscribers']} subs)

💬 COMMENT below what you think!
👍 LIKE if you want more clips like this!
🔔 TURN ON POST NOTIFICATIONS!

📌 #shorts #{creator['channel_name'].replace(' ','')} #viral #trending #gaming #clips

⚠️ All rights belong to {creator['channel_name']}
This is an automated highlight clip."""

# 3. UPDATED UPLOAD FUNCTION
def upload_short():
    creds = Credentials.from_authorized_user_info(info={
        "client_id": os.environ['YT_CLIENT_ID'],
        "client_secret": os.environ['YT_CLIENT_SECRET'],
        "refresh_token": os.environ['YT_REFRESH_TOKEN'],
        "token_uri": "https://oauth2.googleapis.com/token",
        "scopes": ["https://www.googleapis.com/auth/youtube.upload"]
    })
    
    youtube = build("youtube", "v3", credentials=creds)
    
    # Get creator details before upload
    video_id = STREAM_URL.split("v=")[1].split("&")[0]
    creator = get_creator_details(video_id)
    
    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": f"🔥 {creator['channel_name']} DID THIS! #shorts",
                "description": generate_description(creator),
                "tags": [
                    "shorts", creator['channel_name'].lower().replace(" ", ""),
                    "gaming", "viral", "trending", "clips",
                    "live", "stream", "highlight"
                ],
                "categoryId": "20"  # Gaming category
            },
            "status": {
                "privacyStatus": "public",
                "selfDeclaredMadeForKids": False,
                "embeddable": True
            },
        },
        media_body=MediaFileUpload("short.mp4")
    )
    response = request.execute()
    print(f"✅ Uploaded! Video ID: {response['id']}")

# [Keep your existing find_trending_streams(), create_clip(), etc.]
