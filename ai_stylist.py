import base64
import re
from groq import Groq
import config

client = Groq(api_key=config.GROQ_API_KEY)

def analyze_clothing_image(image_bytes: bytes) -> str:
    """Розпізнає фото одягу через модель Qwen"""
    base64_image = base64.b64encode(image_bytes).decode('utf-8')
    prompt = "Подивись на це фото одягу. Визнач, що це за річ, колір, стиль та погоду. 2-3 речення українською."
    
    try:
        response = client.chat.completions.create(
            model="qwen/qwen3.8-27b", 
            messages=[{"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}]}],
            timeout=20
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Помилка аналізу зображення: {str(e)}"

def generate_outfit_recommendation(weather_info: dict, wardrobe_items: list, event: str) -> str:
    """Генерує суворо один текстовий багатошаровий образ на сьогодні з урахуванням дощу та снігу."""
    if not wardrobe_items:
        return "Гардероб порожній."
    
    formatted_items = []
    for item in wardrobe_items:
        if isinstance(item, (tuple, list)):
            desc = item[1] if len(item) > 1 else str(item)
        else:
            desc = str(item)
        formatted_items.append(desc)
        
    items_text = "\n- ".join(formatted_items)
    
    # ДИНАМІЧНИЙ АНАЛІЗ НЕГОДИ
    rain_volume = weather_info.get("rain", 0)
    snow_volume = weather_info.get("snow", 0)
    weather_alert_instruction = ""
    
    # Формуємо застереження для ШІ-стиліста, якщо є опади
    if rain_volume > 0:
        weather_alert_instruction = (
            "\n⚠️ УВАГА СТИЛІСТУ: Зараз іде ДОЩ! "
            "Обов'язково додай у поле 'Прикраси/Аксесуари' ПАРАСОЛЮ. "
            "Також вибери максимально НЕПРОМОКАЛЬНЕ взуття (жодних тканинних чи відкритих варіантів, якщо є альтернатива).\n"
        )
    elif snow_volume > 0:
        weather_alert_instruction = (
            "\n⚠️ УВАГА СТИЛІСТУ: Зараз іде СНІГ або хурделиця! "
            "Обов'язково вибери найтепліше зимове взуття з наявного та найнадійніший верхній одяг. "
            "Додай теплі зимові аксесуари (рукавички, шапка, шарф) у відповідне поле.\n"
        )
    
    prompt = (
        f"Ти професійний стиліст.\n"
        f"Склади для користувача СУВОРO ОДИН готовий образ під подію '{event}' та погоду {weather_info['temp']}°C, {weather_info['description']}.\n"
        f"{weather_alert_instruction}"  # Вставка тригера негоди безпосередньо в мозок ШІ
        f"\nПРАВИЛО БАГАТОШАРОВОСТІ:\n"
        f"- Базовий шар (Верх): футболка або майка з гардероба.\n"
        f"- Середній шар (Проміжний): олімпійка, худі, светр чи кофта з гардероба (якщо прохолодно).\n"
        f"- Upper шар (Верхній одяг): куртка або пальто з гардероба (відповідно до погоди).\n\n"
        f"ЖОДНИХ АЛЬТЕРНАТИВ ТА СПOЛУЧНИКІВ 'АБО'. Тільки одна конкретна річ у кожному пункті.\n\n"
        f"СПИСОК РЕЧЕЙ КОРИСТУВАЧА:\n- {items_text}\n\n"
        f"Заповни цей шаблон назвами з наявного списку:\n"
        f"👕 Базовий верх: [назва однієї речі з гардероба]\n"
        f"🧥 Середній шар (проміжний верх): [назва речі з гардероба або Не потрібно]\n"
        f"🧥 Верхній одяг: [назва куртки/пальта з гардероба або Не потрібно]\n"
        f"👖 Низ: [назва лише однієї речі з гардероба]\n"
        f"👟 Взуття: [актуальне взуття під цей образ з урахуванням опадів та калюж]\n"
        f"📿 Прикраси/Аксесуари: [підбери стильні прикраси та обов'язкові предмети захисту від негоди, якщо вони потрібні за інструкцією вище]\n"
        f"✨ Обґрунтування образу: [коротке речення, чому ці шари добре поєднуються та захищають у таку погоду]"
    )
    
    # Використовуємо стабільні моделі вашого Groq акаунту
    for model_name in ["llama3-8b-8192", "qwen/qwen3.8-27b"]:
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,  # Максимальна точність виконання шаблону й інструкцій негоди
                max_tokens=350
            )
            if response and response.choices:
                content = response.choices[0].message.content
                if content:
                    return content.strip()
        except Exception:
            continue
            
    return "Не вдалося отримати відповідь від ШІ стиліста. Спробуйте пізніше."




def generate_trip_itinerary(forecast_data: dict, wardrobe_items: list, event: str, days_count: int) -> str:
    """Генерує максимально компактний капсульний набір речей у валізу."""
    if not wardrobe_items:
        return "Гардероб порожній."
    
    formatted_items = []
    for item in wardrobe_items:
        if isinstance(item, (tuple, list)):
            desc = item[1] if len(item) > 1 else str(item)
        else:
            desc = str(item)
        formatted_items.append(desc)
        
    items_text = "\n- ".join(formatted_items)
    days_count = min(int(days_count), len(forecast_data["days"]))
    
    total_temp = 0
    weather_conditions = []
    for i in range(days_count):
        day = forecast_data["days"][i]
        total_temp += day["temp"]
        weather_conditions.append(day["description"])
        
    avg_temp = round(total_temp / days_count)
    unique_conditions = ", ".join(set(weather_conditions))

    prompt = (
        f"Ти професійний стиліст, експерт із капсульного гардероба.\n"
        f"Користувач збирає мінімалістичну валізу у відпустку на {days_count} днів у місто {forecast_data['city']}.\n"
        f"Прогноз погоди: в середньому {avg_temp}°C, очікується: {unique_conditions}.\n\n"
        f"ДОСТУПНИЙ ГАРДЕРОБ КОРИСТУВАЧА:\n- {items_text}\n\n"
        f"ЗАВДАННЯ:\n"
        f"Склади СУВОРO МІНІМАЛЬНИЙ чек-лист речей із наявного гардероба. Дотримуйся правил капсули:\n"
        f"- На поїздку до 3 днів: РІВНО 1 універсальний низ і не більше 2 варіантів верху.\n"
        f"- На поїздку 4-5 днів: РІВНО 1-2 низи і 2-3 варіанти верху.\n"
        f"- Усі речі мають ідеально поєднуватися між собою, щоб не брати зайвого одягу про запас!\n\n"
        f"Напиши відповідь суворо за цим шаблоном (без зайвих вступів):\n"
        f"🎒 **КАПСУЛЬНА ВАЛІЗА ({days_count} дн. у м. {forecast_data['city']}):**\n"
        f"👕 **Верх (мінімум речей)**:\n- [конкретні 1-3 назви речей з гардероба, кожна з нового рядка]\n"
        f"👖 **Низ (1-2 базові речі)**:\n- [конкретні 1-2 назви речей з гардероба, кожна з нового рядка]\n"
        f"🧥 **Верхній одяг / Взуття**:\n- [лише 1 варіант взуття та 1 куртка/пальто під погоду {avg_temp}°C]\n"
        f"💡 **Комбінації на кожен день**:\n[Стисло в 2-3 рядки розпиши, як міксувати ці речі, щоб не повторювати один і той самий образ]"
    )
    
        # ОСЬ ЦЕЙ БЛОК НАПРИКІНЦІ ФУНКЦІЇ ПОТРІБНО ЗАМІНИТИ:
    for model_name in ["llama3-8b-8192", "qwen/qwen3.8-27b"]:
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=800  # ЗБІЛЬШЕНО З 400 ДО 800: Тепер відповідь ШІ ніколи не обірветься!
            )
            if response and response.choices:
                content = response.choices[0].message.content
                if content:
                    return content.strip()
        except Exception:
            continue
            
    return "Не вдалося зібрати валізу. Спробуйте пізніше."


import database  # Переконайтеся, що імпортували базу даних

def generate_shopping_recommendation(weather_info: dict, wardrobe_items: list) -> str:
    """Аналізує гардероб на наявність прогалин і видає шопінг-рекомендації з ДИНАМІЧНОЇ бази."""
    if not wardrobe_items:
        return "Твій гардероб повністю порожній. Щоб знайти прогалини, завантаж фото одягу!"
    
    formatted_items = []
    for item in wardrobe_items:
        if isinstance(item, (tuple, list)):
            desc = item[1] if len(item) > 1 else str(item)
        else:
            desc = str(item)
        formatted_items.append(desc)
        
    items_text = "\n- ".join(formatted_items)
    
    # ДИНАМІКА: Отримуємо товари безпосередньо з нашої бази даних
    db_products = database.get_all_shopping_items()
    
    # Формуємо текстовий рядок товарів для ШІ
    products_links_feed = ""
    for prod in db_products:
        name, price, url, category, gender = prod
        # Формуємо маркдаун посилання з анкором для правильного кліку в Telegram
        products_links_feed += f"- [{name} ({price} грн)]({url} '{name.lower()}') [Категорія: {category}, Для кого: {gender}]\n"
    
    prompt = (
        f"Ти професійний стиліст і ревізор гардеробу.\n"
        f"Поточна погода у місті: {weather_info['temp']}°C, {weather_info['description']}.\n\n"
        f"НАЯВНИЙ ГАРДЕРОБ КОРИСТУВАЧА:\n- {items_text}\n\n"
        f"ЗАВДАННЯ:\n"
        f"1. Проаналізуй цей список речей користувача та поточну погоду. Знайди критичну прогалину у шафі (чого критично не вистачає під таку погоду чи для базових шарів).\n"
        f"2. Запропонуй користувачу докупити РІВНО 2 найрізноманітніші доречні речі з наданої БАЗИ ТОВАРІВ.\n\n"
        f"ДОСТУПНА БАЗА ТОВАРІВ З ROZETKA (Обери дві найкращі речі звідси):\n"
        f"{products_links_feed}\n"
        f"КРИТИЧНЕ ПРАВИЛО: Використовуй тільки посилання (URL), які вказані біля обраного товару вище. Не вигадуй інші посилання чи URL!\n\n"
        f"Шаблон відповіді (заповни суворо за зразком, без вступів):\n"
        f"🔎 **Аналіз гардеробу:** [Короткий висновок, чого саме не вистачає]\n\n"
        f"🛒 **Що варто докупити (Шопінг-лист з ROZETKA):**\n"
        f"1. [Назва обраної речі 1 як посилання](Встав відповідний URL) — [Пояснення, чому вона закриє прогалину в гардеробі]\n"
        f"2. [Назва обраної речі 2 як посилання](Встав відповідний URL) — [Пояснення, чому вона пасуватиме до поточної погоди]\n\n"
        f"💡 **Порада стиліста:** [Фінальний інсайт]"
    )
    
    # Використовуємо вашу модель Groq (наприклад, стабільну llama3-8b-8192)
    for model_name in ["llama3-8b-8192", "qwen/qwen3.8-27b"]:
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3, # Трішки творчості для аналізу, але точність для лінків
                max_tokens=450
            )
            if response and response.choices:
                content = response.choices[0].message.content
                if content:
                    return content.strip()
        except Exception:
            continue
            
    return "Не вдалося провести динамічний аналіз гардеробу. Спробуйте пізніше."

