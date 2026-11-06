import asyncio
import logging
from aiogram import Bot, Dispatcher, types  # Імпортуємо ВСЕ ОДРАЗУ в одному рядку
from aiogram.dispatcher.filters import Text
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, WebAppInfo
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

import subprocess
import sys

try:
    import openai
except ImportError:
    print("🤖 Бібліотеку openai не знайдено. Встановлюю примусово...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "openai"])
    import openai
    print("✅ Бібліотеку openai успішно встановлено прямо в процесі!")


import config
import database
import weather
import ai_stylist

import threading
import http.server
import socketserver
import os

# Замініть вашу функцію run_dummy_server або код Dummy-сервера на цей:
import threading
from http.server import SimpleHTTPRequestHandler, HTTPServer

def run_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    # Сервер автоматично шукатиме файл index.html у папці з ботом і показуватиме його
    server_address = ('', port)
    httpd = HTTPServer(server_address, SimpleHTTPRequestHandler)
    print(f"🌍 Повноцінний Web App сервер запущено на порту {port}")
    httpd.serve_forever()

# Переконайтеся, що в коді викликається:
# threading.Thread(target=run_dummy_server, daemon=True).start()


# Запускаємо сервер у фоновому потоці, щоб він не заважав роботу Telegram-бота
threading.Thread(target=run_dummy_server, daemon=True).start()


logging.basicConfig(level=logging.INFO)

storage = MemoryStorage()
bot = Bot(token=config.TELEGRAM_TOKEN)
dp = Dispatcher(bot, storage=storage)

# Додаємо новий стан до наявних класів станів
class UserSettingsStates(StatesGroup):
    waiting_for_city_settings = State()

# ГОЛОВНА КЛАВІАТУРА 2Х3 (ОНОВЛЕНА)
# ГОЛОВНА КЛАВІАТУРА 2Х3 (ОНОВЛЕНА З WEB APP)
main_keyboard = ReplyKeyboardMarkup(resize_keyboard=True, selective=True)

# Офіційний сайт Telegram для тестування Web App
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


# НОВА СТРОКА: Створюємо event_keyboard, якої не вистачало!
event_keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
event_keyboard.add(
    KeyboardButton("Робота"), KeyboardButton("Школа"),
    KeyboardButton("Спортзал"), KeyboardButton("Ділова зустріч")
)


class OutfitStates(StatesGroup):
    waiting_for_event = State()

class TripStates(StatesGroup):
    waiting_for_city = State()
    waiting_for_days = State()

class EditStates(StatesGroup):
    waiting_for_new_name = State()

# 1. Спрацьовує при натисканні на кнопку "⚙️ Змінити місто"
@dp.message_handler(Text(equals="⚙️ Змінити місто"), state="*")
async def start_city_settings(message, state: FSMContext):
    await state.finish()  # Скидаємо попередні стани, якщо вони були
    
    current_city = database.get_user_city(message.from_user.id)
    
    await UserSettingsStates.waiting_for_city_settings.set()
    await message.answer(
        f"🏠 Зараз ваше домашнє місто: **{current_city}**.\n\n"
        f"Введіть нову назву міста українською або англійською мовою (наприклад: *Київ*, *Odesa*, *Берлін*):",
        parse_mode="Markdown"
    )

# 2. Обробка та збереження введеного міста
@dp.message_handler(state=UserSettingsStates.waiting_for_city_settings)
async def save_new_home_city(message, state: FSMContext):
    new_city = message.text.strip()
    
    if len(new_city) < 2 or any(char.isdigit() for char in new_city):
        await message.answer("⚠️ Назва міста вказана некоректно. Будь ласка, введіть правильну назву без цифр:")
        return

    user_id = message.from_user.id
    
    # Зберігаємо місто в базу даних
    database.save_user_city(user_id, new_city)
    await state.finish()  # Закриваємо стан
    
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
        "Привіт! Я твій Розумний Гардероб 🤖\nОбери дію на клавіатурі нижче:",
        reply_markup=main_keyboard
    )

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

