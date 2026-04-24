import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get credentials
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

def save_summary_to_db(video_data: dict):
    """
    Saves the full video summary package directly to the Supabase REST API.
    """
    if not url or not key:
        print("❌ Cannot save: SUPABASE_URL or SUPABASE_KEY missing from .env.")
        return

    # Prepare the API request headers
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates" 
    }
    
    endpoint = f"{url}/rest/v1/youtube_summaries"
    
    try:
        # Notice we are passing the entire video_data dictionary now
        response = requests.post(endpoint, headers=headers, json=video_data)
        if response.status_code in [200, 201, 204]:
            print(f"✅ Summary saved to DB for video {video_data.get('video_id')}")
        else:
            print(f"❌ Database save error: {response.text}")
    except Exception as e:
        print(f"❌ Database save exception: {e}")

def check_if_video_exists(video_id: str) -> bool:
    """
    Checks the Supabase REST API to see if we already have a summary for this video.
    """
    if not url or not key:
        print("❌ Cannot check DB: SUPABASE_URL or SUPABASE_KEY missing.")
        return False

    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
    }
    
    endpoint = f"{url}/rest/v1/youtube_summaries?select=video_id&video_id=eq.{video_id}"
    
    try:
        response = requests.get(endpoint, headers=headers)
        if response.status_code == 200:
            data = response.json()
            if len(data) > 0:
                return True
        return False
    except Exception as e:
        print(f"❌ Database check exception: {e}")
        return False

def get_previous_summaries(channel_name: str, limit: int = 3):
    """
    Fetches the last N summaries for a specific channel from Supabase.
    """
    if not url or not key:
        return []

    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
    }
    
    # Query: filter by channel_name
    endpoint = f"{url}/rest/v1/youtube_summaries?channel_name=eq.{channel_name}&select=title,summary&limit={limit}"
    
    try:
        response = requests.get(endpoint, headers=headers)
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        print(f"❌ Error fetching previous summaries: {e}")
        return []

def get_latest_channel_summary(channel_name: str):
    """
    Retrieves the most recent channel_profile_summary for a creator 
    from the existing youtube_summaries table.
    """
    if not url or not key:
        return None

    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
    }
    # Query for records where channel_profile_summary is not null, limited to 1
    endpoint = f"{url}/rest/v1/youtube_summaries?channel_name=eq.{channel_name}&select=channel_profile_summary,channel_url&channel_profile_summary=not.is.null&limit=1"
    
    try:
        response = requests.get(endpoint, headers=headers)
        if response.status_code == 200:
            data = response.json()
            return data[0] if data else None
        return None
    except Exception as e:
        print(f"❌ Error fetching channel context: {e}")
        return None