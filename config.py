import os
from dotenv import load_dotenv

# Load variables from .env
load_dotenv()

class Config:
    # Configuration constants
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    IMAGE_GEN_KEY = os.getenv("IMAGE_GEN_KEY")
    OPENWEATHERMAP_API_KEY = os.getenv("OPENWEATHERMAP_API_KEY")
    ADMIN_ID = os.getenv("ADMIN_ID")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not Config.TELEGRAM_TOKEN:
    print("Warning: TELEGRAM_BOT_TOKEN is not set!")