@dp.message_handler(Text(equals="👗 Мій гардероб"), state="*")
async def show_wardrobe_menu(message):
    # Отримуємо ID користувача та його поточний стиль із бази даних
    user_id = message.from_user.id
    current_style = database.get_user_style(user_id)
    
    # Створюємо Inline-клавіатуру
    category_kb = InlineKeyboardMarkup(row_width=1)
    
    # КНОПКА WEB APP: Вона відкриває повноцінне вікно всередині Telegram
    # Передаємо user_id та стиль як параметри, щоб сайт знав, чий гардероб відкривати
    web_app_url = f"https://github.io{user_id}&style={current_style}"
    
    category_kb.add(
        InlineKeyboardButton("✨ Відкрити візуальну шафу (Web App)", web_app_info=WebAppInfo(url=web_app_url))
    )
    
    # Залишаємо ваші старі кнопки нижче, як альтернативу
    category_kb.row(
        InlineKeyboardButton("👕 Верх", callback_data="filter_category_верх"),
        InlineKeyboardButton("👖 Низ", callback_data="filter_category_низ")
    )
    category_kb.row(InlineKeyboardButton("📦 Весь гардероб", callback_data="filter_category_все"))
    
    await message.answer("📁 Оберіть формат перегляду гардероба:", reply_markup=category_kb)




@dp.callback_query_handler(lambda c: c.data.startswith('delete_'), state="*")
async def process_delete_clothing(callback_query: CallbackQuery):
    clothing_id = int(callback_query.data.split('_')[1])
    user_id = callback_query.from_user.id
    
    success = database.delete_clothing(user_id, clothing_id)
    if success:
        await bot.answer_callback_query(callback_query.id, text="🔥 Річ успішно видалено!")
        await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
    else:
        await bot.answer_callback_query(callback_query.id, text="⚠️ Помилка: річ не знайдено.")

@dp.callback_query_handler(lambda c: c.data.startswith('edit_'), state="*")
async def process_edit_clothing(callback_query: CallbackQuery, state: FSMContext):
    clothing_id = int(callback_query.data.split('_')[1])
    
    await state.update_data(editing_item_id=clothing_id)
    await EditStates.waiting_for_new_name.set()
    
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(
        chat_id=callback_query.message.chat.id, 
        text="📝 Введіть нову коротку назву (опис) для цієї речі українською мовою:"
    )

def _filter_items_by_category(raw_items, category_target):
    """Допоміжна функція для фільтрації речей за категоріями та ключовими словами."""
    if category_target == "все":
        return raw_items
        
    filtered = []
    for item in raw_items:
        desc_lower = (item[1] if isinstance(item, (tuple, list)) and len(item) > 1 else str(item)).lower()
        db_cat = (item[3] if isinstance(item, (tuple, list)) and len(item) > 3 else "Інше").lower()
        
        if category_target == "верх":
            if "верх" in db_cat or any(w in desc_lower for w in ["худі", "футболка", "кофта", "олімпійка", "зіпка", "лонгслів", "светр", "топ", "майка", "бодік", "костюмчик"]):
                filtered.append(item)

        elif category_target == "низ":
            if "низ" in db_cat or any(w in desc_lower for w in ["джинси", "штани", "брюки", "карго", "джоггери", "шорти", "спідниця"]):
                filtered.append(item)
        elif category_target == "взуття":
            if "взуття" in db_cat or any(w in desc_lower for w in ["кросівки", "взуття", "кеди", "черевики", "чоботи"]):
                filtered.append(item)
        elif category_target == "аксесуари":
            if "аксесуар" in db_cat or "прикрас" in db_cat or any(w in desc_lower for w in ["ланцюжок", "кулон", "підвіска", "кільце", "перстень", "браслет", "намисто", "парасоля", "годинник"]):
                filtered.append(item)
                
    return filtered

