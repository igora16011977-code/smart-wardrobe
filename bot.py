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

# Web-сервер для проходження Health Check
class SafeHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def run_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    try:
        server = HTTPServer(('', port), SafeHandler)
        server.serve_forever()
    except Exception:
        pass

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

class EditStates(StatesGroup):
    waiting_for_new_description = State()

# Головне естетичне меню бота 🕊️
main_keyboard = ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
main_keyboard.row(KeyboardButton("🌤️ Що вдягнути сьогодні?"), KeyboardButton("👗 Візуальна шафа"))
main_keyboard.row(KeyboardButton("🧳 План подорожі"), KeyboardButton("🛍️ Чого не вистачає?"))
main_keyboard.row(KeyboardButton("⚙️ Змінити місто"))

@dp.message_handler(commands=['start'], state="*")
async def cmd_start(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer(
        "Привіт, красуне! ✨ Я твій персональний Розумний Гардероб 🤖💕\n\n"
        "Я допоможу тобі підбирати найстильніші образи по шарах, збирати естетичні валізи у подорожі "
        "та підкажу, яких базових речей не вистачає твоїй кольоровій палітрі. 🧸🍰\n\n"
        "✨ **Просто надішли мені фото свого одягу**, щоб додати його у шафу, або скористайся кнопками меню нижче! 👇",
        reply_markup=main_keyboard,
        parse_mode="Markdown"
    )

# --- БЛОК 1: 🌤️ ЩО ВДЯГНУТИ СЬОГОДНІ ---
@dp.message_handler(Text(equals="🌤️ Що вдягнути сьогодні?"), state="*")
async def ask_for_event(message: types.Message, state: FSMContext):
    await state.finish()
    await OutfitStates.waiting_for_event.set()
    
    event_keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    event_keyboard.row(KeyboardButton("Школа/Університет 📚"), KeyboardButton("Спортзал 🤸‍♀️"))
    event_keyboard.row(KeyboardButton("Прогулянка/Побачення ☕️"), KeyboardButton("Робота/Офіс 💼"))
    
    await message.answer("💕 **Куди саме ти сьогодні збираєшся, серденько?** Обери варіант або напиши свій:", reply_markup=event_keyboard)

@dp.message_handler(state=OutfitStates.waiting_for_event)
async def process_event_and_get_outfit(message: types.Message, state: FSMContext):
    event = message.text
    await state.finish()
    await message.answer("🔮 *Дивлюсь у віконце на погоду та перебираю твою віртуальну шафу... Зачекай хвилиночку!* ✨", reply_markup=main_keyboard, parse_mode="Markdown")
    
    user_id = message.from_user.id
    user_city = database.get_user_city(user_id)
    
    weather_data = weather.get_weather(city=user_city)
    raw_items = database.get_user_wardrobe(user_id, "все")
    
    if not raw_items:
        await message.answer(
            f"📍 **Погода в {user_city}:** {weather_data.get('temp', 12)}°C, {weather_data.get('description', 'без опадів')}.\n\n"
            "⚠️ *Ой, твоя шафа порожня!* Надішли мені кілька фото твоїх улюблених речей "
            "(худі, курточки, джинси, кроси), щоб я могла скласти з них пошаровий образ! 💗"
        )
        return

    full_recommendation = ai_stylist.generate_outfit_recommendation(weather_data, raw_items, event)
    await message.answer(f"📍 **Твій індивідуальний лукбук ({user_city}):**\n\n{full_recommendation}", parse_mode="Markdown")

# --- БЛОК 2: 👗 ВІЗУАЛЬНА ШАФА (ГОРТАННЯ) ---
def get_categories_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("👚 Верх", callback_data="ward_верх"),
        InlineKeyboardButton("👖 Низ", callback_data="ward_низ"),
        InlineKeyboardButton("👟 Взуття", callback_data="ward_взуття"),
        InlineKeyboardButton("✨ Аксесуари", callback_data="ward_аксесуари")
    )
    return keyboard

