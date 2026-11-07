import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")  # Наш новий безкоштовний ШІ 💖

try:
    ADMIN_ID = int(os.getenv("ADMIN_ID", "1902059714"))
except ValueError:
    ADMIN_ID = 1902059714
