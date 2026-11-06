import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher.filters import Text
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, WebAppInfo
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

import config
import database
import weather
import ai_stylist

import threading
from http.server import SimpleHTTPRequestHandler, HTTPServer
import os

def run_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    server_address = ('', port)
    httpd = HTTPServer(server_address, SimpleHTTPRequestHandler)
    print(f"🌍 Повноцінний Web App сервер запущено на порту {port}")
    httpd.serve_forever()

threading.Thread(target=run_dummy_server, daemon=True).start()

logging.basicConfig(level=logging.INFO)

storage = MemoryStorage()
bot = Bot(token=config.TELEGRAM_TOKEN)
dp = Dispatcher(bot, storage=storage)

class UserSettingsStates(StatesGroup):
    waiting_for_city_settings = State()

class OutfitStates(StatesGroup):
    waiting_for_event = State()

class TripStates(StatesGroup):
    waiting_for_city = State()
    waiting_for_days = State()

class EditStates(StatesGroup):
    waiting_for_new_name = State()

main_keyboard = ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
web_app_link = "https://github.io"

main_keyboard.row(
    KeyboardButton("🌤️ Що вдягнути сьогодні?"), 
    KeyboardButton("👗 Візуальна шафа", web_app=WebAppInfo(url=web_app_link))
)
main_keyboard.row(
    KeyboardButton("🧳 Планування подорожі"), 
    KeyboardButton("🛍️ Чого не вистачає?")
)
main_keyboard.row(
    KeyboardButton("⚙️ Змінити місто")
)

event_keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
event_keyboard.add(
    KeyboardButton("Робота"), KeyboardButton("Школа"),
    KeyboardButton("Спортзал"), KeyboardButton("Ділова зустріч")
)

@dp.message_handler(Text(equals="⚙️ Змінити місто"), state="*")
async def start_city_settings(message, state: FSMContext):
    await state.finish()
    current_city = database.get_user_city(message.from_user.id)
    await UserSettingsStates.waiting_for_city_settings.set()
    await message.answer(
        f"🏠 Зараз ваше домашнє місто: **{current_city}**.\n\n"
        f"Введіть нову назву міста українською або англійською мовою (наприклад: *Київ*, *Odesa*, *Берлін*):",
        parse_mode="Markdown"
    )

@dp.message_handler(state=UserSettingsStates.waiting_for_city_settings)
async def save_new_home_city(message, state: FSMContext):
    new_city = message.text.strip()
    if len(new_city) < 2 or any(char.isdigit() for char in new_city):
        await message.answer("⚠️ Назва міста вказана некоректно. Будь ласка, введіть правильну назву без цифр:")
        return
    user_id = message.from_user.id
    database.save_user_city(user_id, new_city)
    await state.finish()
    await message.answer(
        f"✅ Домашнє місто успішно змінено на: **{new_city}**!\n"
        f"Тепер щоденні підбори одягу будуть орієнтуватися на погоду тут.",
        reply_markup=main_keyboard,
        parse_mode="Markdown"
    )

@dp.message_handler(commands=['reset_menu'], state="*")
async def cmd_reset_menu(message):
    await message.answer("🧹 Очищую застарілий кеш інтерфейсу...", reply_markup=ReplyKeyboardRemove())
    await asyncio.sleep(1)
    await message.answer("✨ Кнопки успішно оновлено!", reply_markup=main_keyboard)

@dp.message_handler(commands=['start'], state="*")
async def cmd_start(message):
    database.init_db()
    await message.answer(
        "Привіт! Я твій Розумний Гардероб 🤖\nОбери дію на клавіатурі ниже:",
        reply_markup=main_keyboard
    )

@dp.message_handler(Text(equals="👗 Мій гардероб"), state="*")
async def show_wardrobe_menu(message):
    user_id = message.from_user.id
    current_style = database.get_user_style(user_id)
    category_kb = InlineKeyboardMarkup(row_width=1)
    web_app_url = f"https://github.io{user_id}&style={current_style}"
    category_kb.add(
        InlineKeyboardButton("✨ Відкрити візуальну шафу (Web App)", web_app_info=WebAppInfo(url=web_app_url))
    )
    category_kb.row(
        InlineKeyboardButton("👕 Верх", callback_data="filter_category_верх"),
        InlineKeyboardButton("👖 Низ", callback_data="filter_category_низ")
    )
    category_kb.row(InlineKeyboardButton("📦 Весь гардероб", callback_data="filter_category_все"))
    await message.answer("📁 Оберіть формат перегляду гардероба:", reply_markup=category_kb)

def _filter_items_by_category(raw_items, category_target):
    if category_target == "все":
        return raw_items
    filtered = []
    for item in raw_items:
        desc_lower = (item if isinstance(item, (tuple, list)) and len(item) > 1 else str(item)).lower()
        if category_target == "верх" and any(w in desc_lower for w in ["худі", "футболка", "кофта", "олімпійка", "зіпка", "лонгслів", "светр"]):
            filtered.append(item)
        elif category_target == "низ" and any(w in desc_lower for w in ["джинси", "штани", "bрюки", "карго", "джоггери"]):
            filtered.append(item)
    return filtered

