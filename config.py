# Пряме налаштування конфігурації бота (без використання .env)
from dotenv import load_dotenv

load_dotenv()
import os
TOKEN = os.getenv("BOT_TOKEN")

TELEGRAM_TOKEN = "8980208249:AAHf20dOgrG-refz7CtBVoAV8kt6AdWL5Bk"
import os
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEATHER_API_KEY = "ec787296b70be02f50d617c141b62b61"
ADMIN_ID = 1902059714


# Автоматична перевірка конфігурації (Groq більше не перевіряємо)
if not all([TELEGRAM_TOKEN, WEATHER_API_KEY, OPENAI_API_KEY, ADMIN_ID]):
    print("⚠️ Попередження: Деякі ключі вписані невірно!")

