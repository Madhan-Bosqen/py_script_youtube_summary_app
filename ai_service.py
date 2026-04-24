import os
from google import genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def generate_summary(transcript_text: str, channel_context: dict = None, previous_summaries: list = None) -> str:
    """Generates a structured summary using Google Gemini with channel context."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_key_here":
        return "Summary unavailable: API key not configured."

    try:
        # 1. Initialize the new Client
        client = genai.Client()
        
        # 2. Build Contextual Prompt
        context_block = ""
        if channel_context:
            name = channel_context.get('name', 'Unknown')
            desc = channel_context.get('description', '')
            context_block += f"Channel Name: {name}\n"
            if desc:
                context_block += f"Channel Description: {desc}\n"
        
        if previous_summaries:
            context_block += "\nRecent summaries from this channel for context:\n"
            for i, s in enumerate(previous_summaries, 1):
                title = s.get('title', 'N/A')
                summ = s.get('summary', '')
                # Keep it brief to save tokens
                context_block += f"{i}. {title}: {summ[:300]}...\n"

        prompt = (
            "You are a helpful assistant that summarizes YouTube videos. "
            "Use the provided channel context and previous summaries to maintain consistency and provide a deeper analysis.\n\n"
            f"{context_block}\n"
            "Based on the following transcript, provide a clear, concise, and structured summary. "
            "Focus on the main points, key takeaways, and how this video fits into the channel's usual content.\n\n"
            f"Transcript:\n{transcript_text}"
        )
        
        # 3. Generate content
        response = client.models.generate_content(
            model='gemini-flash-latest',
            contents=prompt,
        )
        return response.text.strip()
    except Exception as e:
        print(f"❌ Error generating summary: {e}")
        return f"Error generating summary: {str(e)}"

def generate_channel_profile_summary(channel_name: str, channel_description: str, recent_summaries: list) -> str:
    """Generates a comprehensive profile/persona summary for a YouTube channel."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "Channel profile summary unavailable."

    try:
        client = genai.Client()
        
        history_text = "\n".join([f"- {s.get('title')}: {s.get('summary')[:200]}..." for s in recent_summaries])
        
        prompt = (
            f"Based on the following information about the YouTube channel '{channel_name}', "
            "provide a professional and engaging profile summary of the creator. "
            "Describe their typical content style, their core topics, and what a viewer can expect from them. "
            "Keep it to 2-3 concise paragraphs.\n\n"
            f"About the Channel:\n{channel_description}\n\n"
            f"Recent Content Themes:\n{history_text}\n\n"
            "Summary Profile:"
        )
        
        response = client.models.generate_content(
            model='gemini-flash-latest',
            contents=prompt,
        )
        return response.text.strip()
    except Exception as e:
        print(f"❌ Error generating channel profile summary: {e}")
        return f"Could not generate creator profile."