@dp.callback_query_handler(lambda c: c.data.startswith('filter_category_') or (c.data.startswith('page_') and c.data != 'page_back_to_menu'), state="*")
async def process_wardrobe_navigation(callback_query: CallbackQuery):
    data_parts = callback_query.data.split('_')
    user_id = callback_query.from_user.id
    raw_items = database.get_user_wardrobe(user_id)
    
    if data_parts[0] == "filter":
        category_target = data_parts[2]
        items = _filter_items_by_category(raw_items, category_target)
        if not items:
            await bot.answer_callback_query(callback_query.id, text="У цій категорії поки немає речей.")
            return
        current_index = 0
        is_first_open = True
    else:
        action = data_parts[1]
        category_target = data_parts[2]
        current_index = int(data_parts[3])
        items = _filter_items_by_category(raw_items, category_target)
        is_first_open = False
        if action == "next":
            current_index = 0 if current_index + 1 >= len(items) else current_index + 1
        elif action == "prev":
            current_index = len(items) - 1 if current_index - 1 < 0 else current_index - 1

    if not items:
        await bot.answer_callback_query(callback_query.id, text="Категорія порожня.")
        return

    item = items[current_index]
    file_id = item[0] if isinstance(item, (tuple, list)) else item
    desc = item[1] if isinstance(item, (tuple, list)) and len(item) > 1 else "Одяг"

    inline_kb = InlineKeyboardMarkup(row_width=2)
    inline_kb.row(
        InlineKeyboardButton("⬅️ Назад", callback_data=f"page_prev_{category_target}_{current_index}"),
        InlineKeyboardButton(f"{current_index + 1} / {len(items)}", callback_data="page_noop"),
        InlineKeyboardButton("Вперед ➡️", callback_data=f"page_next_{category_target}_{current_index}")
    )
    
    if is_first_open:
        try:
            await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
            await bot.send_photo(chat_id=user_id, photo=file_id, caption=f"✨ {desc}", reply_markup=inline_kb)
        except Exception:
            await bot.send_message(chat_id=user_id, text=f"✨ {desc}", reply_markup=inline_kb)
    else:
        from aiogram.types import InputMediaPhoto
        try:
            await bot.edit_message_media(media=InputMediaPhoto(media=file_id, caption=f"✨ {desc}"), chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id, reply_markup=inline_kb)
        except Exception:
            pass
    await callback_query.answer()

@dp.message_handler(Text(equals="🌤️ Що вдягнути сьогодні?"), state="*")
async def ask_for_event(message, state: FSMContext):
    await OutfitStates.waiting_for_event.set()
    await message.answer("Куди ви збираєтесь?", reply_markup=event_keyboard)

@dp.message_handler(state=OutfitStates.waiting_for_event)
async def process_event_and_get_outfit(message, state: FSMContext):
    event = message.text
    await state.finish()
    await message.answer(f"🔄 Аналізую гардероб...", reply_markup=main_keyboard)
    
    user_id = message.from_user.id
    user_city = database.get_user_city(user_id) or "Lviv"
    weather_data = weather.get_weather(city=user_city)
    raw_items = database.get_user_wardrobe(user_id)

    full_recommendation = ai_stylist.generate_outfit_recommendation(weather_data, raw_items, event)
    await message.answer(f"📍 **Погода {user_city}:**\n\n{full_recommendation}", parse_mode="Markdown")

@dp.message_handler(Text(equals="🧳 Планування подорожі"), state="*")
async def start_trip_planning(message, state: FSMContext):
    await TripStates.waiting_for_city.set()
    await message.answer("✈️ Введіть місто, куди ви вирушаєте (наприклад: Київ, Одеса, Берлін):")

@dp.message_handler(state=TripStates.waiting_for_city)
async def process_trip_city(message, state: FSMContext):
    city = message.text.strip()
    await state.update_data(chosen_city=city)
    await TripStates.waiting_for_days.set()
    await message.answer(f"📅 На скільки днів планується поїздка у місто {city}? (Введіть число від 1 до 5):")

@dp.message_handler(state=TripStates.waiting_for_days)
async def process_trip_days(message, state: FSMContext):
    days_text = message.text.strip()
    if not days_text.isdigit() or not (1 <= int(days_text) <= 5):
        await message.answer("⚠️ Будь ласка, введіть число днів від 1 до 5:")
        return

    days_count = int(days_text)
    user_data = await state.get_data()
    city = user_data['chosen_city']
    await state.finish()

    await message.answer(f"🔄 Збираю компактну капсулу...", reply_markup=main_keyboard)
        # Продовження функції process_trip_days
    forecast_data = weather.get_weather_forecast(city)
    raw_items = database.get_user_wardrobe(message.from_user.id)
    
    # Витягуємо чистий опис речі з кортежу (file_id, description, id, category)
    clean_items_for_ai = [item[1] if isinstance(item, (tuple, list)) and len(item) > 1 else str(item) for item in raw_items]
    
    trip_plan = ai_stylist.generate_trip_itinerary(forecast_data, clean_items_for_ai, f"Поїздка в місто {city} на {days_count} днів.")
    await message.answer(trip_plan, parse_mode="Markdown")


@dp.message_handler(Text(equals="🛍️ Чого не вистачає?"), state="*")
async def check_wardrobe_gaps(message):
    user_id = message.from_user.id
    raw_items = database.get_user_wardrobe(user_id)
    user_city = database.get_user_city(user_id) or "Lviv"
    weather_data = weather.get_weather(city=user_city)
    
    shopping_list = ai_stylist.generate_shopping_recommendation(weather_data, raw_items)
    await message.answer(shopping_list, parse_mode="Markdown")


@dp.message_handler(content_types=['photo'], state="*")
async def handle_clothing_photo(message):
    photo = message.photo[-1]
    description = ai_stylist.analyze_clothing_image(b"")
    database.add_clothing(user_id=message.from_user.id, file_id=photo.file_id, description=description)
    await message.answer(f"✅ Додано!\nОпис: {description}")


async def run_bot():
    database.init_db()
    print("🤖 БОТ ЗАПУСКАЄТЬСЯ...")
    try:
        await dp.start_polling()
    finally:
        await dp.storage.close()
        await bot.close()


if __name__ == "__main__":
    asyncio.run(run_bot())

    
