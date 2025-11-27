# core/config.py
import os
from dotenv import load_dotenv

load_dotenv()

def get_api_key():
    google_key = os.getenv("GOOGLE_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY")
    if google_key:
        return google_key
    if gemini_key:
        return gemini_key
    raise EnvironmentError(
        "No Gemini API key found. Please create a .env with GOOGLE_API_KEY or GEMINI_API_KEY."
    )
