import os
import google.generativeai as genai
import config

def get_gemini_model():
    api_key = getattr(config, "GEMINI_API_KEY", os.getenv("GEMINI_API_KEY"))
    if not api_key:
        return None
    try:
        genai.configure(api_key=api_key)
        # ВИПРАВЛЕНО: встановлено правильну модель Gemini
        return genai.GenerativeModel('gemini-2.5-flash')
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
        print(f"Помилка Gemini при аналізі фото: {e}")
        return "Гарна базова річ нейтрального відтінку."

# Решта функцій (generate_outfit_recommendation, generate_trip_itinerary, generate_shopping_recommendation) залишаються без змін
