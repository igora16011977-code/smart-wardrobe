import os
from dotenv import load_dotenv

# Завантажуємо локальний .env (потрібно тільки для тестів на комп'ютері)
load_dotenv()

# Бот тягнутиме ключі з системи (на Render — з розділу Environment Variables)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")

try:
    ADMIN_ID = int(os.getenv("ADMIN_ID", "1902059714"))
except ValueError:
    ADMIN_ID = 1902059714