# ОНОВЛЕНИЙ ХЕНДЛЕР: Перевіряє, щоб callback НЕ був 'page_back_to_menu'
@dp.callback_query_handler(lambda c: c.data.startswith('filter_category_') or (c.data.startswith('page_') and c.data != 'page_back_to_menu'), state="*")
async def process_wardrobe_navigation(callback_query: CallbackQuery):
    data_parts = callback_query.data.split('_')
    user_id = callback_query.from_user.id
    raw_items = database.get_user_wardrobe(user_id)
    
    # 1. ОБРОБКА ВИБОРУ КАТЕГОРІЇ (Наприклад: filter_category_верх)
    if data_parts[0] == "filter":
        category_target = data_parts[2] # 'верх', 'низ', 'взуття', 'аксесуари', 'все'
        items = _filter_items_by_category(raw_items, category_target)
        
        if not items:
            await bot.answer_callback_query(callback_query.id, text=f"У категорії '{category_target.upper()}' поки немає речей.")
            return
            
        current_index = 0
        is_first_open = True
    
    # 2. ОБРОБКА ГОРТАННЯ КНОПКАМИ НАЗАД / ВПЕРЕД (Наприклад: page_next_верх_0)
    else:
        action = data_parts[1] # 'prev', 'next', 'noop'
        if action == "noop":
            await bot.answer_callback_query(callback_query.id)
            return
            
        category_target = data_parts[2]
        current_index = int(data_parts[3]) # Тепер тут суворо число, помилки не буде!
        items = _filter_items_by_category(raw_items, category_target)
        is_first_open = False
        
        if not items:
            await bot.answer_callback_query(callback_query.id, text="Категорія тепер порожня.")
            await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
            return
            
        if action == "next":
            current_index = 0 if current_index + 1 >= len(items) else current_index + 1
        elif action == "prev":
            current_index = len(items) - 1 if current_index - 1 < 0 else current_index - 1

    # Витягуємо дані поточної речі
    item = items[current_index]
    file_id = item[0] if isinstance(item, (tuple, list)) else item
    desc = item[1] if isinstance(item, (tuple, list)) and len(item) > 1 else "Одяг"
    item_id = item[2] if isinstance(item, (tuple, list)) and len(item) > 2 else None

    # Клавіатура пагінації з прив'язкою до обраної категорії
    inline_kb = InlineKeyboardMarkup(row_width=2)
    if item_id is not None:
        inline_kb.add(
            InlineKeyboardButton("✏️ Змінити назву", callback_data=f"edit_{item_id}"),
            InlineKeyboardButton("🗑️ Видалити", callback_data=f"delete_{item_id}")
        )
    inline_kb.row(
        InlineKeyboardButton("⬅️ Назад", callback_data=f"page_prev_{category_target}_{current_index}"),
        InlineKeyboardButton(f"{current_index + 1} / {len(items)}", callback_data="page_noop"),
        InlineKeyboardButton("Вперед ➡️", callback_data=f"page_next_{category_target}_{current_index}")
    )
    inline_kb.row(InlineKeyboardButton("📁 Назад до категорій", callback_data="page_back_to_menu"))

    if is_first_open:
        await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
        try:
            await bot.send_photo(chat_id=user_id, photo=file_id, caption=f"✨ {desc}", reply_markup=inline_kb)
        except Exception:
            await bot.send_message(chat_id=user_id, text=f"✨ {desc} (не вдалося завантажити зображення)", reply_markup=inline_kb)
    else:
        try:
            from aiogram.types import InputMediaPhoto
            await bot.edit_message_media(
                media=InputMediaPhoto(media=file_id, caption=f"✨ {desc}"),
                chat_id=callback_query.message.chat.id,
                message_id=callback_query.message.message_id,
                reply_markup=inline_kb
            )
        except Exception:
            await bot.edit_message_caption(
                chat_id=callback_query.message.chat.id,
                message_id=callback_query.message.message_id,
                caption=f"✨ {desc} (помилка оновлення)",
                reply_markup=inline_kb
            )
            
    await bot.answer_callback_query(callback_query.id)

