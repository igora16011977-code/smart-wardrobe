import os
import google.generativeai as genai
import config

def get_gemini_model():
    api_key = getattr(config, "GEMINI_API_KEY", os.getenv("GEMINI_API_KEY"))
    if not api_key:
        return None
    try:
        genai.configure(api_key=api_key)
        # ПОВЕРТАЄМО НАЙНОВІШУ МОДЕЛЬ 2026 РОКУ
        return genai.GenerativeModel('gemini-3.8-flash')
    except Exception:
        return None

def analyze_clothing_image(image_bytes: bytes) -> str:
    """Аналізує фото одягу через безкоштовний ШІ Gemini та пише дівчачий опис 📸✨"""
    model = get_gemini_model()
    if not model or not image_bytes:
        return "Ніжний та стильний елемент одягу для твого ідеального луку."
        
    prompt = (
        "Ти — найкраща подружка-стиліст, шалено закохана в моду та естетику Pinterest та Coquette. "
        "Подивись на це фото одягу й коротко (в одне речення) опиши його: вкажи точний тип речі (наприклад: чорні класичні брюки, сині широкі джинси, рожеве худі, срібний ланцюжок) "
        "та її колір/стиль. Пиши лаконічно, витончено й українською мовою з додаванням дівчачих емодзі."
    )
    
    try:
        image_part = {"mime_type": "image/jpeg", "data": image_bytes}
        response = model.generate_content([prompt, image_part])
        return response.text.strip()
    except Exception as e:
        print(f"Помилка Gemini API: {e}")
        return "Неймовірно мила та стильна знахідка для твоєї шафи! 🎀🌸"

# Решта функцій (generate_outfit_recommendation, generate_trip_itinerary, generate_shopping_recommendation) залишаються без змін



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
        f"🧥 ВЕРХНІЙ ШАР (Верхній одяг, якщо холодно):\n"
        f"👚 БАЗОВИЙ ВЕРХ (Худі, светрик, кардиган чи топ):\n"
        f"👖 НИЗ (Джинси, спідничка, шорти чи брюки):\n"
        f"👟 ВЗУТТЯ (Кросівки, туфельки тощо):\n"
        f"👜 АКСЕСУАРИ (Прикраси, сумочка):\n\n"
        f"💕 Чому цей образ ідеальний: (Напиши комплімент дівчині та поясни, чому ці шари будуть комфортні для {temp}°C та події '{event}')"
    )

    model = get_gemini_model()
    if model:
        try:
            response = model.generate_content(prompt)
            return f"{weather_header}{response.text.strip()}"
        except Exception as e:
            return f"{weather_header}❌ Ой, красуне, ШІ-подружка припудрює носик. Спробуй ще раз! ({e})"
    return f"{weather_header}👕 Футболка + 👖 Джинси. Додай фото речей, щоб увімкнути магію!"

def generate_trip_itinerary(weather_desc: str, wardrobe_items: list, destination: str, days: int) -> str:
    """Планує капсульну валізу в подорож 🧳✈️"""
    clean_items = []
    for item in wardrobe_items:
        if isinstance(item, (tuple, list)) and len(item) >= 4:
            clean_items.append(f"ID {item[2]}: {item[1]} (Категорія: {item[3]})")
        else:
            clean_items.append(str(item))
            
    items_text = "\n".join(clean_items)
    
    prompt = (
        f"Ти — найкраща подружка-стиліст, яка допомагає зібрати ідеальну естетичну валізу в подорож.\n"
        f"Дівчина їде в місто *{destination}* на *{days} днів*.\n"
        f"Прогноз погоди там: {weather_desc}.\n\n"
        f"УСІ РЕЧІ В ШАФІ:\n{items_text}\n\n"
        f"ТВОЄ ЗАВДАННЯ:\n"
        f"1. Склади максимально компактну, капсульну валізу (пакуй мінімум речей, які легко комбінуються між собою, щоб валіза закрилася легенько!).\n"
        f"2. Розпиши готові комбінації речей окремо для кожного дня (День 1, День 2... аж до {days} дня). "
        f"Кожен день має виглядати як естетичний Pinterest-аутфіт (по шарах: верх, низ, взуття, аксесуар). Пиши у ніжному дівчачому стилі з емодзі."
    )
    
    model = get_gemini_model()
    if model:
        try:
            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            return f"❌ Ой, не вдалося зібрати валізу: {e}"
    return "Помилка ініціализации ШІ-стиліста подорожей."

def generate_shopping_recommendation(wardrobe_items: list) -> str:
    """Аналізує гардероб і створює вішліст базових речей 🛍️🎀"""
    clean_items = []
    for item in wardrobe_items:
        if isinstance(item, (tuple, list)) and len(item) >= 4:
            clean_items.append(f"ID {item[2]}: {item[1]} (Категорія: {item[3]})")
        else:
            clean_items.append(str(item))
            
    items_text = "\n".join(clean_items)
    
    prompt = (
        f"Ти — професійна дівчина-стиліст. Проаналізуй поточну шафу користувачки:\n{items_text}\n\n"
        f"Визнач, яка в неї переважає кольорова палітра та стиль речей. "
        f"Знайди прогалини у базовому гардеробі. Напиши список із 3-4 речей, яких їй катастрофічно не вистачає для ідеальних луків.\n"
        f"Обов'язково поясни, ЧОМУ саме ця річ потрібна, як вона доповнить її кольорову палітру та з якими речами з наявних її можна поєднувати. "
        f"Стиль написання — милий, фенсі, дружній з купою дівочих емодзі 🎀🧁."
    )
    
    model = get_gemini_model()
    if model:
        try:
            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            return f"❌ Не вдалося проаналізувати гардероб: {e}"
    return "Додайте більше фото вашого одягу!"
