import os
import re
import time
import subprocess
import tempfile
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from youtube_transcript_api import YouTubeTranscriptApi
import yt_dlp
from dotenv import load_dotenv
from notification_service import send_new_video_notification

from ai_service import generate_summary, generate_channel_profile_summary

# Try to import the existence check
try:
    from db_service import (
        check_if_video_exists,
        save_summary_to_db,
        get_previous_summaries,
        get_latest_channel_summary,
        get_all_subscribed_channels,
    )
except ImportError:
    def check_if_video_exists(video_id: str) -> bool: return False
    def save_summary_to_db(video_data: dict): pass
    def get_previous_summaries(channel_name: str, limit: int = 3): return []
    def get_latest_channel_summary(channel_name: str): return None
    def get_all_subscribed_channels() -> list: return []

# Load environment variables
load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── HELPER FUNCTIONS ─────────────────────────────────────────────────────────

def extract_video_id(url: str) -> str:
    match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", url)
    return match.group(1) if match else url

def get_video_info(url: str):
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            return {
                "title": info.get('title', 'Unknown Title'),
                "channel_name": info.get('uploader', 'Unknown Channel'),
                "channel_url": info.get('uploader_url'),
                "channel_description": info.get('uploader_description') or info.get('description', '')[:500],
                "video_id": info.get('id', extract_video_id(url))
            }
        except Exception:
            return None

def clean_transcript_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text

def transcript_from_api(video_id: str) -> str:
    ytt_api = YouTubeTranscriptApi()
    transcript_list = ytt_api.list(video_id)
    transcript_obj = next(iter(transcript_list))
    transcript = transcript_obj.fetch()
    full_text = " ".join(snippet.text.strip() for snippet in transcript if snippet.text.strip())
    return clean_transcript_text(full_text)

def parse_vtt_file(vtt_path: Path) -> str:
    lines = []
    for raw_line in vtt_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line == "WEBVTT" or "-->" in line or re.match(r"^\d+$", line) or line.startswith(("NOTE", "Kind:", "Language:")):
            continue
        line = re.sub(r"<[^>]+>", "", line)
        line = re.sub(r"\[[^\]]+\]", "", line)
        if line:
            lines.append(line)

    deduped_lines = []
    previous = None
    for line in lines:
        if line != previous:
            deduped_lines.append(line)
            previous = line

    return clean_transcript_text(" ".join(deduped_lines))

def transcript_from_ytdlp(url: str) -> str:
    with tempfile.TemporaryDirectory(prefix="yt_subs_") as temp_dir:
        output_template = str(Path(temp_dir) / "subtitle.%(ext)s")
        command = [
            "yt-dlp", "--write-auto-sub", "--skip-download", "--sub-langs", "en.*",
            "--sub-format", "vtt", "--output", output_template, url,
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=False)

        if result.returncode != 0:
            stderr = result.stderr.strip() or result.stdout.strip() or "yt-dlp subtitle download failed"
            raise RuntimeError(stderr)

        temp_path = Path(temp_dir)
        vtt_files = sorted(temp_path.glob("*.vtt"))
        if not vtt_files:
            raise FileNotFoundError("yt-dlp did not produce a subtitle file")

        transcript_text = parse_vtt_file(vtt_files[0])
        if not transcript_text:
            raise ValueError("subtitle file was empty after parsing")

        return transcript_text

def fetch_transcript(url: str) -> str:
    video_id = extract_video_id(url)
    try:
        return transcript_from_api(video_id)
    except Exception:
        try:
            return transcript_from_ytdlp(url)
        except Exception as fallback_error:
            raise HTTPException(
                status_code=400,
                detail=f"Unable to fetch transcript: {fallback_error}",
            ) from fallback_error

