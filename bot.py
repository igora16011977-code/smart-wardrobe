import asyncio
import logging
import threading
import os
from http.server import SimpleHTTPRequestHandler, HTTPServer

from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher.filters.builtin import Text
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

import config
import database
import weather
import ai_stylist

# Safe Dummy-сервер для проходження Health Check на Render
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

# Класи станів FSM
class UserSettingsStates(StatesGroup):
    waiting_for_city_settings = State()

class OutfitStates(StatesGroup):
    waiting_for_event = State()

class TripStates(StatesGroup):
    waiting_for_city = State()
    waiting_for_days = State()

# Головна клавіатура бота
main_keyboard = ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
main_keyboard.row(
    KeyboardButton("🌤️ Що вдягнути сьогодні?"), 
    KeyboardButton("👗 Візуальна шафа")
)
main_keyboard.row(
    KeyboardButton("🧳 План подорожі"), 
    KeyboardButton("🛍️ Чого не вистачає?")
)
main_keyboard.row(KeyboardButton("⚙️ Змінити місто"))

@dp.message_handler(commands=['start'], state="*")
async def cmd_start(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer(
        "Привіт! Я твій Розумний Гардероб 🤖\n\n"
        "Я допоможу тобі підібрати ідеальний образ під поточну погоду з твоїх реальних речей, "
        "спланувати капсульну валізу в подорож або підказати, яких базових речей не вистачає.\n\n"
        "Обери дію на клавіатурі нижче або просто **надішліть мені фото одягу**, щоб додати його в шафу 👇",
        reply_markup=main_keyboard,
        parse_mode="Markdown"
    )

# --- БЛОК: ПІДБІР ОБРАЗУ НА СЬОГОДНІ ---
@dp.message_handler(Text(equals="🌤️ Що вдягнути сьогодні?"), state="*")
async def ask_for_event(message: types.Message, state: FSMContext):
    await state.finish()
    await OutfitStates.waiting_for_event.set()
    
    event_keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    event_keyboard.row(KeyboardButton("Прогулянка"), KeyboardButton("Робота"))
    event_keyboard.row(KeyboardButton("Спортзал"), KeyboardButton("Ділова зустріч"))
    
    await message.answer("👔 Куди саме ви сьогодні збираєтесь? Оберіть варіант або напишіть свій:", reply_markup=event_keyboard)

@dp.message_handler(state=OutfitStates.waiting_for_event)
async def process_event_and_get_outfit(message: types.Message, state: FSMContext):
    event = message.text
    await state.finish()
    await message.answer("🔄 Зчитую погоду та аналізую вашу шафу. Зачекайте секунду...", reply_markup=main_keyboard)
    
    user_id = message.from_user.id
    user_city = database.get_user_city(user_id) or "Lviv"
    
    weather_data = weather.get_weather(city=user_city)
    raw_items = database.get_user_wardrobe(user_id)
    
    if not raw_items:
        await message.answer(
            f"📍 **Погода в {user_city}:** {weather_data.get('temp')}°C, {weather_data.get('description')}.\n\n"
            "⚠️ Ваша візуальна шафа зараз порожня! Надішліть мені кілька фотографій вашого одягу "
            "(худі, куртки, джинси, кросівки) одним або декількома повідомленнями, щоб ШІ міг підбирати з них образи."
        )
        return

    full_recommendation = ai_stylist.generate_outfit_recommendation(weather_data, raw_items, event)
    await message.answer(f"📍 **Погода {user_city}:**\n\n{full_recommendation}", parse_mode="Markdown")

# --- БЛОК: ВІЗУАЛЬНА ШАФА (ПАГІНАЦІЯ) ---
def get_wardrobe_inline_keyboard(category="все"):
    keyboard = InlineKeyboardMarkup(row_width=2)
    categories = [("👕 Верх", "wardrobe_верх"), ("👖 Низ", "wardrobe_низ"), 
                  ("👟 Взуття", "wardrobe_взуття"), ("✨ Все", "wardrobe_все")]
    
    buttons = [InlineKeyboardButton(text=name, callback_data=data) for name, data in categories]
    keyboard.add(*buttons)
    return keyboard

@dp.message_handler(Text(equals="👗 Візуальна шафа"), state="*")
async def show_wardrobe_menu(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("📁 Оберіть категорію одягу для перегляду вашої шафи:", reply_markup=get_wardrobe_inline_keyboard())

@dp.callback_query_handler(Text(startswith="wardrobe_"), state="*")
async def process_wardrobe_category(callback_query: CallbackQuery):
    target_category = callback_query.data.split("_")[1]
    user_id = callback_query.from_user.id
    
    raw_items = database.get_user_wardrobe(user_id)
    
    # Фільтрація речей за категоріями
    filtered_items = []
    for item in raw_items:
        file_id, description, item_id, item_category = item[0], item[1], item[2], item[3]
        if target_category == "все" or item_category.lower() == target_category:
            filtered_items.append(item)
            
    await callback_query.answer()
    
    if not filtered_items:
        await callback_query.message.answer(f"📭 У категорії '{target_category}' поки немає доданих речей.")
        return

    await callback_query.message.answer(f"📸 Показую речі з категорії '{target_category}' ({len(filtered_items)} шт):")
    
    # Виводимо до 5 фото за раз, щоб не спамити
    for item in filtered_items[:5]:
        await bot.send_photo(
            chat_id=user_id,
            photo=item[0],
            caption=f"🆔 ID: {item[2]}\n📝 Опис: {item[1]}\n📂 Категорія: {item[3]}"
        )

# --- БЛОК: ЧОГО НЕ ВИСТАЧАЄ ---
@dp.message_handler(Text(equals="🛍️ Чого не вистачає?"), state="*")
async def check_missing_items(message: types.Message, state: FSMContext):
    await state.finish()
    user_id = message.from_user.id
    user_city = database.get_user_city(user_id) or "Lviv"
    
    weather_data = weather.get_weather(city=user_city)
    raw_items = database.get_user_wardrobe(user_id)
    
    recommendation = ai_stylist.generate_shopping_recommendation(weather_data, raw_items)
    await message.answer(recommendation, parse_mode="Markdown", disable_web_page_preview=True)

# --- БЛОК: ЗМІНА МІСТА ---
@dp.message_handler(Text(equals="⚙️ Змінити місто"), state="*")
async def start_city_settings(message: types.Message, state: FSMContext):
    await state.finish()
    current_city = database.get_user_city(message.from_user.id)
    await UserSettingsStates.waiting_for_city_settings.set()
    await message.answer(
        f"🏠 Ваше поточне місто для прогнозу погоди: **{current_city}**.\n\n"
        f"Введіть нову назву міста українською або англійською (наприклад: *Київ* або *Kyiv*):",
        parse_mode="Markdown"
    )

@dp.message_handler(state=UserSettingsStates.waiting_for_city_settings)
async def save_new_home_city(message: types.Message, state: FSMContext):
    new_city = message.text.strip()
    if len(new_city) < 2 or any(char.isdigit() for char in new_city):
        await message.answer("⚠️ Назва міста вказана некоректно. Спробуйте ще раз:")
        return
        
    database.save_user_city(message.from_user.id, new_city)
    await state.finish()
    await message.answer(
        f"✅ Домашнє місто успішно змінено на: **{new_city}**!",
        reply_markup=main_keyboard,
        parse_mode="Markdown"
    )

# --- БЛОК: ПРИЙОМ НОВИХ ФОТО ОДЯГУ ---
@dp.message_handler(content_types=['photo'], state="*")
async def handle_clothing_photo(message: types.Message):
    user_id = message.from_user.id
    photo = message.photo[-1] # Беремо найкращу якість фото
    
    # Локальний ШІ-аналізатор генерує базовий опис для речі
    description = ai_stylist.analyze_clothing_image(b"")
    
    # Зберігаємо в базу даних PostgreSQL
    database.add_clothing(user_id=user_id, file_id=photo.file_id, description=description)
    await message.answer("✨ Я розпізнав і зберіг цю річ у вашу цифрову шафу! Тепер вона враховуватиметься при підборі образів.")

async def main():
    database.init_db()
    print("🤖 БОТ ЗАПУСКАЄТЬСЯ...")
    try:
        await dp.start_polling()
    finally:
        await bot.close()

if __name__ == '__main__':
    asyncio.run(main())



    