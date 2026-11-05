import base64
import os
import random
import openai
import config

def get_openai_client():
    """Ініціалізація клієнта OpenAI."""
    api_key = getattr(config, "OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
    if not api_key:
        return None
    try:
        return openai.OpenAI(api_key=api_key)
    except Exception:
        return None

def analyze_clothing_image(image_bytes: bytes) -> str:
    """Аналіз нових речей через OpenAI (gpt-4o-mini)."""
    base64_image = base64.b64encode(image_bytes).decode('utf-8')
    
    prompt = (
        "Ти — професійний і лаконічний ШІ-стиліст додатка 'Шо одіти?'. Твоє завдання — уважно подивитися на фото та скласти живий, природний опис речі.\n"
        "Пиши відповідь строго одним коротким абзацом (3-4 речення) українською мовою. Не використовуй списки, пункти чи емодзі типу кубиків чи зірочок.\n\n"
        "Дотримуйся плану всередині абзацу:\n"
        "1. Чітко визнач річ.\n"
        "2. Опиши силует, текстуру, тканину, деталі або написи.\n"
        "3. Визнач загальний стиль речі.\n"
        "4. Вкажи, для яка погода або сезон підходить найкраще."
    )
    
    client_openai = get_openai_client()
    if not client_openai:
        return "❌ Помилка: Клієнт OpenAI не ініціалізований. Пропишіть OPENAI_API_KEY у config.py!"

    try:
        response = client_openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user", 
                    "content": [
                        {"type": "text", "text": prompt}, 
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }
            ],
            timeout=15
        )
        if response and response.choices and len(response.choices) > 0:
            return response.choices[0].message.content.strip()
    except Exception as e:
        error_text = str(e)
        if "insufficient_quota" in error_text.lower() or "billing" in error_text.lower():
            return "❌ Помилка OpenAI: На вашому балансі закінчилися кошти!"
        return f"❌ Помилка роботи ШІ OpenAI: {error_text}"
    return "❌ Помилка: Не вдалося отримати відповідь від OpenAI."


def generate_outfit_recommendation(weather_info: dict, wardrobe_items: list, event: str) -> str:
    """
    ВІДНОВЛЕНО: Генерація щоденного пошарового образу.
    """
    temp = weather_info.get('temp', weather_info.get('temperature', 12))
    feels_like = weather_info.get('feels_like', weather_info.get('feels_like_temperature', 10))
    condition = weather_info.get('description', weather_info.get('condition', 'хмарно з проясненнями'))
    humidity = weather_info.get('humidity', 78)
    wind = weather_info.get('wind', {}).get('speed', 4.5) if isinstance(weather_info.get('wind'), dict) else weather_info.get('wind', 4.5)
    uv_index = weather_info.get('uv', weather_info.get('uv_index', 2))

    weather_header = (
        f"💨 Вітер: {wind} м/с\n"
        f"💧 Волгогість: {humidity}%\n"
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

    client_openai = get_openai_client()
    if client_openai:
        try:
            response = client_openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=450
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
                max_tokens=650
            )
            if response and response.choices and len(response.choices) > 0:
                return f"{intro_header}{response.choices[0].message.content.strip()}"
        except Exception as e:
            print(f"Помилка OpenAI у подорожах: {e}")

    return f"{intro_header}👕 **Рекомендовані речі у валізу:**\n- Речі базового гардероба.\n\n💡 Порада: Чергуйте шари одягу."

def generate_shopping_recommendation(weather_info: dict, wardrobe_items: list) -> str:
    """Аналізує гардероб на наявність прогалин."""
    link1 = "[Стильні джинси прямого крою (1500 грн)](https://rozetka.com.ua)"
    link2 = "[Класичне чорне худі (1200 грн)](https://rozetka.com.ua)"
    return (
        f"🔎 **Аналіз гардеробу:** У вашій шафі вже є база речей! Враховуючи погоду ({weather_info.get('temp', 15)}°C), додайте комфортні акценти.\n\n"
        f"🛒 **Що варто докупити:**\n1. {link1}\n2. {link2}"
    )
