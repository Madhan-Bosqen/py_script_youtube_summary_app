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
    Uses merge-duplicates so re-processing an existing video updates it instead of crashing.
    """
    if not url or not key:
        print("❌ Cannot save: SUPABASE_URL or SUPABASE_KEY missing from .env.")
        return

    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates"
    }

    endpoint = f"{url}/rest/v1/youtube_summaries"

    try:
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
            return len(data) > 0
        return False
    except Exception as e:
        print(f"❌ Database check exception: {e}")
        return False


def get_previous_summaries(channel_name: str, limit: int = 3):
    """
    Fetches the last N summaries for a specific channel from Supabase.
    Used to give the AI model context about the channel's recent content.
    """
    if not url or not key:
        return []

    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
    }

    # URL-encode the channel name to handle spaces and special characters
    from urllib.parse import quote
    encoded_name = quote(channel_name)

    endpoint = (
        f"{url}/rest/v1/youtube_summaries"
        f"?channel_name=eq.{encoded_name}"
        f"&select=title,summary"
        f"&order=created_at.desc"
        f"&limit={limit}"
    )

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
    Returns None if no profile has been generated yet.
    """
    if not url or not key:
        return None

    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
    }

    from urllib.parse import quote
    encoded_name = quote(channel_name)

    endpoint = (
        f"{url}/rest/v1/youtube_summaries"
        f"?channel_name=eq.{encoded_name}"
        f"&select=channel_profile_summary,channel_url"
        f"&channel_profile_summary=not.is.null"
        f"&order=created_at.desc"
        f"&limit=1"
    )

    try:
        response = requests.get(endpoint, headers=headers)
        if response.status_code == 200:
            data = response.json()
            return data[0] if data else None
        return None
    except Exception as e:
        print(f"❌ Error fetching channel context: {e}")
        return None


# 🔥 NEW: Get all channels the user has subscribed to
def get_all_subscribed_channels() -> list:
    """
    Returns all rows from channel_subscriptions where:
      - is_subscribed = TRUE
      - channel_url is NOT NULL
    Each item contains: { channel_name, channel_url, notifications_enabled }
    This is used by the /force-check-all endpoint to know which channels to check.
    """
    if not url or not key:
        print("❌ Cannot fetch channels: SUPABASE_URL or SUPABASE_KEY missing.")
        return []

    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
    }

    endpoint = (
        f"{url}/rest/v1/channel_subscriptions"
        f"?is_subscribed=eq.true"
        f"&channel_url=not.is.null"
        f"&select=channel_name,channel_url,notifications_enabled"
    )

    try:
        response = requests.get(endpoint, headers=headers)
        if response.status_code == 200:
            channels = response.json()
            print(f"📋 Found {len(channels)} subscribed channel(s) in DB.")
            return channels
        else:
            print(f"❌ Error fetching subscribed channels: {response.text}")
            return []
    except Exception as e:
        print(f"❌ Exception fetching subscribed channels: {e}")
        return []