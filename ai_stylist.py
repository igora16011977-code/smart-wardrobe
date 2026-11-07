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
        f"💕 Чому цей образ ідеальний: (Напиши комплімент дівчині та поясни, чому ці шари будуть комфортні для {temp}°C та події '{event}')"
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