def get_latest_video_id(channel_url: str):
    ydl_opts = {
        'extract_flat': 'in_playlist',
        'playlist_items': '1',
        'quiet': True
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # 🔥 FIX: Remove tracking parameters before looking up the channel
            clean_url = channel_url.split('?')[0]
            target_url = clean_url if clean_url.endswith('/videos') else f"{clean_url}/videos"
            
            info = ydl.extract_info(target_url, download=False)
            if 'entries' in info and len(info['entries']) > 0:
                latest_video_id = info['entries'][0]['id']
                print(f"🔍 Found latest video ID: {latest_video_id}")
                return latest_video_id
            return None
    except Exception as e:
        print(f"❌ Error fetching channel data: {e}")
        return None

# ─── SHARED PROCESSING HELPER ─────────────────────────────────────────────────

def _process_single_channel(channel_url: str, notifications_enabled: bool = True) -> dict:
    print(f"\n--- 🚀 Processing: {channel_url} ---")

    latest_video_id = get_latest_video_id(channel_url)
    if not latest_video_id:
        return {
            "channel_url": channel_url,
            "status": "error",
            "message": "Could not find any videos on this channel."
        }

    if check_if_video_exists(latest_video_id):
        print(f"✅ Already have video {latest_video_id}. Skipping.")
        return {
            "channel_url": channel_url,
            "status": "up_to_date",
            "message": "No new videos found.",
            "video_id": latest_video_id
        }

    print(f"🔥 NEW VIDEO: {latest_video_id}")
    video_url = f"https://www.youtube.com/watch?v={latest_video_id}"

    try:
        transcript = fetch_transcript(video_url)
        metadata = get_video_info(video_url)

        if not metadata:
            return {
                "channel_url": channel_url,
                "status": "error",
                "message": "Failed to get video metadata."
            }

        channel_name = metadata["channel_name"]
        prev_summaries = get_previous_summaries(channel_name, limit=3)
        
        summary = generate_summary(
            transcript,
            channel_context={
                "name": channel_name,
                "description": metadata.get("channel_description", "")
            },
            previous_summaries=prev_summaries
        )

        channel_info = get_latest_channel_summary(channel_name)
        channel_profile_summary = channel_info.get('channel_profile_summary') if channel_info else None

        if not channel_profile_summary:
            print(f"✨ Generating channel profile for {channel_name}...")
            channel_profile_summary = generate_channel_profile_summary(
                channel_name,
                metadata.get("channel_description", ""),
                prev_summaries + [{"title": metadata["title"], "summary": summary}]
            )

        video_data = {
            "video_id": latest_video_id,
            "video_url": video_url,
            "title": metadata["title"],
            "channel_name": channel_name,
            "channel_url": metadata.get("channel_url"),
            "channel_profile_summary": channel_profile_summary,
            "transcript": transcript,
            "summary": summary
        }
        save_summary_to_db(video_data)

        if notifications_enabled:
            send_new_video_notification(
                title=metadata["title"],
                channel_name=channel_name,
                video_id=latest_video_id
            )

        print(f"✅ Done: {metadata['title']}")

        return {
            "channel_url": channel_url,
            "channel_name": channel_name,
            "status": "new_video",
            "message": "New video summarized and saved!",
            "video_id": latest_video_id,
            "title": metadata["title"],
        }

    except Exception as e:
        print(f"❌ Error processing {channel_url}: {e}")
        return {
            "channel_url": channel_url,
            "status": "error",
            "message": str(e)
        }

# ─── API ENDPOINTS ────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "ok", "message": "YouTube transcript API is running"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/transcript")
def get_transcript(url: str):
    metadata = get_video_info(url)
    if not metadata:
        raise HTTPException(status_code=400, detail="Could not fetch video metadata.")

    channel_name = metadata["channel_name"]
    channel_url = metadata.get("channel_url")
    prev_summaries = get_previous_summaries(channel_name, limit=3)
    channel_info = get_latest_channel_summary(channel_name)
    channel_profile_summary = channel_info.get('channel_profile_summary') if channel_info else None
    transcript = fetch_transcript(url)

    channel_context = {
        "name": channel_name,
        "description": metadata.get("channel_description", "")
    }
    summary = generate_summary(transcript, channel_context=channel_context, previous_summaries=prev_summaries)

    if not channel_profile_summary:
        channel_profile_summary = generate_channel_profile_summary(
            channel_name,
            metadata.get("channel_description", ""),
            prev_summaries + [{"title": metadata["title"], "summary": summary}]
        )

    video_data = {
        "video_id": metadata["video_id"],
        "video_url": url,
        "title": metadata["title"],
        "channel_name": channel_name,
        "channel_url": channel_url,
        "channel_profile_summary": channel_profile_summary,
        "transcript": transcript,
        "summary": summary
    }
    save_summary_to_db(video_data)

    return {
        "status": "success",
        "video_id": metadata["video_id"],
        "video_url": url,
        "title": metadata["title"],
        "channel_name": channel_name,
        "channel_url": channel_url,
        "channel_profile_summary": channel_profile_summary,
        "previous_summaries": [s.get('summary', '') for s in prev_summaries],
        "transcript": transcript,
        "summary": summary,
    }

@app.get("/channel-profile")
def get_channel_profile_endpoint(channel_name: str):
    channel_info = get_latest_channel_summary(channel_name)
    prev_summaries = get_previous_summaries(channel_name, limit=3)

    if not channel_info and not prev_summaries:
        return {"status": "error", "message": "No data found for this channel."}

    return {
        "status": "success",
        "data": {
            "channel_name": channel_name,
            "channel_url": channel_info.get('channel_url') if channel_info else None,
            "profile_summary": channel_info.get('channel_profile_summary') if channel_info else "No profile generated yet.",
            "last_3_summaries": prev_summaries
        }
    }

@app.get("/transcript-only")
def get_transcript_only(url: str):
    try:
        transcript = fetch_transcript(url)
        return {"transcript": transcript}
    except HTTPException:
        return {"error": "Unable to fetch transcript"}

@app.get("/force-check")
def force_check_channel(channel_url: str):
    result = _process_single_channel(channel_url, notifications_enabled=True)
    return result

@app.get("/force-check-all")
def force_check_all_channels():
    print("\n=== 🚀 BULK CHANNEL CHECK STARTED ===")
    channels = get_all_subscribed_channels()

    if not channels:
        return {"status": "error", "message": "No subscribed channels found in the database."}

    print(f"📋 Checking {len(channels)} channel(s)...")
    results = []
    new_videos_count = 0

    for channel in channels:
        channel_url = channel.get("channel_url", "")
        notifications_enabled = channel.get("notifications_enabled", False)
        channel_name = channel.get("channel_name", "Unknown")

        if not channel_url:
            print(f"⚠️ Skipping '{channel_name}' — no channel_url set.")
            results.append({
                "channel_name": channel_name,
                "status": "skipped",
                "message": "No channel_url stored. Edit this channel in the app to add its URL."
            })
            continue

        result = _process_single_channel(channel_url, notifications_enabled)
        result.setdefault("channel_name", channel_name)
        results.append(result)

        if result.get("status") == "new_video":
            new_videos_count += 1

        time.sleep(2)

    print(f"\n=== ✅ BULK CHECK DONE | {new_videos_count} new video(s) across {len(channels)} channel(s) ===")

    return {
        "status": "success",
        "total_channels_checked": len(channels),
        "new_videos_found": new_videos_count,
        "results": results
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    print(f"Starting FastAPI server on http://localhost:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)