# Окремий чистий хендлер для повернення в меню категорій
@dp.callback_query_handler(lambda c: c.data == 'page_back_to_menu', state="*")
async def back_to_categories_menu(callback_query: CallbackQuery):
    category_kb = InlineKeyboardMarkup(row_width=2)
    category_kb.add(
        InlineKeyboardButton("👕 Верх", callback_data="filter_category_верх"),
        InlineKeyboardButton("👖 Низ", callback_data="filter_category_низ"),
        InlineKeyboardButton("👟 Взуття", callback_data="filter_category_взуття"),
        InlineKeyboardButton("📿 Аксесуари", callback_data="filter_category_аксесуари")
    )
    category_kb.row(InlineKeyboardButton("📦 Весь гардероб", callback_data="filter_category_все"))
    
    await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
    await bot.send_message(chat_id=callback_query.from_user.id, text="📁 Обери категорію гардероба для перегляду:", reply_markup=category_kb)
    await callback_query.answer()


# Обробник кнопки повернення назад до вибору категорій
@dp.callback_query_handler(lambda c: c.data == 'page_back_to_menu', state="*")
async def back_to_categories_menu(callback_query: CallbackQuery):
    category_kb = InlineKeyboardMarkup(row_width=2)
    category_kb.add(
        InlineKeyboardButton("👕 Верх", callback_data="filter_category_верх"),
        InlineKeyboardButton("👖 Низ", callback_data="filter_category_низ"),
        InlineKeyboardButton("👟 Взуття", callback_data="filter_category_взуття"),
        InlineKeyboardButton("📿 Аксесуари", callback_data="filter_category_аксесуари")
    )
    category_kb.row(InlineKeyboardButton("📦 Весь гардероб", callback_data="filter_category_все"))
    
    await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
    await bot.send_message(chat_id=callback_query.from_user.id, text="📁 Обери категорію гардероба для перегляду:", reply_markup=category_kb)
    await callback_query.answer()



@dp.message_handler(state=EditStates.waiting_for_new_name)
async def save_new_clothing_name(message, state: FSMContext):
    new_name = message.text.strip()
    if len(new_name) < 2:
        await message.answer("⚠️ Назва занадто коротка. Будь ласка, введіть коректну назву речі:")
        return
        
    user_data = await state.get_data()
    clothing_id = user_data.get('editing_item_id')
    user_id = message.from_user.id
    await state.finish()
    
    success = database.update_clothing_description(user_id, clothing_id, new_name)
    if success:
        await message.answer(f"✅ Назву успішно змінено на:\n«{new_name}»", reply_markup=main_keyboard)
    else:
        await message.answer("⚠️ Не вдалося оновити назву. Можливо, річ вже видалена.", reply_markup=main_keyboard)

@dp.message_handler(Text(equals="🌤️ Що вдягнути сьогодні?"), state="*")
async def ask_for_event(message, state: FSMContext):
    raw_items = database.get_user_wardrobe(message.from_user.id)
    if not raw_items:
        await message.answer("Твій гардероб порожній! Завантаж спочатку фото свого одягу.")
        return
    await OutfitStates.waiting_for_event.set()
    await message.answer("Куди ви збираєтесь?", reply_markup=event_keyboard)


