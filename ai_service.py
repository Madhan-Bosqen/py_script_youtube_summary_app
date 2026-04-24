import os
from google import genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def generate_summary(transcript_text: str) -> str:
    """Generates a structured summary using Google Gemini."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_key_here":
        return "Summary unavailable: API key not configured."

    try:
        # 1. Initialize the new Client
        client = genai.Client()
        
        # 2. Define the prompt
        prompt = (
            "You are a helpful assistant that summarizes YouTube videos. "
            "Based on the following transcript, provide a clear, concise, and structured summary. "
            "Focus on the main points and key takeaways.\n\n"
            f"Transcript:\n{transcript_text}"
        )
        
        # 3. Generate content using the new syntax
        response = client.models.generate_content(
            model='gemini-1.5',
            contents=prompt,
        )
        return response.text.strip()
    except Exception as e:
        print(f"❌ Error generating summary: {e}")
        return f"Error generating summary: {str(e)}"