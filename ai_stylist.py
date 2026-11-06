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
        "✨ Стильна та комфортна річ у повсякденному стилі. Чудово підійде для створення сучасного casual-образу.",
        "✨ Якісна базова річ з приємного матеріалу. Має вільний силует, що забезпечує максимальний комфорт.",
        "✨ Сучасний елемент гардероба у мінімалістичному стилі. Легко комбінується з іншими речами."
    ]
    return random.choice(templates)

def generate_outfit_recommendation(weather_info: dict, wardrobe_items: list, event: str) -> str:
    temp = weather_info.get('temp', 12)
    condition = weather_info.get('description', 'хмарно з проясненнями')
    
    weather_header = f"💨 Вітер: {weather_info.get('wind', {}).get('speed', 4.5)} м/с\n💧 Вологість: {weather_info.get('humidity', 78)}%\n\n"

    clean_items = []
    for item in wardrobe_items:
        if isinstance(item, (tuple, list)) and len(item) >= 3:
            clean_items.append(f"ID {item[2]}: {item[1]}")
        else:
            clean_items.append(str(item))
            
    items_text = "\n- ".join(clean_items)

    prompt = (
        f"Ти — професійний лаконічний ШІ-стиліст додатка 'Шо одіти?'. Підберіть реальний образ під погоду {temp}°C, {condition}. Подія: {event}.\n"
        f"ДОСТУПНІ РЕЧІ:\n- {items_text}\n\n"
        f"Формат відповіді:\n👕 Базовий верх: ...\n"
        f"ОДЯГНИ: [числові ID через кому]"
    )

    client_openai = get_openai_client()
    if client_openai:
        try:
            response = client_openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_completion_tokens=450  # Виправлено параметр для нових моделей OpenAI
            )
            return f"{weather_header}{response.choices[0].message.content.strip()}"
        except Exception as e:
            print(f"Помилка OpenAI: {e}")

    return f"{weather_header}👕 Базовий верх: Футболка\n👖 Низ: Джинси\n✨ Локальний підбір на {temp}°C."

def generate_trip_itinerary(weather_data, wardrobe_items, event_description):
    wardrobe_text = "".join([f"- ID: {item[0]}, Опис: {item[1]}\n" for item in wardrobe_items if isinstance(item, (tuple, list))])
    client_openai = get_openai_client()
    if not client_openai:
        return "❌ Помилка: Клієнт OpenAI не ініціалізований."

    try:
        response = client_openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Ти — професійний ШІ-стиліст. Склади валізу з вказаних речей."},
                {"role": "user", "content": f"Погода: {weather_data}\nГардероб:\n{wardrobe_text}"}
            ],
            max_completion_tokens=750,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ Помилка OpenAI: {e}"

def generate_shopping_recommendation(weather_info: dict, wardrobe_items: list) -> str:
    return (
        f"🔎 **Аналіз гардеробу:** У вашій шафі вже є база речей!\n\n"
        f"🛒 **Що варто докупити:**\n"
        f"1. [Стильні джинси прямого крою (1500 грн)](https://rozetka.com.ua)\n"
        f"2. [Класичне чорне худі (1200 грн)](https://rozetka.com.ua)"
    )