@dp.message_handler(Text(equals="👗 Візуальна шафа"), state="*")
async def show_wardrobe_menu(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("🎀 **Яку поличку твого гардероба відкриваємо?**", reply_markup=get_categories_keyboard())

@dp.callback_query_handler(Text(startswith="ward_"), state="*")
async def process_category_view(callback_query: types.CallbackQuery):
    category = callback_query.data.split("_")[1]
    user_id = callback_query.from_user.id
    
    items = database.get_user_wardrobe(user_id, category)
    await callback_query.answer()
    
    if not items:
        await callback_query.message.answer(f"🍦 У категорії *'{category.upper()}'* поки немає доданих речей. Надішли мені фото!", parse_mode="Markdown")
        return
        
    await callback_query.message.delete()
    await send_wardrobe_gallery_item(user_id, items, 0, category)

async def send_wardrobe_gallery_item(chat_id: int, items: list, index: int, category: str):
    file_id, description, item_id, _ = items[index]
    
    keyboard = InlineKeyboardMarkup(row_width=2)
    
    # Стрілочки для красивого гортання речей 💝
    nav_row = []
    if index > 0:
        nav_row.append(InlineKeyboardButton("◀️ Попередня", callback_data=f"slide_{category}_{index-1}"))
    if index < len(items) - 1:
        nav_row.append(InlineKeyboardButton("▶️ Наступна", callback_data=f"slide_{category}_{index+1}"))
    if nav_row:
        keyboard.row(*nav_row)
        
    keyboard.row(
        InlineKeyboardButton("📝 Змінити опис", callback_data=f"change_{item_id}_{category}_{index}"),
        InlineKeyboardButton("🗑️ Видалити", callback_data=f"drop_{item_id}_{category}")
    )
    keyboard.row(InlineKeyboardButton("🔙 Назад до поличок", callback_data="go_to_cats"))
    
    caption = (
        f"🌸 Категорія: *{category.upper()}*\n"
        f"📄 Річ: `{index+1}` з `{len(items)}` \n\n"
        f"✨ *Опис:* {description}"
    )
    
    await bot.send_photo(
        chat_id=chat_id,
        photo=file_id,
        caption=caption,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

@dp.callback_query_handler(Text(startswith="slide_"), state="*")
async def navigate_gallery(callback_query: types.CallbackQuery):
    _, category, index_str = callback_query.data.split("_")
    index = int(index_str)
    user_id = callback_query.from_user.id
    
    items = database.get_user_wardrobe(user_id, category)
    await callback_query.answer()
    
    if items and index < len(items):
        await callback_query.message.delete()
        await send_wardrobe_gallery_item(user_id, items, index, category)

@dp.callback_query_handler(Text(equals="go_to_cats"), state="*")
async def return_to_categories(callback_query: types.CallbackQuery):
    await callback_query.answer()
    await callback_query.message.delete()
    await callback_query.message.answer("🎀 **Яку поличку твого гардероба відкриваємо?**", reply_markup=get_categories_keyboard())

# --- БЛОК 2.5: РЕДАГУВАННЯ ТА ВИДАЛЕННЯ ---
@dp.callback_query_handler(Text(startswith="drop_"), state="*")
async def delete_item_handler(callback_query: types.CallbackQuery):
    _, item_id_str, category = callback_query.data.split("_")
    item_id = int(item_id_str)
    user_id = callback_query.from_user.id
    
    database.delete_clothing(item_id, user_id)
    await callback_query.answer("Річ успішно видалена! 🌬️")
    await callback_query.message.delete()
    
    items = database.get_user_wardrobe(user_id, category)
    if items:
        await send_wardrobe_gallery_item(user_id, items, 0, category)
    else:
        await callback_query.message.answer("🧁 Поличка порожня!", reply_markup=get_categories_keyboard())

@dp.callback_query_handler(Text(startswith="change_"), state="*")
async def edit_description_handler(callback_query: types.CallbackQuery, state: FSMContext):
    _, item_id_str, category, index_str = callback_query.data.split("_")
    await callback_query.answer()
    
    await EditStates.waiting_for_new_description.set()
    await state.update_data(item_id=int(item_id_str), category=category, index=int(index_str), msg_id=callback_query.message.message_id)
    
    await callback_query.message.answer("✍ *Напиши мені новий естетичний опис для цієї речі:*", parse_mode="Markdown")

@dp.message_handler(state=EditStates.waiting_for_new_description)
async def save_new_description_handler(message: types.Message, state: FSMContext):
    new_desc = message.text.strip()
    data = await state.get_data()
    user_id = message.from_user.id
    
    database.update_clothing_description(data['item_id'], user_id, new_desc)
    try:
        await bot.delete_message(user_id, data['msg_id'])
    except Exception:
        pass
        
    await state.finish()
    await message.answer("✨ *Опис оновлено, а річ дбайливо перескладено!*", parse_mode="Markdown")
    
    items = database.get_user_wardrobe(user_id, data['category'])
    if items:
        await send_wardrobe_gallery_item(user_id, items, min(data['index'], len(items)-1), data['category'])

# --- БЛОК 3: 🧳 ПЛАН ПОДОРОЖІ ---

@dp.message_handler(Text(equals="🧳 План подорожі"), state="*")
async def start_trip_itinerary(message: types.Message, state: FSMContext):
    await state.finish()
    await TripStates.waiting_for_city.set()
    await message.answer("✈️ Ой, куди ми збираємось подорожувати? Напиши назву міста:")

@dp.message_handler(state=TripStates.waiting_for_city)
async def process_trip_city(message: types.Message, state: FSMContext):
    city = message.text.strip()
    await state.update_data(trip_city=city)
    await TripStates.waiting_for_days.set()
    await message.answer(f"🗺️ Романтично! Місто призначення: *{city}*. А на скільки днів ти туди вирушаєш?", parse_mode="Markdown")

@dp.message_handler(state=TripStates.waiting_for_days)
async def process_trip_days(message: types.Message, state: FSMContext):
    days_text = message.text.strip()
    if not days_text.isdigit() or int(days_text) <= 0:
        await message.answer("💖 Напиши, будь ласка, кількість днів циферками:")
        return
    
    days = int(days_text)
    data = await state.get_data()
    destination = data['trip_city']
    await state.finish()
    
    await message.answer(f"🧁 Збираю компактну валізу та планую Pinterest-аутфіти на кожен із {days} днів подорожі... ✨")
    
    user_id = message.from_user.id
    trip_weather = weather.get_weather(city=destination)
    weather_desc = f"{trip_weather.get('temp', 12)}°C, {trip_weather.get('description', 'чудова погода')}"
    
    wardrobe = database.get_user_wardrobe(user_id, "все")
    if not wardrobe:
        await message.answer("⚠️ Твоя шафа порожня! Додай спочатку фото речей, щоб я могла спакувати твою стильну валізу.")
        return
        
    itinerary = ai_stylist.generate_trip_itinerary(weather_desc, wardrobe, destination, days)
    await message.answer(f"🧳 Твій розумний гайд для мандрівки у *{destination}*:\n\n{itinerary}", parse_mode="Markdown")


# --- БЛОК 4: 🛍️ ЧОГО НЕ ВИСТАЧАЄ ---

@dp.message_handler(Text(equals="🛍️ Чого не вистачає?"), state="*")
async def check_missing_items(message: types.Message, state: FSMContext):
    await state.finish()
    user_id = message.from_user.id
    raw_items = database.get_user_wardrobe(user_id, "все")
    if not raw_items:
        await message.answer("🧸 Надішли мені спочатку хоча б 3-5 photoграфiй свого одягу, щоб я розпізнала твою улюблену кольорову палітру!")
        return
    
    await message.answer("🔎 Сканую твої речі, аналізую колірну гаму та підбираю ідеальні базові елементи... ☕️")
    recommendation = ai_stylist.generate_shopping_recommendation(raw_items)
    await message.answer(f"🛍️ *Твій Wish-list для ідеального гардероба:*\n\n{recommendation}", parse_mode="Markdown")


# --- БЛОК 5: ⚙️ ЗМІНИТИ МІСТО (ЗБЕРЕЖЕННЯ ПОСТІЙНО) ---

@dp.message_handler(Text(equals="⚙️ Змінити місто"), state="*")
async def start_city_settings(message: types.Message, state: FSMContext):
    await state.finish()
    current_city = database.get_user_city(message.from_user.id)
    await UserSettingsStates.waiting_for_city_settings.set()
    await message.answer(f"🏠 Твоє поточне затишне місто для прогнозу: *{current_city}*.\n\nНа яке місто ти хочеш його змінити?", parse_mode="Markdown")

@dp.message_handler(state=UserSettingsStates.waiting_for_city_settings)
async def save_new_home_city(message: types.Message, state: FSMContext):
    new_city = message.text.strip()
    database.save_user_city(message.from_user.id, new_city)
    await state.finish()
    await message.answer(f"✨ Супер! Тепер я постійно орієнтуюся на місто *{new_city}* 🌸", reply_markup=main_keyboard, parse_mode="Markdown")


# --- ПРИЙОМ НОВИХ ФОТО ---

@dp.message_handler(content_types=['photo'], state="*")
async def handle_clothing_photo(message: types.Message):
    user_id = message.from_user.id
    photo = message.photo[-1]
    status = await message.reply("🔮 Приміряю річ на твою цифрову поличку...")
    description = ai_stylist.analyze_clothing_image(b"")
    
    database.add_clothing(user_id=user_id, file_id=photo.file_id, description=description)
    await status.edit_text(f"✨ Ура! Річ успішно додано!\nАвтоматичний аналіз: _{description}_. Тепер вона бере участь у підборах образу! 🎀", parse_mode="Markdown")


# --- ГОЛОВНИЙ СТАРТ БОТА ---

async def main():
    database.init_db()
    try:
        await dp.start_polling()
    finally:
        await bot.close()

if __name__ == '__main__':
    asyncio.run(main())
