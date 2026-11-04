import base64
import os
import openai
from groq import Groq
import config

# Ініціалізація клієнтів із перевіркою ключів
def get_openai_client():
    api_key = getattr(config, "OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
    if not api_key:
        return None
    return openai.OpenAI(api_key=api_key)

def get_groq_client():
    api_key = getattr(config, "GROQ_API_KEY", os.getenv("GROQ_API_KEY"))
    if not api_key:
        return None
    return Groq(api_key=api_key)

def analyze_clothing_image(image_bytes: bytes) -> str:
    """Розпізнає фото одягу через НОВУ актуальну модель Groq Llama 3.2 11B Vision"""
    import base64
    import os
    import config
    from groq import Groq

    base64_image = base64.b64encode(image_bytes).decode('utf-8')
    prompt = "Подивись на це фото одягу. Визнач, що це за річ, колір, стиль та погоду. 2-3 речення українською."
    
    try:
        api_key = getattr(config, "GROQ_API_KEY", os.getenv("GROQ_API_KEY"))
        if not api_key:
            return "Помилка: Ключ GROQ_API_KEY не знайдено в налаштуваннях!"
            
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model="llama-3.2-11b-vision-preview", # Стабільна робоча модель із підтримкою зору!
            messages=[
                {
                    "role": "user", 
                    "content": [
                        {"type": "text", "text": prompt}, 
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }
            ],
            timeout=20
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Помилка аналізу зображення через Groq Vision: {str(e)}"


def generate_outfit_recommendation(weather_info: dict, wardrobe_items: list, event: str) -> str:
    """Генерує текстовий образ на сьогодні з урахуванням погоди."""
    if not wardrobe_items:
        return "Гардероб порожній."
    
    formatted_items = [item[1] if isinstance(item, (tuple, list)) and len(item) > 1 else str(item) for item in wardrobe_items]
    items_text = "\n- ".join(formatted_items)
    
    rain_volume = weather_info.get("rain", 0)
    snow_volume = weather_info.get("snow", 0)
    weather_alert_instruction = ""
    
    if rain_volume > 0:
        weather_alert_instruction = "\n⚠️ УВАГА СТИЛІСТУ: Зараз іде ДОЩ! Додай у поле 'Прикраси/Аксесуари' ПАРАСОЛЮ.\n"
    elif snow_volume > 0:
        weather_alert_instruction = "\n⚠️ УВАГА СТИЛІСТУ: Зараз іде СНІГ! Додай теплі аксесуари (рукавички, шапка, шарф).\n"
    
    prompt = (
        f"Ти професійний стиліст.\n"
        f"Склади для користувача СУВОРO ОДИН готовий образ під подію '{event}' та погоду {weather_info['temp']}°C, {weather_info['description']}.\n"
        f"{weather_alert_instruction}"
        f"\nСПИСОК РЕЧЕЙ КОРИСТУВАЧА:\n- {items_text}\n\n"
        f"Заповни цей шаблон назвами з наявного списку:\n"
        f"👕 Базовий верх: [назва однієї речі]\n"
        f"🧥 Середній шар: [назва речі або Не потрібно]\n"
        f"🧥 Верхній одяг: [назва речі або Не потрібно]\n"
        f"👖 Низ: [назва лише однієї речі]\n"
        f"👟 Взуття: [актуальне взуття]\n"
        f"📿 Прикраси/Аксесуари: [аксесуари]\n"
        f"✨ Обґрунтування образу: [коротке речення]"
    )
    
    client = get_groq_client()
    if not client:
        return "Помилка: Ключ GROQ_API_KEY не знайдено!"

    # Виправлено моделі Groq (залишено діючу Llama 3.1)
    for model_name in ["llama-3.1-8b-instant", "llama3-8b-8192"]:
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=800  
            )
            if response and response.choices:
                return response.choices[0].message.content.strip()
        except Exception:
            continue
            
    return "Не вдалося отримати відповідь від ШІ стиліста. Спробуйте пізніше."


def generate_trip_itinerary(forecast_data: dict, wardrobe_items: list, event: str, days_count: int) -> str:
    """Генерує компактний капсульний набір речей у валізу."""
    if not wardrobe_items:
        return "Гардероб порожній."
    
    formatted_items = [item[1] if isinstance(item, (tuple, list)) and len(item) > 1 else str(item) for item in wardrobe_items]
    items_text = "\n- ".join(formatted_items)
    days_count = min(int(days_count), len(forecast_data.get("days", []))) if forecast_data.get("days") else int(days_count)
    
    avg_temp = forecast_data.get("temp", 15)
    unique_conditions = forecast_data.get("description", "мінлива хмарність")

    prompt = (
        f"Ти професійний стиліст, експерт із капсульного гардероба.\n"
        f"Користувач збирає мінімалістичну валізу на {days_count} днів у місто {forecast_data.get('city', 'Київ')}.\n"
        f"Прогноз погоди: в середньому {avg_temp}°C, очікується: {unique_conditions}.\n\n"
        f"ДОСТУПНИЙ ГАРДЕРОБ КОРИСТУВАЧА:\n- {items_text}\n\n"
        f"Заповни шаблон назвами речей з гардероба:\n"
        f"🎒 **КАПСУЛЬНА ВАЛІЗА:**\n"
        f"👕 **Верх**:\n- [назви речей]\n"
        f"👖 **Низ**:\n- [назви речей]\n"
        f"🧥 **Верхній одяг / Взуття**:\n- [варіанти]\n"
        f"💡 **Комбінації на кожен день**:\n[коротко]"
    )
    
    client = get_groq_client()
    if not client:
        return "Помилка: Ключ GROQ_API_KEY не знайдено!"

    for model_name in ["llama-3.1-8b-instant", "llama3-8b-8192"]:
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=800  
            )
            if response and response.choices:
                return response.choices[0].message.content.strip()
        except Exception:
            continue
            
    return "Не вдалося зібрати валізу. Спробуйте пізніше."


