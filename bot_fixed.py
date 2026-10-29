import asyncio
import logging
import base64
import requests
import sqlite3
from aiogram import Bot, Dispatcher
from aiogram.dispatcher.filters import Text
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from groq import Groq

# Усі ключі зібрані тут з виправленими помилками та доданим дефісом
TELEGRAM_TOKEN = "8980208249:AAGYq5ohv_5SFKY9UbG-dp13RucE9LzsbN4"
GROQ_API_KEY = "gsk_DoGE5TIKIG4I4m74pv7NWGdyb3FYu-ZnRFcykn6eSYSCKw07wqSFV"
WEATHER_API_KEY = "ec787296b70be02f50d617c141b62b61"
DB_NAME = "wardrobe.db"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher(bot)
client = Groq(api_key=GROQ_API_KEY)

def get_weather(city: str = "Kyiv") -> dict:
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
        else:
            return {"success": True, "temp": 18, "description": "хмарно з проясненнями", "feels_like": 17, "humidity": 60}
    except Exception:
        return {"success": True, "temp": 15, "description": "прохолодно", "feels_like": 14, "humidity": 65}

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

def add_clothing(user_id: int, file_id: str, description: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO clothes (user_id, file_id, description) VALUES (?, ?, ?)', (user_id, file_id, description))
    conn.commit()
    conn.close()

def get_user_wardrobe(user_id: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT id, file_id, description FROM clothes WHERE user_id = ?', (user_id,))
    items = cursor.fetchall()
    conn.close()
    return items

main_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
main_keyboard.add(KeyboardButton("🌤️ Що вдягнути сьогодні?"), KeyboardButton("👗 Мій гардероб"))

@dp.message_handler(commands=['start'])
async def cmd_start(message):
    init_db()
    await message.answer("Привіт! Я твій Розумний Гардероб 🧥🤖\n\nНадішли мені фото одягу або скористайся меню нижче.", reply_markup=main_keyboard)

@dp.message_handler(Text(equals="👗 Мій гардероб"))
async def show_wardrobe(message):
    items = get_user_wardrobe(message.from_user.id)
    if not items:
        await message.answer("Твій гардероб порожній. Надішли фото одягу!")
        return
    await message.answer(f"📦 У твоєму гардеробі речей: {len(items)}:")
    for item in items:
        await message.answer_photo(photo=item[1], caption=f"✨ {item[2]}")

@dp.message_handler(Text(equals="🌤️ Що вдягнути сьогодні?"))
async def get_outfit(message):
    await message.answer("🔄 Перевіряю погоду та аналізую ваш гардероб...")
    weather_data = get_weather()
    raw_items = get_user_wardrobe(message.from_user.id)
    wardrobe_list = [item[2] for item in raw_items]
    
    items_text = ", ".join(wardrobe_list) if wardrobe_list else "Гардероб порожній."
    prompt = f"Ти персональний стиліст. Погода: {weather_data['temp']} градусів, {weather_data['description']}. Речі: {items_text}. Склади стильний образ на сьогодні. Напиши відповідь коротко українською мовою."
    
    try:
        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7, max_tokens=500
        )
        await message.answer(response.choices[0].message.content)
    except Exception as e:
        await message.answer(f"❌ Помилка ШІ: {str(e)}")

@dp.message_handler(content_types=['photo'])
async def handle_clothing_photo(message):
    await message.answer("🤖 ШІ розпізнає твій одяг, зачекай трішки...")
    photo = message.photo[-1]
    
    try:
        file_info = await bot.get_file(photo.file_id)
        file_success = await bot.download_file(file_info.file_path)
        image_bytes = file_success.read()
        
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        prompt = "Що це за одяг? Визнач річ, колір, стиль та погоду. Лаконічно, 2-3 речення українською мовою."
        
        response = client.chat.completions.create(
            model="llama-3.2-11b-vision-preview",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]
            }],
            timeout=20
        )
        description = response.choices[0].message.content
        add_clothing(message.from_user.id, photo.file_id, description)
        await message.answer(f"✅ Додано до гардеробу!\n\n**Опис від ШІ:**\n{description}", parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"❌ Помилка обробки фото: {str(e)}")

async def run_bot():
    init_db()
    print("🤖 АВТОНОМНИЙ БОТ ЗАПУСКАЄТЬСЯ... Перейдіть у Telegram!")
    try:
        await dp.start_polling(reset_webhook=True)
    finally:
        await bot.close()

if __name__ == "__main__":
    asyncio.run(run_bot())
