import asyncio
import logging
import threading
import os
from http.server import SimpleHTTPRequestHandler, HTTPServer

from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher.filters.builtin import Text  # Виправлено імпорт фільтру
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

import config
import database
import weather
import ai_stylist

# Безпечний Dummy-сервер для проходження Health Check на Render
class SafeHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"OK")

def run_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    try:
        server = HTTPServer(('', port), SafeHandler)
        print(f"🌍 Повноцінний Web App сервер запущено на порту {port}")
        server.serve_forever()
    except Exception as e:
        print(f"Помилка Dummy сервера: {e}")

threading.Thread(target=run_dummy_server, daemon=True).start()

logging.basicConfig(level=logging.INFO)
storage = MemoryStorage()
bot = Bot(token=config.TELEGRAM_TOKEN)
dp = Dispatcher(bot, storage=storage)

class OutfitStates(StatesGroup):
    waiting_for_event = State()

main_keyboard = ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
main_keyboard.row(KeyboardButton("🌤️ Що вдягнути сьогодні?"), KeyboardButton("⚙️ Змінити місто"))

@dp.message_handler(commands=['start'], state="*")
async def cmd_start(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("Привіт! Я твій Розумний Гардероб 🤖", reply_markup=main_keyboard)

@dp.message_handler(Text(equals="🌤️ Що вдягнути сьогодні?"), state="*")
async def ask_for_event(message: types.Message, state: FSMContext):
    await state.finish()
    await OutfitStates.waiting_for_event.set()
    await message.answer("Куди ви збираєтесь?")

@dp.message_handler(state=OutfitStates.waiting_for_event)
async def process_event_and_get_outfit(message: types.Message, state: FSMContext):
    event = message.text
    await state.finish()
    user_id = message.from_user.id
    user_city = database.get_user_city(user_id) or "Lviv"
    
    weather_data = weather.get_weather(city=user_city)
    raw_items = database.get_user_wardrobe(user_id)
    full_recommendation = ai_stylist.generate_outfit_recommendation(weather_data, raw_items, event)
    
    await message.answer(f"📍 **Погода {user_city}:**\n\n{full_recommendation}", parse_mode="Markdown")

async def main():
    try:
        await dp.start_polling()
    finally:
        await bot.close()

if __name__ == '__main__':
    asyncio.run(main())


    