# Пряме налаштування конфігурації бота (без використання .env)

TELEGRAM_TOKEN = "8980208249:AAGYq5ohv_5SFKY9UbG-dp13RucE9LzsbN4"
GROQ_API_KEY = "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"
WEATHER_API_KEY = "ec787296b70be02f50d617c141b62b61"
ADMIN_ID = 1902059714


# Автоматична перевірка
if not all([TELEGRAM_TOKEN, GROQ_API_KEY, WEATHER_API_KEY, ADMIN_ID]):
    print("⚠️ Попередження: Деякі ключі вписані невірно!")

