import os
import random
import openai
import config

def get_openai_client():
    api_key = getattr(config, "OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
    if not api_key:
        return None
    try:
        return openai.OpenAI(api_key=api_key)
    except Exception:
        return None

def analyze_clothing_image(image_bytes: bytes) -> str:
    templates = [
        "Ніжне базове оверсайз худі пастельного відтінку.",
        "Естетичні світлі джинси прямого крою у стилі Pinterest.",
        "Мінімалістичний срібний ланцюжок з витонченою підвіскою.",
        "Стильні білі шкіряні кросівки на кожен день.",
        "Затишний в'язаний кардиган для прохолодних вечорів."
    ]
    return random.choice(templates)

def generate_outfit_recommendation(weather_info: dict, wardrobe_items: list, event: str) -> str:

    temp = weather_info.get('temp', 12)
    condition = weather_info.get('description', 'хмарно з проясненнями')
    wind = weather_info.get('wind', {}).get('speed', 3.5)
    humidity = weather_info.get('humidity', 70)
    
    weather_header = (
        f"🌸 **Погодний щоденник:**\n"
        f"🌡️ За вікном зараз: `{temp}°C` ({condition})\n"
        f"💨 Вітерець: `{wind} м/с` | 💧 Вологість: `{humidity}%` \n\n"
    )

    items_text = "\n".join([f"- ID {item[2]} (Поличка: {item[3]}): {item[1]}" for item in wardrobe_items])

    prompt = (
        f"Ти — найкраща подружка-стиліст, шалено закохана в моду та естетику Coquette/Pinterest. "
        f"Склади для дівчини суперстильний образ з її реальних речей під погоду {temp}°C, {condition}. Подія: {event}.\n\n"
        f"ОСЬ РЕЧІ З ЇЇ ШАФИ:\n{items_text}\n\n"
        f"ОБОВ'ЯЗКОВО сформуй відповідь дуже красиво, мімімішно, з купою дівочих емодзі за такою структурою:\n"
        f"🧥 ВЕРХНІЙ ШАР (Верхній одяг, якщо холодно):\n"
        f"👚 БАЗОВИЙ ВЕРХ (Худі, светрик, кардиган чи топ):\n"
        f"👖 НИЗ (Джинси, спідничка, шорти чи брюки):\n"
        f"👟 ВЗУТТЯ (Кросівки, туфельки тощо):\n"
        f"👜 АКСЕСУАРИ (Прикраси, сумочка):\n\n"
        f"💕 Чому цей образ ідеальний: (Напиши комплімент дівчині та поясни, чому ці шари будуть комфортні для {temp}°C та події '{event}')")

    """
    ВІДНОВЛЕНО: Генерація щоденного пошарового образу.
    """
    temp = weather_info.get('temp', weather_info.get('temperature', 12))
    feels_like = weather_info.get('feels_like', weather_info.get('feels_like_temperature', 10))
    condition = weather_info.get('description', weather_info.get('condition', 'хмарно з проясненнями'))
    humidity = weather_info.get('humidity', 78)
    wind = weather_info.get('wind', {}).get('speed', 4.5) if isinstance(weather_info.get('wind'), dict) else weather_info.get('wind', 4.5)
    uv_index = weather_info.get('uv', weather_info.get('uv_index', 2))

       # Знайдіть цей блок у файлі ai_stylist.py:
    weather_header = (
        f"🌡️ Температура: {temp}°C (відчувається як {feels_like}°C)\n"
        f"☁️ Стан: {condition}\n"
        f"💨 Вітер: {wind} м/с\n"
        f"💧 Вологість: {humidity}%\n"
        f"☀️ УФ-індекс (UV): {uv_index}\n\n"
    )


    clean_items = []
    for item in wardrobe_items:
        desc = item[1] if isinstance(item, (tuple, list)) and len(item) > 1 else str(item)
        clean_items.append(desc)
    items_text = "\n- ".join(clean_items)

    prompt = (
        f"Ти — професійний лаконічний ШІ-стиліст додатка 'Шо одіти?'. На основі погоди ({temp}°C, {condition}, відчувається як {feels_like}°C) та події ({event}) "
        f"склади структурований пошаровий образ користувача з його гардеробу.\n\n"
        f"СПИСОК РЕЧЕЙ КОРИСТУВАЧА:\n- {items_text}\n\n"
        f"Пиши відповідь українською мовою строго за цим шаблоном (підставляй реальні назви речей користувача):\n"
        f"👕 Базовий верх: ...\n"
        f"🧥 Середній шар: ...\n"
        f"🧥 Верхній одяг: ...\n"
        f"👖 Низ: ...\n"
        f"👟 Взуття: ...\n"
        f"💍 Прикраси/Аксесуари: ...\n"
        f"✨ *Обґрунтування образу:* [1-2 речення чому це комфортно під погоду]\n\n"
        f"ОДЯГНИ: [напиши через кому id або точні назви обраних речей]"

    )

    client = get_openai_client()
    if client:
        try:

            response = client.chat.completions.create(

            response = client_openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=450
            )
            )
            if response and response.choices and len(response.choices) > 0:
                return f"{weather_header}{response.choices[0].message.content.strip()}"
        except Exception as e:
            print(f"Помилка OpenAI при виборі образу: {e}")

    # Бекап
    backup_content = (
        f"👕 Базовий верх: Світла футболка\n"
        f"🧥 Середній шар: Білий худі з капюшоном\n"
        f"🧥 Верхній одяг: Куртка за потреби\n"
        f"👖 Низ: Вільні джинси або штани\n"
        f"👟 Взуття: Білі спортивні кросівки\n\n"
        f"✨ *Обґрунтування образу:* Поєднання базових шарів забезпечує чудовий рівень тепла та комфорту для поточної погоди {temp}°C."
    )
    return f"{weather_header}{backup_content}"