@dp.message_handler(state=OutfitStates.waiting_for_event)
async def process_event_and_get_outfit(message, state: FSMContext):
    event = message.text
    await state.finish()

    await message.answer(f"🔄 Аналізую гардероб, прораховую шари одягу та зчитую датчики погоди...", reply_markup=main_keyboard)
    
    user_id = message.from_user.id
    
    # 1. Безпечно дістаємо місто
    try:
        user_city = database.get_user_city(user_id) or "Lviv"
    except Exception:
        user_city = "Lviv"
        
    # 2. Безпечно отримуємо погоду
    try:
        weather_data = weather.get_weather(city=user_city)
    except Exception:
        weather_data = {"temp": 15, "feels_like": 14, "description": "мінлива хмарність", "city": user_city}
    
    # 3. Безпечно дістаємо речі з бази даних
    try:
        raw_items = database.get_user_wardrobe(user_id)
    except Exception as e:
        await message.answer(f"❌ Помилка доступу до бази даних гардеробу: {str(e)}")
        return

    if not raw_items:
        await message.answer("Твій гардероб порожній! Спочатку завантаж фото одягу.")
        return

    # 4. Викликаємо ШІ-стиліста з повним перехопленням помилок
    try:
        full_recommendation = ai_stylist.generate_outfit_recommendation(weather_data, raw_items, event)
    except Exception as e:
        await message.answer(f"❌ Помилка модуля ШІ стиліста: {str(e)}")
        return

    # Розбираємо технічну відповідь від Qwen
    clean_recommendation = full_recommendation
    chosen_ids = []
    
    if "ОДЯГНИ:" in full_recommendation:
        try:
            parts = full_recommendation.split("ОДЯГНИ:")
            clean_recommendation = parts[0].strip()
            raw_ids = parts[1].strip()
            if "немає" not in raw_ids.lower():
                chosen_ids = [int(x.strip()) for x in raw_ids.split(",") if x.strip().isdigit()]
        except Exception:
            clean_recommendation = full_recommendation

    # 5. Формуємо та надсилаємо звіт про погоду і вибір ШІ
    weather_report = (
        f"📍 <b>Погода у місті {weather_data.get('city', user_city)}:</b>\n"
        f"🌡️  Температура: {weather_data.get('temp', 15)}°C (відчувається як {weather_data.get('feels_like', 14)}°C)\n"
        f"☁️ Стан: {weather_data.get('description', 'мінлива хмарність')}\n\n"
        f"💡 <b>Рекомендація стиліста ({event}):</b>\n{clean_recommendation}"
    )
    
    try:
        await message.answer(weather_report, parse_mode="HTML")
    except Exception:
        # Резервний вивід без HTML-тегів, якщо ШІ згенерував поламані теги
        await message.answer(weather_report.replace("<b>", "").replace("</b>", ""))
    
    # 6. НАЙБІЛЬШ БЕЗПЕЧНИЙ ПОШУК ТА НАДСИЛАННЯ ФОТО
    if chosen_ids:
        photo_sent = False
        for item_id in chosen_ids:
            for item in raw_items:
                # Перевіряємо структуру елемента бази, щоб уникнути IndexError
                if isinstance(item, (tuple, list)) and len(item) >= 3:
                    db_file_id = item[0]
                    db_desc = item[1]
                    db_item_id = item[2] # Перевірте, чи правильно зчитується ID

                    
                    if db_item_id == item_id:
                        if not photo_sent:
                            await message.answer("👟 <b>Ось фото речей, які я підібрав для вашого образу:</b>", parse_mode="HTML")
                            photo_sent = True
                        try:
                            await bot.send_photo(chat_id=user_id, photo=db_file_id, caption=f"✨ {db_desc}")
                        except Exception:
                            pass  # Ігноруємо поламані або застарілі ID файлів у Telegram



@dp.message_handler(Text(equals="🧳 Планування подорожі"), state="*")
async def start_trip_planning(message, state: FSMContext):
    raw_items = database.get_user_wardrobe(message.from_user.id)
    if not raw_items:
        await message.answer("Твій гардероб порожній! Спочатку завантаж фото одягу.")
        return
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
        await message.answer("⚠️ Будь ласка, введіть число днів цифрами (від 1 до 5):")
        return

    days_count = int(days_text)
    user_data = await state.get_data()
    city = user_data['chosen_city']
    await state.finish()

    await message.answer(f"🔄 Аналізую прогноз погоди для м. {city} та збираю компактну капсулу...", reply_markup=main_keyboard)
    
    forecast_data = weather.get_weather_forecast(city)
    raw_items = database.get_user_wardrobe(message.from_user.id)
    
    clean_items_for_ai = []
    for item in raw_items:
        desc = item[1] if isinstance(item, (tuple, list)) and len(item) > 1 else str(item)
        clean_items_for_ai.append(desc)

    trip_plan = ai_stylist.generate_trip_itinerary(forecast_data, clean_items_for_ai, city, days_count)
    await message.answer(trip_plan, parse_mode="Markdown")

