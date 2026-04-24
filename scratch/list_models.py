import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

def list_models():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ No API key found.")
        return

    client = genai.Client()
    print("--- Available Models ---")
    try:
        # Use pagination or list
        for model in client.models.list():
            print(f"- {model.name}")
    except Exception as e:
        print(f"❌ Error listing models: {e}")

if __name__ == "__main__":
    list_models()
