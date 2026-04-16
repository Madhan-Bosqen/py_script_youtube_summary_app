import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure Gemini
api_key = os.getenv("GEMINI_API_KEY")
if api_key and api_key != "your_key_here":
    genai.configure(api_key=api_key)
else:
    print("Warning: GEMINI_API_KEY not set or still has placeholder value.")

def generate_summary(transcript_text: str) -> str:
    """Generates a structured summary using Google Gemini."""
    if not os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY") == "your_key_here":
        return "Summary unavailable: API key not configured."

    try:
        model = genai.GenerativeModel("gemini-flash-latest")
        prompt = (
            "You are a helpful assistant that summarizes YouTube videos. "
            "Based on the following transcript, provide a clear, concise, and structured summary. "
            "Focus on the main points and key takeaways.\n\n"
            f"Transcript:\n{transcript_text}"
        )
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Error generating summary: {e}")
        return f"Error generating summary: {str(e)}"
