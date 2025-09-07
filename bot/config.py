import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    DATABASE_URL = os.getenv("DATABASE_URL", "")
    
    # Limits
    DAILY_FREE_REQUESTS = 1
    SUBSCRIPTION_PRICE_STARS = 5
    
    # File processing limits
    MAX_FILE_SIZE_MB = 100
    SUPPORTED_AUDIO_FORMATS = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac"}
    SUPPORTED_VIDEO_FORMATS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
    
    # OpenAI settings
    WHISPER_MODEL = "whisper-1"
    GPT_MODEL = "gpt-4o-mini"  # Using mini for cost optimization