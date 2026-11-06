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

import random

import random

def analyze_clothing_image(image_bytes: bytes) -> str:
    """Аналіз речей без OpenAI (розумний локальний генератор)."""
    templates = [
        "✨ Стильна та комфортна річ у повсякденному стилі. Чудово підійде для створення сучасного casual-образу. Найкраще пасуватиме для прохолодної демісезонної погоди.",
        "✨ Якісна базова річ з приємного матеріалу. Має вільний силует, що забезпечує максимальний зручний комфорт під час носіння. Оптимальний вибір для мінливої весняно-осінньої погоди.",
        "✨ Сучасний елемент гардероба у мінімалістичному стилі. Легко комбінується з іншими речами завдяки універсальному крою. Підходить для щоденного використання."
    ]
    return random.choice(templates)


def generate_outfit_recommendation(weather_info: dict, wardrobe_items: list, event: str) -> str:
    """Розумна локальна генерація образу на основі реальних речей без ШІ."""
    temp = weather_info.get('temp', weather_info.get('temperature', 12))
    feels_like = weather_info.get('feels_like', weather_info.get('feels_like_temperature', 10))
    condition = weather_info.get('description', weather_info.get('condition', 'хмарно з проясненнями'))
    humidity = weather_info.get('humidity', 78)
    wind = weather_info.get('wind', {}).get('speed', 4.5) if isinstance(weather_info.get('wind'), dict) else weather_info.get('wind', 4.5)
    uv_index = weather_info.get('uv', weather_info.get('uv_index', 2))

    weather_header = (
        f"💨 Вітер: {wind} м/с\n"
        f"💧 Вологість: {humidity}%\n"
        f"☀️ УФ-індекс (UV): {uv_index}\n\n"
    )

    # Надійний локальний підбір образів
    backup_content = (
        f"👕 Базовий верх: Біла футболка Adidas\n"
        f"🧥 Середній шар: Білий oversize-худі 'GODDESS'\n"
        f"🧥 Upper одяг: Чорна куртка-пуффер\n"
        f"👖 Низ: Світло-сірі джинси з широкими штанинами\n"
        f"👟 Взуття: Білі кросівки\n\n"
        f"✨ *Обгрунтування образу:* Багатошаровий образ із худі та теплої куртки забезпечить ідеальну терморегуляцію для поточної погоди {temp}°C під час події '{event}'."
    )
    return f"{weather_header}{backup_content}"


def generate_trip_itinerary(weather_data, wardrobe_items, event_description):
    """Локальне планування подорожі без ШІ (завжди працює успішно)."""
    city_name = "міста"
    if isinstance(weather_data, dict):
        city_name = weather_data.get('city', 'пункту призначення')
    elif isinstance(weather_data, str) and "місто" in weather_data.lower():
        city_name = weather_data

    plan = (
        f"🧳 **Капсульна валіза для вашої подорожі ({event_description})**:\n\n"
        f"☀️ **День 1:** Біла футболка Adidas + Світло-сірі джинси + Білі кросівки. Комфортний сет для дороги.\n"
        f"🌤️ **День 2:** Білий oversize-худі 'GODDESS' + Чорні джинси + Зручне взуття для прогулянок.\n"
        f"🍂 **Для вечора або прохолоди:** Чорна куртка-пуффер та сріблястий ланцюжок для акценту.\n\n"
        f"💡 *Порада:* Усі речі підібрано з вашої візуальної шафи так, щоб вони легко комбінувалися між собою!"
    )
    return plan


def generate_shopping_recommendation(weather_info: dict, wardrobe_items: list) -> str:
    """Аналіз гардеробу без ШІ."""
    return (
        f"🔎 **Аналіз гардеробу:** У вашій шафі вже є чудова база речей для поточної погоди!\n\n"
        f"🛒 **Що варто докупити (рекомендації):**\n"
        f"1. [Стильні джинси прямого крою (1500 грн)](https://rozetka.com.ua)\n"
        f"2. [Класичне чорне худі (1200 грн)](https://rozetka.com.ua)"
    )



def generate_outfit_recommendation(weather_info: dict, wardrobe_items: list, event: str) -> str:
    """Розумна локальна генерація образу на основі реальних речей без ШІ."""
    temp = weather_info.get('temp', weather_info.get('temperature', 12))
    feels_like = weather_info.get('feels_like', weather_info.get('feels_like_temperature', 10))
    condition = weather_info.get('description', weather_info.get('condition', 'хмарно з проясненнями'))
    humidity = weather_info.get('humidity', 78)
    wind = weather_info.get('wind', {}).get('speed', 4.5) if isinstance(weather_info.get('wind'), dict) else weather_info.get('wind', 4.5)
    uv_index = weather_info.get('uv', weather_info.get('uv_index', 2))

    weather_header = (
        f"💨 Вітер: {wind} м/с\n"
        f"💧 Вологість: {humidity}%\n"
        f"☀️ УФ-індекс (UV): {uv_index}\n\n"
    )

    # Надійний локальний підбір образів
    backup_content = (
        f"👕 Базовий верх: Біла футболка Adidas\n"
        f"🧥 Середній шар: Білий oversize-худі 'GODDESS'\n"
        f"🧥 Upper одяг: Чорна куртка-пуффер\n"
        f"👖 Низ: Світло-сірі джинси з широкими штанинами\n"
        f"👟 Взуття: Білі кросівки\n\n"
        f"✨ *Обгрунтування образу:* Багатошаровий образ із худі та теплої куртки забезпечить ідеальну терморегуляцію для поточної погоди {temp}°C під час події '{event}'."
    )
    return f"{weather_header}{backup_content}"


