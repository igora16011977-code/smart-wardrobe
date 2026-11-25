import asyncio
import logging
import threading
import os
from io import BytesIO
from http.server import ThreadingHTTPServer

from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher.filters.builtin import Text
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

import config
import database
import weather
import ai_stylist
from web_server import WardrobeWebHandler


def run_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    try:
        # ThreadingHTTPServer не блокує наступні перевірки паралельними запитами.
        server = ThreadingHTTPServer(("0.0.0.0", port), WardrobeWebHandler)
        logging.info("HTTP health server запущено на 0.0.0.0:%s", port)
        server.serve_forever()
    except Exception:
        logging.exception("Помилка запуску HTTP health server")


threading.Thread(
    target=run_dummy_server,
    name="http-health-server",
    daemon=True,
).start()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
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
    waiting_for_new_description = State()

# Головне меню бота 🕊️
WEB_APP_URL = (os.getenv("WEB_APP_URL") or "").strip()

main_keyboard = ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
main_keyboard.row(KeyboardButton("🌤️ Що вдягнути сьогодні?"))
main_keyboard.row(KeyboardButton("🧳 План подорожі"), KeyboardButton("🛍️ Чого не вистачає?"))

# Постійна кнопка на нижній клавіатурі лише надсилає текст боту.
# Сам Mini App відкривається окремою inline-кнопкою, щоб Telegram передав initData.
if WEB_APP_URL:
    main_keyboard.row(KeyboardButton("👗 Відкрити візуальну шафу"))

main_keyboard.row(KeyboardButton("⚙️ Змінити місто"))

@dp.message_handler(Text(equals="👗 Відкрити візуальну шафу"), state="*")
async def open_visual_wardrobe(message: types.Message):
    if not WEB_APP_URL:
        await message.answer(
            "🌷 Зараз не вдається відкрити шафу. Спробуй, будь ласка, трохи пізніше."
        )
        return

    webapp_keyboard = InlineKeyboardMarkup().add(
        InlineKeyboardButton(
            "👗 Відкрити візуальну шафу",
            web_app=WebAppInfo(url=WEB_APP_URL)
        )
    )
    await message.answer(
        "🌸 Твоя шафа вже чекає!\n\nНатисни кнопку нижче, щоб переглянути свої речі та створювати нові образи. ✨",
        reply_markup=webapp_keyboard
    )