@dp.message_handler(Text(equals="🛍️ Чого не вистачає?"), state="*")
async def check_wardrobe_gaps(message):
    user_id = message.from_user.id
    
    try:
        # Отримуємо сирі кортежі з бази даних без попереднього каліченого очищення рядків
        raw_items = database.get_user_wardrobe(user_id)
    except Exception as e:
        await message.answer(f"❌ Помилка доступу до бази даних: {str(e)}")
        return

    if not raw_items:
        await message.answer("Твій гардероб порожній! Завантаж фото одягу за допомогою звичайного надсилання фото, щоб я міг знайти прогалини.")
        return

    await message.answer("🔄 Проводжу ревізію вашої шафи, аналізую клімат та шукаю прогалини в асортименті...")

    # Безпечно визначаємо місто та погоду
    try:
        user_city = database.get_user_city(user_id) or "Lviv"
        weather_data = weather.get_weather(city=user_city)
    except Exception:
        weather_data = {"temp": 15, "description": "мінлива хмарність"}

    # Викликаємо оновлений, стійкий до помилок ШІ-модуль
    try:
        shopping_list = ai_stylist.generate_shopping_recommendation(weather_data, raw_items)
        await message.answer(shopping_list, parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"❌ Критична помилка стиліста: {str(e)}")


@dp.message_handler(content_types=['photo'], state="*")
async def handle_clothing_photo(message):
    photo = message.photo[-1]
    try:
        file_info = await bot.get_file(photo.file_id)
        file_success = await bot.download_file(file_info.file_path)
        description = ai_stylist.analyze_clothing_image(file_success.read())
        database.add_clothing(user_id=message.from_user.id, file_id=photo.file_id, description=description)
        await message.answer(f"✅ Додано!\nОпис ШІ: {description}")
    except Exception as e:
        await message.answer(f"❌ Помилка: {str(e)}")

# ХЕНДЛЕР ДЛЯ ОБРОБКИ ДАНИХ З WEB APP
@dp.message_handler(content_types=types.ContentType.WEB_APP_DATA, state="*")
async def process_webapp_style_change(message: types.Message):
    # Отримуємо дані, які надіслав наш JS-скрипт із файлу index.html
    webapp_data = message.web_app_data.data
    user_id = message.from_user.id
    
    # Перевіряємо, чи це команда на зміну стилю інтерфейсу
    if webapp_data.startswith("set_style_"):
        # Витягуємо чисту назву стилю (наприклад: 'neon', 'pastel' або 'default')
        chosen_style = webapp_data.replace("set_style_", "")
        
        # Зберігаємо обраний стиль користувача в нашу базу даних PostgreSQL
        database.save_user_style(user_id, chosen_style)
        
        # Створюємо красиву відповідь залежно від обраної теми
        style_emojis = {"default": "✨ Стандартний", "neon": "🌌 Неоновий", "pastel": "🌸 Пастельний"}
        friendly_style_name = style_emojis.get(chosen_style, chosen_style)
        
        await message.answer(
            f"🎨 <b>Стиль інтерфейсу успішно змінено!</b>\n"
            f"Тепер ваш персональний стиль: <b>{friendly_style_name}</b>.\n\n"
            f"Налаштування збережено у хмарі. При наступному відкритті візуальної шафи "
            f"вона завантажиться у вашому унікальному дизайні!",
            parse_mode="HTML"
        )
@dp.message_handler(commands=['start'], state="*")
async def send_welcome(message: types.Message):
    from aiogram.types import MenuButtonWebApp, WebAppInfo
    
    # Замініть це посилання на адресу вашого сервісу з Render!
    render_url = "https://onrender.com"
    
    await bot.set_chat_menu_button(
        chat_id=message.chat.id,
        menu_button=MenuButtonWebApp(
            text="👗 Шафа",
            web_app=WebAppInfo(url=render_url)
        )
    )
    await message.answer("Привіт! Меню оновлено.", reply_markup=main_keyboard)


async def run_bot():
    database.init_db()
    print("🤖 БОТ ЗАПУСКАЄТЬСЯ...")
    try:
        await dp.start_polling()
    finally:
        await dp.storage.close()
        await dp.storage.wait_closed()
        await bot.close()


if __name__ == "__main__":
    try:
        asyncio.run(run_bot())
    except (KeyboardInterrupt, SystemExit):
        print("\n🛑 Бот успішно зупинений.")