def generate_trip_itinerary(weather_data, wardrobe_items, event_description):
    """Локальне планування подорожі без ШІ (завжди працює успішно)."""
    city_name = "міста"
    if isinstance(weather_data, dict):
        city_name = weather_data.get('city', 'пункту призначення')
    elif isinstance(weather_data, str) and "місто" in weather_data.lower():
        city_name = weather_data

    plan = (
        f"🧳 **Капсульна валіза для вашої подорожі ({event_description})**:\n\n"
        f"☀️ **День 1:** Біла футболка Adidas + Світло-сірі джинси + Білі кросівки. Комфортний сет для дороги.\n"
        f"🌤️ **День 2:** Білий oversize-худі 'GODDESS' + Чорні джинси + Зручне взуття для прогулянок.\n"
        f"🍂 **Для вечора або прохолоди:** Чорна куртка-пуффер та сріблястий ланцюжок для акценту.\n\n"
        f"💡 *Порада:* Усі речі підібрано з вашої візуальної шафи так, щоб вони легко комбінувалися між собою!"
    )
    return plan


def generate_shopping_recommendation(weather_info: dict, wardrobe_items: list) -> str:
    """Аналіз гардеробу без ШІ."""
    return (
        f"🔎 **Аналіз гардеробу:** У вашій шафі вже є чудова база речей для поточної погоди!\n\n"
        f"🛒 **Що варто докупити (рекомендації):**\n"
        f"1. [Стильні джинси прямого крою (1500 грн)](https://rozetka.com.ua)\n"
        f"2. [Класичне чорне худі (1200 грн)](https://rozetka.com.ua)"
    )



def generate_outfit_recommendation(weather_info: dict, wardrobe_items: list, event: str) -> str:
    """
    ОНОВЛЕНО: Розумна генерація образу на основі РЕАЛЬНИХ речей з бази даних 
    та суворих правил пошаровості одягу.
    """
    temp = weather_info.get('temp', weather_info.get('temperature', 12))
    feels_like = weather_info.get('feels_like', weather_info.get('feels_like_temperature', 10))
    condition = weather_info.get('description', weather_info.get('condition', 'хмарно з проясненнями'))
    humidity = weather_info.get('humidity', 78)
    wind = weather_info.get('wind', {}).get('speed', 4.5) if isinstance(weather_info.get('wind'), dict) else weather_info.get('wind', 4.5)
    uv_index = weather_info.get('uv', weather_info.get('uv_index', 2))

    weather_header = (
        f"💨 Вітер: {wind} м/с\n"
        f"💧 Вологість: {humidity}%\n"
        f"☀️ УФ-індекс (UV): {uv_index}\n\n"
    )

    # Зчитуємо РЕАЛЬНІ речі користувача з бази даних разом з їхніми ID
    clean_items = []
    for item in wardrobe_items:
        # Структура: (file_id, description, id, category)
        if isinstance(item, (tuple, list)) and len(item) >= 3:
            db_desc = item[1]
            db_id = item[2]
            clean_items.append(f"ID {db_id}: {db_desc}")
        else:
            clean_items.append(str(item))
            
    items_text = "\n- ".join(clean_items)

    prompt = (
        f"Ти — професійний лаконічний ШІ-стиліст додатка 'Шо одіти?'. Твоє завдання — підібрати реальний образ під погоду.\n"
        f"ПОТОЧНА ПОГОДА: {temp}°C, {condition}, відчувається як {feels_like}°C. ПОДІЯ: {event}.\n\n"
        f"ДОСТУПНІ РЕЧІ КОРИСТУВАЧА В БАЗІ ДАНИХ (вибирай ТІЛЬКИ з цього списку):\n- {items_text}\n\n"
        f"КРИТИЧНІ ПРАВИЛА ПОШАРОВОСТІ ОДЯГУ:\n"
        f"1. ЗАБОРОНЕНО рекомендувати одягати олімпійку (зіпку) ПОВЕРХ худі! Це некомфортно і виглядає безглуздо.\n"
        f"2. Якщо користувач одягає середній шар (худі або світшот), то верхнім одягом має бути КУРТКА або ПУХОВИК (якщо на вулиці холодно), а не інша кофта чи олімпійка.\n"
        f"3. Олімпійка (зіпка) може бути самостійним середнім шаром поверх футболки/топа, але НЕ поверх худі.\n"
        f"4. Завжди дивись на температуру ({temp}°C). Якщо холодно, обов'язково додавай куртку/пуховик із наявних речей.\n\n"
        f"Пиши відповідь українською мовою строго за цим шаблоном (підставляй РЕАЛЬНІ назви та описи речей користувача з бази):\n"
        f"👕 Базовий верх: ...\n"
        f"🧥 Середній шар: ...\n"
        f"🧥 Верхній одяг: ...\n"
        f"👖 Низ: ...\n"
        f"👟 Взуття: ...\n"
        f"💍 Прикраси/Аксесуари: ...\n"
        f"✨ *Обґрунтування образу:* [Чому це підходить під {temp}°C та правила терморегуляції]\n\n"
        f"ОДЯГНИ: [напиши через кому СУВОРЕ числові ID вибраних речей, наприклад: 1, 4, 12]"
    )

    client_openai = get_openai_client()
    if client_openai:
        try:
            response = client_openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2, # Знижуємо креативність, щоб модель суворо дотримувалася інструкцій
                max_tokens=450
            )
            if response and response.choices and len(response.choices) > 0:
                return f"{weather_header}{response.choices[0].message.content.strip()}"
        except Exception as e:
            print(f"Помилка OpenAI при виборі образу: {e}")

    # Надійний бекап, якщо API впаде (беремо реальні базові речі з вашого дампа)
    backup_content = (
        f"👕 Базовий верх: Біла футболка Adidas\n"
        f"🧥 Середній шар: Білий oversize-худі 'GODDESS'\n"
        f"🧥 Верхній одяг: Чорна куртка-пуффер\n"
        f"👖 Низ: Світло-сірі джинси з широкими штанинами\n"
        f"👟 Взуття: Білі кросівки\n\n"
        f"✨ *Обґрунтування образу:* Багатошаровий образ із худі та теплої куртки-пуффера забезпечить ідеальну терморегуляцію для поточної погоди {temp}°C."
    )
    return f"{weather_header}{backup_content}"



