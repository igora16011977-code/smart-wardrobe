import os
import google.generativeai as genai
import config
import random

def get_gemini_model():
    api_key = getattr(config, "GEMINI_API_KEY", os.getenv("GEMINI_API_KEY"))
    if not api_key:
        return None
    try:
        genai.configure(api_key=api_key)
        # 100% Робоча та стабільна модель на сьогодні
        return genai.GenerativeModel('gemini-1.5-flash')
    except Exception:
        return None

def analyze_clothing_image(image_bytes: bytes) -> str:
    """Аналізує фото одягу через безкоштовний ШІ Gemini та пише дівчачий опис 📸✨"""
    model = get_gemini_model()
    
    backup_descriptions = [
        "Неймовірно мила та стильна знахідка для твоєї шафи! ідеально підійде для затишного луку 🎀🌸",
        "Просто естетика Pinterest у чистому вигляді! Ця річ точно стане твоєю улюбленою 🧸🍰",
        "Витончений елемент гардероба у стилі Coquette для найніжніших образів ✨🩰",
        "Шалено стильна річ, яка додасть твоему аутфіту особливого шарму 🕊️"
    ]
    
    if not model or not image_bytes:
        return random.choice(backup_descriptions)
        
    prompt = (
        "Ти — найкраща подружка-стиліст, шалено закохана в моду та естетику Pinterest та Coquette. "
        "Подивись на це фото одягу й коротко (в одне речення) опиши його: вкажи точний тип речі (наприклад: чорні класичні брюки, сині широкі джинси, рожеве худі, срібний ланцюжок) "
        "та її колір/стиль. Пиши лаконічно, витончено й українською мовою з додаванням дівчачих емодзі."
    )
    
    try:
        image_part = {"mime_type": "image/jpeg", "data": image_bytes}
        response = model.generate_content([prompt, image_part])
        return response.text.strip()
    except Exception:
        return random.choice(backup_descriptions)

def generate_outfit_recommendation(weather_info: dict, wardrobe_items: list, event: str) -> str:
    """Генерує пошаровий образ на сьогодні під погоду та подію 🌤️👗"""
    temp = weather_info.get('temp', 12)
    condition = weather_info.get('description', 'хмарно з проясненнями')
    wind = weather_info.get('wind', {}).get('speed', 3.5)
    humidity = weather_info.get('humidity', 70)
    
    weather_header = (
        f"🌸 **Погодний щоденник:**\n"
        f"🌡️ За вікном зараз: `{temp}°C` ({condition})\n"
        f"💨 Вітерець: `{wind} м/с` | 💧 Вологість: `{humidity}%` \n\n"
    )

    clean_items = []
    for item in wardrobe_items:
        if isinstance(item, (tuple, list)) and len(item) >= 4:
            clean_items.append(f"ID {item[2]}: {item[1]} (Категорія: {item[3]})")
        else:
            clean_items.append(str(item))
            
    items_text = "\n".join(clean_items)

    prompt = (
        f"Ти — найкраща подружка-стиліст, шалено закохана в моду та естетику Coquette/Pinterest. "
        f"Склади для дівчини суперстильний образ з її реальних речей під погоду {temp}°C, {condition}. Подія: {event}.\n\n"
        f"ОСЬ РЕЧІ З ЇЇ ШАФИ:\n{items_text}\n\n"
        f"ОБОВ'ЯЗКОВО сформуй відповідь дуже красиво, мімімішно, з купою дівочих емодзі за такою структурою:\n"
        f"🧥 ВЕРХНІЙ ШАР:\n👚 БАЗОВИЙ ВЕРХ:\n👖 НИЗ:\n👟 ВЗУТТЯ:\n👜 АКСЕСУАРИ:\n\n"
        f"💕 Чому цей образ ідеальний: (Напиши комплімент дівчині та поясни, чому ці шари будуть комфортні для {temp}°C та події '{event}')"
    )

    model = get_gemini_model()
    if model:
        try:
            response = model.generate_content(prompt)
            return f"{weather_header}{response.text.strip()}"
        except Exception as e:
            return f"{weather_header}❌ Ой, красуне, ШІ-подружка припудрює носик. ({e})"
    return f"{weather_header}👕 Футболка + 👖 Джинси. Додай фото речей, щоб увімкнути магію!"

def generate_trip_itinerary(weather_desc: str, wardrobe_items: list, destination: str, days: int) -> str:
    clean_items = []
    for item in wardrobe_items:
        if isinstance(item, (tuple, list)) and len(item) >= 4:
            clean_items.append(f"ID {item[2]}: {item[1]} (Категорія: {item[3]})")
        else:
            clean_items.append(str(item))
    items_text = "\n".join(clean_items)
    
    prompt = (
        f"Ти — найкраща подружка-стиліст. Дівчина їде в місто *{destination}* на *{days} днів*.\n"
        f"Прогноз погоди там: {weather_desc}.\n\nУСІ РЕЧІ В ШАФІ:\n{items_text}\n\n"
        f"Розпиши готові комбінації речей окремо для кожного дня (День 1, День 2... аж до {days} дня) у стилі Pinterest з емодзі."
    )
    model = get_gemini_model()
    if model:
        try:
            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            return f"❌ Ой, не вдалося зібрати валізу: {e}"
    return "Помилка ініціализации ШІ-стиліста."

def generate_shopping_recommendation(wardrobe_items: list) -> str:
    clean_items = []
    for item in wardrobe_items:
        if isinstance(item, (tuple, list)) and len(item) >= 4:
            clean_items.append(f"ID {item[2]}: {item[1]} (Категорія: {item[3]})")
        else:
            clean_items.append(str(item))
    items_text = "\n".join(clean_items)
    
    prompt = (
        f"Ти — професійна дівчина-стиліст. Проаналізуй поточну шафу:\n{items_text}\n\n"
        f"Знайди прогалини у базовому гардеробі. Напиши список із 3-4 речей, яких не вистачає, з дівочими емодзі 🎀🧁."
    )
    model = get_gemini_model()
    if model:
        try:
            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            return f"❌ Не вдалося проаналізувати гардероб: {e}"
    return "Додайте більше фото вашого одягу!"