def generate_shopping_recommendation(weather_info: dict, wardrobe_items: list) -> str:
    """Аналізує гардероб на наявність прогалин і видає шопінг-рекомендації."""
    import database
    if not wardrobe_items:
        return "Твій гардероб повністю порожній. Щоб знайти прогалини, завантаж фото одягу!"
    
    formatted_items = [item[1] if isinstance(item, (tuple, list)) and len(item) > 1 else str(item) for item in wardrobe_items]
    items_text = "\n- ".join(formatted_items)
    
    db_products = database.get_all_shopping_items()
    products_links_feed = ""
    for prod in db_products:
        name, price, url, category, gender = prod
        products_links_feed += f"- [{name} ({price} грн)]({url} '{name.lower()}') [Категорія: {category}, Для кого: {gender}]\n"
    
    prompt = (
        f"Ти професійний стиліст і ревізор гардеробу.\n"
        f"Поточна погода: {weather_info['temp']}°C, {weather_info['description']}.\n\n"
        f"НАЯВНИЙ ГАРДЕРОБ КОРИСТУВАЧА:\n- {items_text}\n\n"
        f"Запропонуй користувачу докупити РІВНО 2 речі з бази:\n"
        f"{products_links_feed}\n"
        f"Шаблон відповіді:\n"
        f"🔎 **Аналіз гардеробу:** ...\n"
        f"🛒 **Що варто докупити:**\n1. [Назва](URL) — чому\n2. [Назва](URL) — чому"
    )
    
    client = get_groq_client()
    if not client:
        return "Помилка: Ключ GROQ_API_KEY не знайдено!"

    for model_name in ["llama-3.1-8b-instant", "llama3-8b-8192"]:
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=450
            )
            if response and response.choices:
                return response.choices[0].message.content.strip()
        except Exception:
            continue
            
    return "Не вдалося провести аналіз гардеробу. Спробуйте пізніше."
