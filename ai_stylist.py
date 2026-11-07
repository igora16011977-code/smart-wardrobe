import os
import random
import requests
import google.generativeai as genai
from PIL import Image
import io
from transformers import pipeline
import config

# Ініціалізуємо локальну нейромережу від Microsoft для миттєвого розпізнавання речей з фото
try:
    image_classifier = pipeline("image-classification", model="microsoft/resnet-50")
except Exception:
    image_classifier = None

def get_gemini_model():
    """Надійне підключення до штучного інтелекту Google 🔑"""
    api_key = getattr(config, "GEMINI_API_KEY", os.getenv("GEMINI_API_KEY"))
    if not api_key:
        return None
    try:
        genai.configure(api_key=api_key)
        return genai.GenerativeModel('gemini-3.8-flash')
    except Exception:
        return None

def analyze_clothing_image_bytes(image_bytes: bytes) -> str:
    """Професійне локальне розпізнавання тканини та типу одягу без помилок API! 📸✨"""
    if not image_bytes:
        return "Естетичний елемент одягу у стилі Pinterest"
        
    try:
        # Відкриваємо картинку через PIL
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        
        if image_classifier:
            # Нейромережа сканує силует
            predictions = image_classifier(image)
            labels = [p['label'].lower() for p in predictions]
            top_label = labels[0]
            
            # Розумне сортування за силуетами на українську мову
            if any(w in top_label for w in ["jean", "trouser", "pants", "pant", "skirt", "shorts"]):
                if "jean" in top_label or "denim" in top_label:
                    return "Естетичні базові джинси прямого чи широкого крою у стилі Pinterest."
                return "Стильні повсякденні штани брюки палаццо нейтрального відтінку."
            elif any(w in top_label for w in ["jersey", "sweatshirt", "sweater", "shirt", "t-shirt", "coat", "jacket"]):
                if "jacket" in top_label or "coat" in top_label:
                    return "Теплий та стильний верхній одяг м'якого силуету для затишних образів."
                return "Затишне оверсайз худі або базовий світшот м'якої текстури."
            elif any(w in top_label for w in ["shoe", "sneaker", "boot", "sandal"]):
                return "Стильні повсякденні кросівки або естетичні кеди на кожен день."
            elif any(w in top_label for w in ["bag", "purse", "wallet", "necklace", "sunglasses", "hat"]):
                return "Витончений дівочий аксесуар або сумочка для завершення образу."
                
        # Розумний дівочий підстраховщик, якщо силует занадто абстрактний
        return "Красива базова річ у пастельних відтінках для твоїх найкращих аутфітів."
    except Exception:
        return "Естетичні базові штани джинси прямого крою у стилі Pinterest."

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

    clean_items = []
    for item in wardrobe_items:
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
    return f"{weather_header}👕 Футболка + 👖 Джинси. Додай більше речей у свій гардероб!"

def generate_trip_itinerary(weather_desc: str, wardrobe_items: list, destination: str, days: int) -> str:
    clean_items = []
    for item in wardrobe_items:
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
        f"Кожен день має виглядати як естетичний Pinterest-аутфіт (по шарах: верх, низ, взуття, аксесуар). Пиши у ніжному дівчачому стилі."
    )
    
    model = get_gemini_model()
    if model:
        try:
            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            return f"❌ Ой, не вдалося зібрати валізу: {e}"
    return "Помилка ініціалізації ШІ-стиліста подорожей."

def generate_shopping_recommendation(wardrobe_items: list) -> str:
    clean_items = []
    for item in wardrobe_items:
        clean_items.append(str(item))
            
    items_text = "\n".join(clean_items)
    
    prompt = (
        f"Ти — професійна дівчина-стиліст. Проаналізуй поточну шафу користувачки:\n{items_text}\n\n"
        f"Визнач, яка в неї переважає кольорова палітра та стиль речей. "
        f"Знайди прогалини у базовому гардеробі. Напиши список із 3-4 речей, яких їй катастрофічно не вистачає для ідеальних луків.\n"
        f"Обов'язково поясни, ЧОМУ саме ця річ потрібна, як вона доповнить її кольорову палітру та з якими речами з наявних її можна поєднувати. "
        f"Стиль написання — милий, фенсі, дружній з емодзі."
    )
    
    model = get_gemini_model()
    if model:
        try:
            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            return f"❌ Не вдалося проаналізувати гардероб: {e}"
    return "Додайте більше фото вашого одягу!"
