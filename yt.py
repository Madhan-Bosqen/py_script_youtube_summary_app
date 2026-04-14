import os
import re

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from youtube_transcript_api import YouTubeTranscriptApi
import yt_dlp

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def extract_video_id(url: str) -> str:
    match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", url)
    return match.group(1) if match else url

def get_video_info(url: str):
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': "in_playlist", # Extracts fast, but still gets single video metadata
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            return {
                "title": info.get('title', 'Unknown Title'),
                "channel_name": info.get('uploader', 'Unknown Channel'),
                "video_id": info.get('id', extract_video_id(url))
            }
        except Exception:
            return None


@app.get("/")
def root():
    return {"status": "ok", "message": "YouTube transcript API is running"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/transcript")
def get_transcript(url: str):
    video_id = extract_video_id(url)
    
    # 1. Fetch transcript
    try:
        ytt_api = YouTubeTranscriptApi()
        transcript_list = ytt_api.list(video_id)
        transcript_obj = next(iter(transcript_list))
        transcript = transcript_obj.fetch()
        full_text = " ".join([snippet.text.strip() for snippet in transcript])
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Transcript error: {str(e)}")
        
    # 2. Fetch metadata using yt_dlp
    metadata = get_video_info(url)
    if not metadata:
        raise HTTPException(status_code=400, detail="Could not fetch video metadata using yt-dlp.")
        
    return {
        "status": "success",
        "video_id": metadata["video_id"],
        "video_url": url,
        "title": metadata["title"],
        "channel_name": metadata["channel_name"],
        "transcript": full_text
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8001"))
    print(f"Starting FastAPI server on http://localhost:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