def generate_trip_itinerary(forecast_data: dict, wardrobe_items: list, event: str, days_count: int) -> str:
    """Лаконічний генератор капсули для подорожей із розбивкою по днях та шарах."""
    city = event.strip() if event else "обраного міста"
    days = days_count if days_count else 2

    temp = forecast_data.get('temp', forecast_data.get('temperature', 12))
    condition = forecast_data.get('description', forecast_data.get('condition', 'хмарно з проясненнями'))

    intro_header = (
        f"Вітаю! Прогноз погоди для м. {city}: {temp}°C, {condition}.\n"
        f"Ось твій збалансований гардероб на {days} дні(в), зібраний з твоїх речей:\n\n"
        f"🎒 КАПСУЛЬНА ВАЛІЗА:\n\n"
    )

    clean_items = []
    for item in wardrobe_items:
        if isinstance(item, (tuple, list)):
            text_fields = [str(x).strip() for x in item if isinstance(x, str) and len(str(x).strip()) > 5]
            if text_fields:
                clean_items.append(text_fields[0])
            else:
                clean_items.append(str(item[-1]).strip())
        else:
            clean_items.append(str(item).strip())

    clean_items = [x for x in clean_items if not x.isdigit() and len(x) > 3]
    if not clean_items:
        clean_items = ["Біле худі з написом 'GODDESS'", "Світло-сірі джинси", "Чорна куртка-пуффер", "Білі кросівки"]

    items_text = "\n- ".join(clean_items)

    prompt = (
        f"Ти — професійний ШІ-стиліст додатка 'Шо одіти?'. Твоє завдання — зібрати капсулу та образи для поїздки в місто {city} на {days} днів.\n"
        f"Температура: {temp}°C, стан погоди: {condition}.\n\n"
        f"СПИСОК НАЯВНИХ РЕЧЕЙ КОРИСТУВАЧА:\n- {items_text}\n\n"
        f"Напиши відповідь строго українською мовою за цим шаблоном. Склади повноцінні багатошарові образи (базовий верх + проміжний верх/худі + куртка якщо холодно):\n\n"
        f"👕 **Рекомендовані речі у валізу:**\n"
        f"- [Колір + назва речі з бази] — [коротка роль у поїздці]\n\n"
        f"📅 **Варіанти поєднань по днях:**\n"
        f"**День 1:** [Повний набір одягу на цей день: що з чим поєднати з верхнього одягу, верху та низу]\n"
        f"**День 2:** [Повний комплект одягу на зміну або інше поєднання шарів]\n\n"
        f"💡 **Порада стиліста щодо терморегуляції:** [1-2 речення, як правильно чергувати шари одягу при {temp}°C]"
    )

    client_openai = get_openai_client()
    if client_openai:
        try:
            response = client_openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
                max_completion_tokens=650
            )
            return f"{weather_header}{response.choices[0].message.content.strip()}"
        except Exception as e:
            return f"{weather_header}❌ Ой, красуне, ШІ-стиліст припудрив носик, спробуй ще раз! ({e})"
    return f"{weather_header}👕 Футболка + 👖 Джинси. Додай фото речей, щоб увімкнути магію!"

def generate_trip_itinerary(weather_desc: str, wardrobe_items: list, destination: str, days: int) -> str:
    items_text = "\n".join([f"- ID {item[2]} ({item[3]}): {item[1]}" for item in wardrobe_items])
    
    prompt = (
        f"Ти — найкраща подружка-стиліст, яка допомагає зібрати ідеальну естетичну валізу в подорож.\n"
        f"Дівчина їде в місто *{destination}* на *{days} днів*.\n"
        f"Прогноз погоди там: {weather_desc}.\n\n"
        f"УСІ РЕЧІ В ШАФІ:\n{items_text}\n\n"
        f"ТВОЄ ЗАВДАННЯ:\n"
        f"1. Склади максимально компактну, капсульну валізу (пакуй мінімум речей, які легко комбінуються між собою, щоб валіза закрилася легенько!).\n"
        f"2. Розпиши готові комбінації речей окремо для кожного дня (День 1, День 2... аж до {days} дня). "
        f"Кожен день має виглядати як естетичний Pinterest-аутфіт (по шарах: верх, низ, взуття, аксесуар). Пиши у ніжному дівчачому стилі."
    )
    
    client = get_openai_client()
    if client:
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_completion_tokens=1000
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"❌ Ой, не вдалося зібрати валізу: {e}"
    return "Помилка ініціалізації ШІ-стиліста подорожей."

def generate_shopping_recommendation(wardrobe_items: list) -> str:
    items_text = "\n".join([f"- {item[1]} (Категорія: {item[3]})" for item in wardrobe_items])
    
    prompt = (
        f"Ти — професійна дівчина-стиліст. Проаналізуй поточну шафу користувачки:\n{items_text}\n\n"
        f"Визнач, яка в неї переважає кольорова палітра та стиль речей. "
        f"Знайди прогалини у базовому гардеробі. Напиши список із 3-4 речей, яких їй катастрофічно не вистачає для ідеальних луків.\n"
        f"Обов'язково поясни, ЧОМУ саме ця річ потрібна, як вона доповнить її кольорову палітру та з якими речами з наявних її можна поєднувати. "
        f"Стиль написання — милий, фенсі, дружній з емодзі."
    )
    
    client = get_openai_client()
    if client:
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
                max_completion_tokens=650
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"❌ Не вдалося проаналізувати гардероб: {e}"
    return "Додайте більше фото вашого одягу!"
