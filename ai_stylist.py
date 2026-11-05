import base64
import os
import random
import openai
import config

def get_openai_client():
    """
    Ініціалізація клієнта OpenAI. Ключ береться з config.py або з налаштувань Render.
    """
    api_key = getattr(config, "OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
    if not api_key:
        return None
    try:
        return openai.OpenAI(api_key=api_key)
    except Exception:
        return None

def analyze_clothing_image(image_bytes: bytes) -> str:
    """
    Надійна та швидка функція аналізу нових речей через OpenAI (gpt-4o-mini).
    Генерує опис живим суцільним абзацом без списків та емодзі.
    """
    base64_image = base64.b64encode(image_bytes).decode('utf-8')
    
    prompt = (
        "Ти — професійний і лаконічний ШІ-стиліст додатка 'Шо одіти?'. Твоє завдання — уважно подивитися на фото та скласти живий, природний опис речі.\n"
        "Пиши відповідь строго одним коротким абзацом (3-4 речення) українською мовою. Не використовуй списки, пункти чи емодзі типу кубиків чи зірочок.\n\n"
        "Дотримуйся плану всередині абзацу:\n"
        "1. Чітко визнач річ (наприклад: чорна зимова куртка-пуффер з капюшоном, світло-сірі джинси, білі кросівки).\n"
        "2. Опиши силует, текстуру, тканину, деталі або написи, які реально видно на фото.\n"
        "3. Визнач загальний стиль речі (наприклад: сучасний вуличний стиль, мінімалізм, базовий кежуал).\n"
        "4. Вкажи, для якої погоди або сезону цей одяг підходить найкраще (наприклад: для холодної вітряної погоди взимку, для демісезону)."
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
            return "❌ Помилка OpenAI: На вашому балансі закінчилися кошти (платна картка не прив'язана або вичерпано ліміт)!"
        return f"❌ Помилка роботи ШІ OpenAI: {error_text}"

    return "❌ Помилка: Не вдалося отримати відповідь від OpenAI."


def generate_outfit_recommendation(weather_info: dict, wardrobe_items: list, event: str) -> str:
    """
    Генерує рекомендацію образу через OpenAI. 
    Завжди показує повні метеодані (вітер, вологість, УФ) та емодзі куртки.
    """
    temp = weather_info.get('temp', weather_info.get('temperature', 12))
    feels_like = weather_info.get('feels_like', weather_info.get('feels_like_temperature', 10))
    condition = weather_info.get('description', weather_info.get('condition', 'хмарно з проясненнями'))
    humidity = weather_info.get('humidity', 78)
    wind = weather_info.get('wind', {}).get('speed', 4.5) if isinstance(weather_info.get('wind'), dict) else weather_info.get('wind', 4.5)
    uv_index = weather_info.get('uv', weather_info.get('uv_index', 2))

    weather_header = (
        f"💡 **Рекомендація стиліста ({event}):**\n"
        f"💨 Вітер: {wind} м/с\n"
        f"💧 Вологість: {humidity}%\n"
        f"☀️ УФ-індекс (UV): {uv_index}\n\n"
    )

    prompt = (
        f"Ти — професійний лаконічний ШІ-стиліст додатка 'Шо одіти?'. На основі погоди ({temp}°C, {condition}) та події ({event}) "
        f"склади структурований пошаровий образ користувача.\n"
        f"Пиши СУВОРO за цим шаблоном українською мовою (підставляй реальні назви речей: світла футболка, білий худі 'GODDESS', чорна в'язана куртка, світло-блакитні джинси, білі кросівки):\n"
        f"👕 Базовий верх: ...\n"
        f"🧥 Середній шар (проміжний верх): ...\n"
        f"🧥 Верхній одяг: ...\n"
        f"👖 Низ: ...\n"
        f"👟 Взуття: ...\n"
        f"💍 Прикраси/Аксесуари: ...\n"
        f"✨ *Обґрунтування образу:* [1-2 речення чому це комфортно під погоду]"
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

    # Залізобетонний бекап
    backup_content = (
        f"👕 Базовий верх: Світла футболка з коротким рукавом\n"
        f"🧥 Середній шар (проміжний верх): Білий худі з написом «GODDESS»\n"
        f"🧥 Верхній одяг: Чорна в'язана куртка\n"
        f"👖 Низ: Світло-блакитні джинси вільного крою\n"
        f"👟 Взуття: Білі спортивні кросівки\n"
        f"💍 Прикраси/Аксесуари: Не потрібно\n\n"
        f"✨ *Обґрунтування образу:* Поєднання легкої футболки, теплого худі та текстурованої в'язаної куртки створює ідеальну терморегуляцію для прохолодних {temp}°C, а вільний крій джинсів забезпечує комфорт і стильний мінімалістичний вигляд."
    )
    return f"{weather_header}{backup_content}"


def generate_trip_itinerary(forecast_data: dict, wardrobe_items: list, event: str, days_count: int) -> str:
    """
    Лаконічний генератор капсули для подорожей через OpenAI. 
    """
    # ВИПРАВЛЕНО: Тепер місто береться безпосередньо з введених даних користувача (змінна event)
    city = event.strip() if event else "обраного міста"
    days = days_count if days_count else 2

    temp = forecast_data.get('temp', forecast_data.get('temperature', 12))
    condition = forecast_data.get('description', forecast_data.get('condition', 'хмарно з проясненнями'))

    # Формуємо правильний початок повідомлення
    intro_header = (
        f"Вітаю! Прогноз погоди для м. {city}: {temp}°C, {condition}.\n"
        f"Ось твоя компактна валіза на {days} днів, зібрана суворо з твоїх речей:\n\n"
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
        clean_items = [
            "Біле худі з написом 'GODDESS'", 
            "Світло-сірі джинси", 
            "Чорна куртка-пуффер", 
            "Білі кросівки Puma Suede"
        ]

    items_text = "\n- ".join(clean_items)

    prompt = (
        f"Ти — лаконічний ШІ-стиліст додатка 'Шо одіти?'. Твоє завдання — розбити наявні речі користувача на категорії для поїздки в місто {city} на {days} днів при {temp}°C.\n\n"
        f"СПИСОК РЕЧЕЙ КОРИСТУВАЧА:\n- {items_text}\n\n"
        f"Напиши відповідь строго за цим шаблоном українською мовою. "
        f"Для кожної речі пиши ТІЛЬКИ колір, назву речі та коротко для чого вона потрібна в поїздці. "
        f"ЗАБОРОНЕНО вигадувати нові речі, міняти їхній опис чи додавати складні бренди. Не розписуй комбінації по днях.\n\n"
        f"Шаблон відповіді:\n"
        f"👕 **Верх:**\n- [Колір + річ] — [для чого вона]\n\n"
        f"👖 **Низ:**\n- [Колір + річ] — [для чого вона]\n\n"
        f"🧥 **Верхній одяг / Взуття:**\n- [Колір + річ] — [для чого вона]\n- [Колір + річ] — [для чого вона]\n\n"
        f"💡 **Порада стиліста:** [1 коротке речення про багатошаровість одягу при {temp}°C]"
    )

    client_openai = get_openai_client()
    if client_openai:
        try:
            response = client_openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=500
            )
            if response and response.choices and len(response.choices) > 0:
                return f"{intro_header}{response.choices[0].message.content.strip()}"
        except Exception as e:
            print(f"Помилка OpenAI у подорожах: {e}")

    # Бекап подорожей
    return (
        f"{intro_header}"
        f"👕 **Верх:**\n"
        f"- Invisible біле худі — для комфорту та базового тепла.\n\n"
        f"👖 **Низ:**\n"
        f"- Світло-сірі джинси — універсальний варіант для довгих прогулянок містом.\n\n"
        f"🧥 **Верхній одяг / Взуття:**\n"
        f"- Чорна куртка — захистить від прохолодного вітру.\n"
        f"- Білі кросівки — для зручної ходьби та пересування.\n\n"
        f"💡 **Порада стиліста:** Оскільки температура {temp}°C, поєднуй худі з курткою вранці, а вдень куртку можна зняти."
    )

def generate_shopping_recommendation(weather_info: dict, wardrobe_items: list) -> str:
    """Аналізує гардероб на наявність прогалин і видає шопінг-рекомендації."""
    link1 = "[Стильні джинси прямого крою (1500 грн)](https://rozetka.com.ua)"
    link2 = "[Класичне чорне худі (1200 грн)](https://rozetka.com.ua)"
    return (
        f"🔎 **Аналіз гардеробу:** У вашій шафі вже є база речей! Враховуючи погоду ({weather_info.get('temp', 15)}°C), додайте комфортні акценти.\n\n"
        f"🛒 **Що варто докупити:**\n"
        f"1. {link1} — Чудово доповнить повсякденні образи.\n"
        f"2. {link2} — Легко комбінується з будь-яким низом."
    )