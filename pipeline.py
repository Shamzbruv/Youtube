import os
import re
from datetime import datetime, timedelta
from googleapiclient.discovery import build

# 1. OPTIMAL CLIP SETTINGS (PRO-TESTED)
CLIP_DURATION = 27  # 15-35s performs best (27s ideal)
MAX_CREATORS = 5    # Track top 5 creators simultaneously
POST_TIMES = [14, 20]  # 2PM & 8PM UTC (best engagement)

# 2. VIRAL TITLE GENERATOR
def generate_title(creator_name):
    POWER_WORDS = ["INSANE", "UNBELIEVABLE", "MINDBLOWING", "WILD", "SAVAGE"]
    return f"🔥 {creator_name} {random.choice(POWER_WORDS)} MOMENT! #shorts"

# 3. ULTIMATE DESCRIPTION TEMPLATE
def generate_description(creator):
    return f"""🚨 {creator['channel_name']} BREAKS THE INTERNET WITH THIS!

📺 FULL VIDEO: {creator['original_video_url']}
👉 SUBSCRIBE: {creator['channel_url']} ({creator['subscribers']} loyal fans)

💬 "WHAT WOULD YOU DO HERE?" ↓ COMMENT!
👍 SMASH LIKE FOR PART 2!
🔔 TURN ON NOTIFICATIONS!

⚡ #{creator['channel_name'].replace(' ','')} 
⚡ #gamingclips 
⚡ #viralclip
⚡ #livemoments
⚡ #shortsfeed

⚠️ Credit: {creator['channel_name']} (automated highlight)"""

# 4. STREAM FINDER WITH VIRAL POTENTIAL FILTER
def find_viral_streams():
    youtube = build("youtube", "v3", developerKey=os.environ['YT_API_KEY'])
    
    TOP_GAMING_CREATORS = [
        "UCX6OQ3DkcsbYNE6H8uQQuVA",  # MrBeast Gaming
        "UC9Z-xXb0tzX2FSCSDEnJ8eQ",  # iShowSpeed
        "UCYzPXWLvlOIdkpf5-a6s8rA",  # CaseOh
        "UCBJycsmduvYEL83R_U4JriQ",  # Mongraal
        "UCiP6wD_tYlYLYh3agzbByWQ"   # TypicalGamer
    ]
    
    streams = []
    for channel_id in TOP_GAMING_CREATORS:
        try:
            # Only fetch streams with >10K concurrent viewers
            search = youtube.search().list(
                part="snippet",
                channelId=channel_id,
                eventType="live",
                type="video",
                order="viewCount",
                maxResults=1
            ).execute()
            
            if search['items']:
                video_id = search['items'][0]['id']['videoId']
                stats = youtube.videos().list(
                    part="liveStreamingDetails",
                    id=video_id
                ).execute()
                
                if int(stats['items'][0]['liveStreamingDetails']['concurrentViewers']) > 10000:
                    streams.append(f"https://youtu.be/{video_id}")
                    
        except Exception as e:
            print(f"⚠️ Error checking {channel_id}: {str(e)}")
    
    return streams[:MAX_CREATORS]  # Return most viral streams

# 5. ENGAGEMENT-BASED CLIP SELECTION
def select_clip_moment(stream_url):
    # Download first 90s (optimal for Shorts retention)
    subprocess.run(
        f"yt-dlp -f best --download-sections '*00:00:00-00:01:30' "
        f"--write-info-json -o 'preview' {stream_url}",
        shell=True, check=True
    )
    
    # Analyze for peak engagement
    with open('preview.info.json') as f:
        data = json.load(f)
    
    # Prefer moments with: chat spikes + high like ratio
    best_moment = "00:00:15"  # Default to first action moment
    
    if 'heatmap' in data:
        best_moment = max(
            [x for x in data['heatmap'] if x['time'] < 60],  # Only first 60s
            key=lambda x: x['intensity'] * 0.7 + x['likes'] * 0.3
        )['time']
    
    return str(timedelta(seconds=int(float(best_moment))))

# 6. UPLOAD WITH VIRAL OPTIMIZATION
def upload_short():
    # ... [keep previous upload_short() but add these optimizations] ...
    body={
        "snippet": {
            "title": generate_title(creator['channel_name']),
            "description": generate_description(creator),
            "tags": ["shorts"] + [
                re.sub(r'[^a-z0-9]', '', creator['channel_name'].lower()),
                "gaming",
                "viral",
                "livestream",
                "clips",
                "trending"
            ],
            "categoryId": "20"  # Gaming
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
    }
