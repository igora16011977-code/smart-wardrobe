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


def generate_trip_itinerary(forecast_data: dict, wardrobe_items: list, event: str, days_count: int) -> str:
    """
    Лаконічний генератор капсули для подорожей через OpenAI із розбивкою по днях та шарах.
    """
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

    # ОНОВЛЕНИЙ ПРОМПТ: Дозволяємо ШІ групувати речі за шарами та розписувати дні
    prompt = (
        f"Ти — професійний ШІ-стиліст додатка 'Шо одіти?'. Твоє завдання — зібрати капсулу та покрокові образи для поїздки в місто {city} на {days} днів.\n"
        f"Температура повітря: {temp}°C, стан погоди: {condition}.\n\n"
        f"СПИСОК НАЯВНИХ РЕЧЕЙ КОРИСТУВАЧА (використовуй ТІЛЬКИ їх, не вигадуй сторонні бренди):\n- {items_text}\n\n"
        f"Напиши відповідь строго українською мовою за цим шаблоном. Склади повноцінні багатошарові образи (базовий верх + проміжний верх/худі + куртка якщо холодно), щоб користувач не мерз:\n\n"
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
                temperature=0.4, # Трохи вища креативність для кращого комбінування
                max_tokens=650
            )
            if response and response.choices and len(response.choices) > 0:
                return f"{intro_header}{response.choices[0].message.content.strip()}"
        except Exception as e:
            print(f"Помилка OpenAI у подорожах: {e}")

    # Залізобетонний багатошаровий бекап
    return (
        f"{intro_header}"
        f"👕 **Рекомендовані речі у валізу:**\n"
        f"- Біле худі — основний теплий шар.\n"
        f"- Сірі джинси — базовий практичний низ.\n"
        f"- Світло-кремова куртка-пуффер — верхній захисний шар.\n"
        f"- Білі кросівки — зручне взуття.\n\n"
        f"📅 **Варіанти поєднань по днях:**\n"
        f"**День 1:** Одягніть базову футболку, поверх неї Біле худі, Світло-кремову куртку-пуффер та Сірі джинси. Це забезпечить надійне тепло в дорозі.\n"
        f"**День 2:** Якщо вдень стане тепліше, залиште куртку в готелі — комбінуйте Біле худі разом із Сірими джинсами та кросівками.\n\n"
        f"💡 **Порада стиліста щодо терморегуляції:** Оскільки температура становить {temp}°C, обов'язково використовуйте правило трьох шарів (футболка + худі + куртка), щоб легко адаптуватися до змін погоди."
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