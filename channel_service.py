import yt_dlp

def get_latest_video_id(channel_url: str):
    """
    Looks at a YouTube channel URL and returns the ID of the newest video.
    """
    ydl_opts = {
        'extract_flat': 'in_playlist', # Don't download the video, just get metadata
        'playlist_items': '1',         # Only grab the very first item (the newest)
        'quiet': True                  # Keep the console clean
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # We add /videos to the URL to ensure we look at the uploads tab, not shorts or live
            target_url = channel_url if channel_url.endswith('/videos') else f"{channel_url}/videos"
            info = ydl.extract_info(target_url, download=False)
            
            if 'entries' in info and len(info['entries']) > 0:
                latest_video_id = info['entries'][0]['id']
                print(f"🔍 Found latest video ID: {latest_video_id}")
                return latest_video_id
            return None
    except Exception as e:
        print(f"❌ Error fetching channel data: {e}")
        return None