@dp.message_handler(commands=['start'], state="*")
async def cmd_start(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer(
        "♡ Привіт, красуне! Рада тебе бачити. 🌷\n\n"
        "Я — твій персональний fashion-помічник. Допоможу створювати гармонійні образи, "
        "планувати стильні подорожі та знаходити речі, яких бракує твоєму гардеробу. ✨\n\n"
        "**Почнімо з маленького кроку:** надішли фото одягу, щоб додати його до своєї шафи, "
        "або обери потрібний розділ у меню нижче. 💗",
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
    
    await message.answer("🌸 Який у тебе сьогодні план? Обери нагоду або напиши свій варіант — я підберу образ з урахуванням погоди. ✨", reply_markup=event_keyboard)

@dp.message_handler(state=OutfitStates.waiting_for_event)
async def process_event_and_get_outfit(message: types.Message, state: FSMContext):
    event = message.text
    await state.finish()
    await message.answer("🔮 *Зазирну в прогноз погоди та перегляну твою шафу. Зараз підберу для тебе образ...* ✨", reply_markup=main_keyboard, parse_mode="Markdown")
    
    user_id = message.from_user.id
    user_city = await asyncio.to_thread(database.get_user_city, user_id)
    
    weather_data = await asyncio.to_thread(weather.get_weather, user_city)
    raw_items = await asyncio.to_thread(database.get_user_wardrobe, user_id, "все")
    
    if not raw_items:
        await message.answer(
            f"📍 **Погода в {user_city}:** {weather_data.get('temp', 12)}°C, {weather_data.get('description', 'без опадів')}.\n\n"
            "🌷 У твоїй шафі поки замало речей для підбору образу. "
            "Надішли кілька фото улюбленого одягу — і я зможу скласти для тебе стильну комбінацію. 💗"
        )
        return

    full_recommendation = await asyncio.to_thread(
        ai_stylist.generate_outfit_recommendation, weather_data, raw_items, event
    )
    await message.answer(f"🌷 **Твій образ на сьогодні · {user_city}**\n\n{full_recommendation}", parse_mode="Markdown")

# --- БЛОК 2: 👗 ВІЗУАЛЬНА ШАФА (ГОРТАННЯ СТРІЛОЧКАМИ) ---
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
    await message.answer("🎀 **Яку частину гардероба хочеш переглянути?** Обирай свою поличку:", reply_markup=get_categories_keyboard())

@dp.callback_query_handler(Text(startswith="ward_"), state="*")
async def process_category_view(callback_query: types.CallbackQuery):
    category = callback_query.data.split("_")[1]
    user_id = callback_query.from_user.id
    
    items = await asyncio.to_thread(database.get_user_wardrobe, user_id, category)
    await callback_query.answer()
    
    if not items:
        await callback_query.message.answer(f"🌸 У розділі *«{category.upper()}»* поки порожньо. Надішли фото речі, і вона оселиться на цій поличці!", parse_mode="Markdown")
        return
        
    await callback_query.message.delete()
    await send_wardrobe_gallery_item(user_id, items, 0, category)

async def send_wardrobe_gallery_item(chat_id: int, items: list, index: int, category: str):
    file_id, description, item_id, _ = items[index]
    
    keyboard = InlineKeyboardMarkup(row_width=2)
    
    nav_row = []
    if index > 0:
        nav_row.append(InlineKeyboardButton("◀️ Попередня", callback_data=f"slide_{category}_{index-1}"))
    if index < len(items) - 1:
        nav_row.append(InlineKeyboardButton("▶️ Наступна", callback_data=f"slide_{category}_{index+1}"))
    if nav_row:
        keyboard.row(*nav_row)
        
    keyboard.row(
        InlineKeyboardButton("✍️ Змінити опис", callback_data=f"change_{item_id}_{category}_{index}"),
        InlineKeyboardButton("🗑️ Видалити", callback_data=f"drop_{item_id}_{category}")
    )
    keyboard.row(InlineKeyboardButton("🌷 До категорій", callback_data="go_to_cats"))
    
    caption = (
        f"🌸 *{category.upper()}*\n"
        f"♡ Річ {index+1} з {len(items)}\n\n"
        f"📝 *Про цю річ:* {description}"
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
    
    items = await asyncio.to_thread(database.get_user_wardrobe, user_id, category)
    await callback_query.answer()
    
    if items and index < len(items):
        await callback_query.message.delete()
        await send_wardrobe_gallery_item(user_id, items, index, category)

@dp.callback_query_handler(Text(equals="go_to_cats"), state="*")
async def return_to_categories(callback_query: types.CallbackQuery):
    await callback_query.answer()
    await callback_query.message.delete()
    await callback_query.message.answer("🎀 **Яку частину гардероба хочеш переглянути?** Обирай свою поличку:", reply_markup=get_categories_keyboard())

# --- БЛОК 2.5: РЕДАГУВАННЯ ТА ВИДАЛЕННЯ ---
@dp.callback_query_handler(Text(startswith="drop_"), state="*")
async def delete_item_handler(callback_query: types.CallbackQuery):
    _, item_id_str, category = callback_query.data.split("_")
    item_id = int(item_id_str)
    user_id = callback_query.from_user.id
    
    await asyncio.to_thread(database.delete_clothing, item_id, user_id)
    await callback_query.answer("Річ видалено з гардероба. 🌷")
    await callback_query.message.delete()
    
    items = await asyncio.to_thread(database.get_user_wardrobe, user_id, category)
    if items:
        await send_wardrobe_gallery_item(user_id, items, 0, category)
    else:
        await callback_query.message.answer("♡ Ця поличка тепер порожня.", reply_markup=get_categories_keyboard())

@dp.callback_query_handler(Text(startswith="change_"), state="*")
async def edit_description_handler(callback_query: types.CallbackQuery, state: FSMContext):
    _, item_id_str, category, index_str = callback_query.data.split("_")
    await callback_query.answer()
    
    await EditStates.waiting_for_new_description.set()
    await state.update_data(item_id=int(item_id_str), category=category, index=int(index_str), msg_id=callback_query.message.message_id)
    
    await callback_query.message.answer("✍️ *Який опис хочеш залишити для цієї речі?*\n\nНапиши його одним повідомленням — я збережу оновлення. 🌸", parse_mode="Markdown")

@dp.message_handler(state=EditStates.waiting_for_new_description)
async def save_new_description_handler(message: types.Message, state: FSMContext):
    new_desc = message.text.strip()
    data = await state.get_data()
    user_id = message.from_user.id
    
    await asyncio.to_thread(
        database.update_clothing_description, data['item_id'], user_id, new_desc
    )
    try:
        await bot.delete_message(user_id, data['msg_id'])
    except Exception:
        pass
        
    await state.finish()
    await message.answer("✨ *Опис оновлено!* Твоя річ знову на своєму місці. 💗", parse_mode="Markdown")
    
    items = await asyncio.to_thread(
        database.get_user_wardrobe, user_id, data['category']
    )
    if items:
        await send_wardrobe_gallery_item(user_id, items, min(data['index'], len(items)-1), data['category'])

from io import BytesIO
from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.builtin import Text
import database
import weather
import ai_stylist



async def send_long_message(message, text):
    """Надсилає довгий текст частинами без помилок Markdown."""
    max_length = 4000

    chunks = []
    current_chunk = ""

    for paragraph in text.split("\n"):
        if len(current_chunk) + len(paragraph) + 1 <= max_length:
            current_chunk += paragraph + "\n"
        else:
            if current_chunk.strip():
                chunks.append(current_chunk.strip())

            while len(paragraph) > max_length:
                chunks.append(paragraph[:max_length])
                paragraph = paragraph[max_length:]

            current_chunk = paragraph + "\n"

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    for chunk in chunks:
        await message.answer(chunk)


# --- БЛОК 3: 🧳 ПЛАН ПОДОРОЖІ ---

# Додано пропущений декоратор для кнопки
@dp.message_handler(Text(equals="🧳 План подорожі"), state="*")
async def start_trip_itinerary(message: types.Message, state: FSMContext):
    await state.finish()
    await TripStates.waiting_for_city.set()
    await message.answer("🧳 Куди вирушаємо? Напиши місто, для якого сплануємо твою стильну валізу. ✨")

@dp.message_handler(state=TripStates.waiting_for_city)
async def process_trip_city(message: types.Message, state: FSMContext):
    city = message.text.strip()
    await state.update_data(trip_city=city)
    await TripStates.waiting_for_days.set()
    await message.answer(f"🗺️ Чудовий вибір — *{city}*! На скільки днів плануємо подорож?", parse_mode="Markdown")

@dp.message_handler(state=TripStates.waiting_for_days)
async def process_trip_days(message: types.Message, state: FSMContext):
    days_text = message.text.strip()
    if not days_text.isdigit() or int(days_text) <= 0:
        await message.answer("💗 Напиши, будь ласка, кількість днів цифрами — наприклад, 4.")
        return
        
    days = int(days_text)
    data = await state.get_data()
    destination = data['trip_city']
    await state.finish()
    
    await message.answer(f"🧳 Планую твою подорож на {days} днів...\n\nПеревіряю погоду та добираю компактний гардероб і поєднання речей. ✨")
    
    user_id = message.from_user.id
    trip_weather = await asyncio.to_thread(weather.get_weather_forecast, destination)
    weather_desc = f"{trip_weather.get('temp', 12)}°C, {trip_weather.get('description', 'чудова погода')}"
    
    wardrobe = await asyncio.to_thread(database.get_user_wardrobe, user_id, "все")
    if not wardrobe:
        await message.answer("🌷 Спочатку додай до шафи кілька фото свого одягу. Тоді я зможу скласти валізу з речей, які вже маєш.")
        return
        
    itinerary = await asyncio.to_thread(
        ai_stylist.generate_trip_itinerary, weather_desc, wardrobe, destination, days
    )
    await send_long_message(
    message,
    f"🧳 Твоя стильна подорож до {destination}\n\n{itinerary}"
)


# --- БЛОК 4: 🛍️ ЧОГО НЕ ВИСТАЧАЄ ---

@dp.message_handler(Text(equals="🛍️ Чого не вистачає?"), state="*")
async def check_missing_items(message: types.Message, state: FSMContext):
    await state.finish()
    user_id = message.from_user.id
    raw_items = await asyncio.to_thread(database.get_user_wardrobe, user_id, "все")
    if not raw_items:
        await message.answer("🌸 Додай до гардероба хоча б 3–5 фото одягу. Так я зможу краще зрозуміти твою палітру та підказати, чого бракує.")
        return
        
    await message.answer("🔎 Переглядаю твій гардероб та аналізую кольори й поєднання...\n\nЗараз підготую список речей, які можуть його доповнити. 🌷")
    recommendation = await asyncio.to_thread(
        ai_stylist.generate_shopping_recommendation, raw_items
    )
    await message.answer(f"🛍️ *Ідеї для поповнення гардероба*\n\n{recommendation}", parse_mode="Markdown")


# --- БЛОК 5: ⚙️ ЗМІНИТИ МІСТО ---

@dp.message_handler(Text(equals="⚙️ Змінити місто"), state="*")
async def start_city_settings(message: types.Message, state: FSMContext):
    await state.finish()
    current_city = await asyncio.to_thread(database.get_user_city, message.from_user.id)
    await UserSettingsStates.waiting_for_city_settings.set()
    await message.answer(f"🏡 Зараз прогноз погоди налаштований для міста *{current_city}*.\n\nЯке місто вказати натомість?", parse_mode="Markdown")

@dp.message_handler(state=UserSettingsStates.waiting_for_city_settings)
async def save_new_home_city(message: types.Message, state: FSMContext):
    new_city = message.text.strip()
    await asyncio.to_thread(database.save_user_city, message.from_user.id, new_city)
    await state.finish()
    await message.answer(f"🌷 Готово! Тепер для прогнозу та підбору образів орієнтуватимуся на *{new_city}*.", reply_markup=main_keyboard, parse_mode="Markdown")


# --- ПРИЙОМ НОВИХ ФОТО (ІЗ ЗАВАНТАЖЕННЯМ БАЙТІВ ДЛЯ GEMINI) ---


@dp.message_handler(content_types=['photo'], state="*")
async def handle_clothing_photo(message: types.Message):
    user_id = message.from_user.id
    photo = message.photo[-1]

    status = await message.reply(
        "🔎 Розглядаю твою річ та визначаю її характеристики... 🌸"
    )

    try:
        logging.info(
            "Початок обробки фото користувача %s",
            user_id
        )

        photo_file = await bot.get_file(photo.file_id)

        photo_buffer = BytesIO()
        await bot.download_file(
            photo_file.file_path,
            photo_buffer
        )
        image_bytes = photo_buffer.getvalue()

        if not image_bytes:
            raise ValueError("Фотографія порожня.")

        logging.info(
            "Фото завантажено. Розмір: %s байтів",
            len(image_bytes)
        )

        logging.info("Починаю аналіз Gemini")

        clothing = await asyncio.wait_for(
            asyncio.to_thread(
                ai_stylist.analyze_clothing_image_structured,
                image_bytes
            ),
            timeout=150
        )

        title = clothing.get("title", "").strip()
        description = clothing.get("description", "").strip()
        category = clothing.get("category", "").strip()
        color = clothing.get("color", "").strip()
        material = clothing.get("material", "").strip()
        style = clothing.get("style", "").strip()

        logging.info(
            "Gemini завершив аналіз: title=%s, category=%s, color=%s, material=%s, style=%s",
            title, category, color, material, style
        )

        was_added = await asyncio.to_thread(
            database.add_clothing,
            user_id,
            photo.file_id,
            description,
            photo.file_unique_id,
            title,
            category,
            color,
            material,
            style,
        )

        if was_added:
            logging.info("Річ збережено в базі даних з усіма характеристиками")
            details = [
                f"♡ Назва: {title}",
                f"Категорія: {category or 'не визначено'}",
                f"Колір: {color or 'не визначено'}",
                f"Матеріал: {material or 'не визначено'}",
                f"Фасон: {style or 'не визначено'}",
            ]
            await status.edit_text(
                "🌷 *Нова річ у твоєму гардеробі!*\n\n"
                + "\n".join(details)
                + f"\n\n📝 Опис: {description}\n"
                + "Тепер ця річ доступна для створення нових образів. 🎀"
            )
        else:
            logging.info(
                "Повторне фото не додано: user_id=%s, file_id=%s",
                user_id,
                photo.file_id,
            )
            await status.edit_text(
                "♡ Ця річ уже є у твоєму гардеробі — повторно додавати її не потрібно. 💗"
            )

    except asyncio.TimeoutError:
        logging.error("Перевищено час очікування Gemini")
        await status.edit_text(
            "⏳ Фото обробляється довше, ніж очікувалося. Спробуй, будь ласка, ще раз трохи пізніше."
        )

    except Exception:
        logging.exception("Помилка обробки фотографії")
        await status.edit_text(
            "🌷 Не вдалося додати цю річ. Спробуй надіслати фото ще раз трохи пізніше."
        )

# --- ЗАПУСК БОТА ---

async def main():
    logging.info("Ініціалізація бази даних")
    await asyncio.to_thread(database.init_db)
    try:
        logging.info("Запуск Telegram polling; перевірте, що працює лише один екземпляр бота")
        await dp.start_polling()
    finally:
        logging.info("Зупинка Telegram polling")
        await bot.close()

if __name__ == '__main__': # Виправлено синтаксис dunder-змінних
    import asyncio
    asyncio.run(main()) 