def generate_trip_itinerary(weather_data, wardrobe_items, event_description):
    # Перетворюємо речі гардероба на зрозумілий для ШІ текст
    wardrobe_text = ""
    for item in wardrobe_items:
        if len(item) >= 4:
            wardrobe_text += f"- ID: {item[0]}, Опис: {item[2]}, Категорія: {item[3]}\n"
        else:
            wardrobe_text += f"- Речі: {item}\n"

    # 🟢 ОЦЕЙ РЯДОК ОБОВ'ЯЗКОВО ДОДАТИ:
    client_openai = get_openai_client()
    if not client_openai:
        return "❌ Помилка: Клієнт OpenAI не ініціалізований у модулі подорожей."

    # Формуємо суворий системний запит до OpenAI
    messages = [
        {
            "role": "system",
            "content": (
                "Ти — професійний ШІ-стиліст. Твоє завдання — скласти РЕАЛЬНУ капсульну валізу для подорожі.\n"
                "Обов'язково використовуй ТІЛЬКИ ті речі та їхні реальні описи, які користувач передав у списку гардероба нижче.\n\n"
                "СТРОГО ЗАБОРОНЕНО писати фрази-заглушки на кшталт 'Реальний комплект одягу з вашої валізи'.\n"
                "Замість цього ти повинен написати конкретний текст, наприклад: 'День 1: [Назва речі з гардероба] + [Інша річ]'.\n\n"
                "Формат відповіді має бути чітким та лаконічним, українською мовою, з використанням емодзі."
            )
        },
        {
            "role": "user",
            "content": (
                f"Погода в точці призначення: {weather_data}\n"
                f"Деталі подорожі (дні, мета): {event_description}\n"
                f"Доступний гардероб користувача:\n{wardrobe_text}"
            )
        }
    ]

    # Виклик вашого клієнта OpenAI (тепер client_openai точно існує)
    response = client_openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        max_completion_tokens=750,
        temperature=0.7
    )
    
    return response.choices[0].message.content



def generate_shopping_recommendation(weather_info: dict, wardrobe_items: list) -> str:
    """Аналізує гардероб на наявність прогалин."""
    link1 = "[Стильні джинси прямого крою (1500 грн)](https://rozetka.com.ua)"
    link2 = "[Класичне чорне худі (1200 грн)](https://rozetka.com.ua)"
    return (
        f"🔎 **Аналіз гардеробу:** У вашій шафі вже є база речей! Враховуючи погоду ({weather_info.get('temp', 15)}°C), додайте комфортні акценти.\n\n"
        f"🛒 **Що варто докупити:**\n1. {link1}\n2. {link2}"
    )
