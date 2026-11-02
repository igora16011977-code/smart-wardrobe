import os
import asyncio
import logging
import requests
import sqlite3
from aiogram import Bot, Dispatcher, executor
from aiogram.dispatcher.filters import Text
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from dotenv import load_dotenv

# Завантажуємо токени з файлу .env
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
DB_NAME = os.getenv("DB_NAME", "wardrobe.db")

if not TELEGRAM_TOKEN:
    raise ValueError("Помилка: TELEGRAM_TOKEN не знайдено у файлі .env!")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher(bot)

# ==================== ЛОГІКА ПОГОДИ (БЕЗ ШІ) ====================

def get_weather(city: str = "Kyiv") -> dict:
    """Отримує актуальну погоду через OpenWeather API"""
    url = "https://openweathermap.org"
    params = {"q": city, "appid": WEATHER_API_KEY, "units": "metric", "lang": "uk"}
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return {
                "success": True,
                "temp": round(data["main"]["temp"]),
                "description": data["weather"][0]["description"],
                "feels_like": round(data["main"]["feels_like"]),
                "humidity": data["main"]["humidity"]
            }
    except Exception as e:
        logging.error(f"Помилка отримання погоди: {e}")
    
    # Резервний варіант, якщо сервер погоди не відповів
    return {"success": False, "temp": 15, "description": "мінлива хмарність", "feels_like": 14, "humidity": 60}

def get_recommendation_by_weather(weather_data: dict) -> str:
    """Функція замість ШІ, яка дає чітку пораду залежно від температури"""
    temp = weather_data["temp"]
    desc = weather_data["description"]
    feels_like = weather_data.get("feels_like", temp)
    
    advice = f"🌤 **Погода зараз:** {temp}°C (відчувається як {feels_like}°C), {desc}.\n\n"
    advice += "👔 **Рекомендація щодо одягу:**\n"
    
    if temp < 0:
        advice += "🥶 Дуже холодно! Одягайте теплий пуховик, шапку, шарф та рукавички. З гардероба оберіть найтепліші светри та зимове взуття."
    elif 0 <= temp < 10:
        advice += "🍂 Холодно. Рекомендуємо тепле пальто або куртку, черевики, щільний худі чи джемпер."
    elif 10 <= temp < 18:
        advice += "🌤 Помірна прохолода. Підійде легка куртка, вітровка, тренч, щільні джинси та кросівки або туфлі."
    elif 18 <= temp < 25:
        advice += "☀️ Комфортно і тепло. Можна впевнено одягати лонгслів, сорочку, джинси або штани-чінос."
    else:
        advice += "🔥 Спекотно! Найкращий вибір — футболка, шорти, легка сукня та відкрите взуття."
        
    return advice

# ==================== РОБОТА З БАЗОЮ ДАНИХ ====================

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clothes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            file_id TEXT NOT NULL,
            description TEXT NOT NULL,
            category TEXT DEFAULT 'Інше',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# ==================== КЛАВІАТУРА ТА ОБРОБНИКИ БОТА ====================

# Створюємо просте меню для користувача
main_menu = ReplyKeyboardMarkup(resize_keyboard=True)
main_menu.add(KeyboardButton("🌤 Що мені одягти?"))

@dp.message_handler(commands=['start'])
async def send_welcome(message):
    await message.answer(
        "👋 Привіт! Я твій персональний розумний гардероб.\n"
        "Натисни кнопку нижче, щоб отримати пораду щодо одягу за поточною погодою!",
        reply_markup=main_menu
    )

@dp.message_handler(Text(equals="🌤 Що мені одягти?"))
async def give_advice(message):
    # Отримуємо погоду (можна замінити на ваше місто, наприклад, "Lviv")
    weather = get_weather("Kyiv")
    # Генеруємо текстову пораду без залучення Groq/Llama
    recommendation = get_recommendation_by_weather(weather)
    
    await message.answer(recommendation)

# ==================== ЗАПУСК БОТА (ДЛЯ НОВИХ ВЕРСІЙ PYTHON) ====================

if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        logging.info("Бот успішно стартував без ШІ!")
        executor.start_polling(dp, skip_updates=True, loop=loop)
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот зупинений користувачем!")



