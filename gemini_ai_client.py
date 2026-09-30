import os
from dotenv import load_dotenv
from google import genai

# Load .env file
load_dotenv()

# Get API key
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError("GEMINI_API_KEY is missing from the .env file")

# Create Gemini client
client = genai.Client(api_key=API_KEY)

# Default model
MODEL = os.getenv("TIP_MODEL", "gemini-3.8-flash")


def generate_text(prompt: str) -> str:
    """Generate text using Gemini."""

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt
    )

    return response.text