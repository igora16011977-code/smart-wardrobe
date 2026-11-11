"""AI-функції бота «Шо одіти?».

Розпізнавання фото виконується Gemini через офіційний Google Gen AI SDK.
Інші текстові рекомендації використовують OpenAI, якщо налаштований ключ.
"""

import os
from typing import Any, Iterable

import config


def _get_openai_client():
    """Повертає OpenAI-клієнт або None, якщо ключ не налаштований."""
    api_key = getattr(config, "OPENAI_API_KEY", None) or os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None

    try:
        from openai import OpenAI
        return OpenAI(api_key=api_key)
    except Exception as exc:
        print(f"Не вдалося ініціалізувати OpenAI: {exc}")
        return None


def _get_gemini_client():
    """Повертає Gemini-клієнт; помилки конфігурації пояснюються виклику."""
    api_key = getattr(config, "GEMINI_API_KEY", None) or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Не налаштовано GEMINI_API_KEY. Додайте ключ Gemini у Render → "
            "Environment та локальний .env."
        )

    try:
        from google import genai
        return genai.Client(api_key=api_key)
    except ImportError as exc:
        raise RuntimeError(
            "Не встановлено пакет google-genai. Оновіть requirements.txt "
            "і виконайте повторний Deploy."
        ) from exc
    except Exception as exc:
        raise RuntimeError(f"Не вдалося ініціалізувати Gemini: {exc}") from exc


def _detect_image_mime(image_bytes: bytes) -> str:
    """Визначає MIME-тип за сигнатурою зображення."""
    if not image_bytes:
        raise ValueError("Отримано порожній файл фотографії.")

    if image_bytes.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if image_bytes.startswith(b"RIFF") and image_bytes[8:12] == b"WEBP":
        return "image/webp"

    raise ValueError(
        "Формат фотографії не розпізнано. Надішліть зображення у форматі JPG, PNG або WEBP."
    )


def analyze_clothing_image(image_bytes: bytes) -> str:
    """Аналізує реальне фото одягу та повертає короткий опис українською."""
    if not isinstance(image_bytes, (bytes, bytearray)) or not image_bytes:
        raise ValueError("Не отримано дані фотографії.")

    mime_type = _detect_image_mime(bytes(image_bytes))
    client = _get_gemini_client()

    try:
        from google.genai import types

        prompt = (
            "Ти — уважний асистент для каталогізації одягу. Проаналізуй прикріплену "
            "фотографію і створи короткий фактичний опис українською мовою для "
            "особистого гардероба.\n"
            "Визнач: 1) тип речі; 2) основний видимий колір і відтінок; "
            "3) фасон/крій; 4) видимий матеріал або фактуру, лише якщо це можна "
            "обґрунтовано визначити.\n"
            "Не вигадуй бренд, склад тканини, сезон, призначення чи деталі, яких "
            "не видно. Якщо відтінок темний — не називай його світлим. "
            "Якщо колір неоднозначний, прямо зазнач це.\n"
            "Поверни лише один опис одним реченням, без вступу, списків, емодзі "
            "та слів «на фото зображено»."
        )

        image_part = types.Part.from_bytes(
            data=bytes(image_bytes),
            mime_type=mime_type,
        )
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        response = client.models.generate_content(
            model=model_name,
            contents=[prompt, image_part],
            config=types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=160,
            ),
        )

        description = (getattr(response, "text", None) or "").strip()
        if not description:
            raise RuntimeError("Gemini не повернув текстового опису фотографії.")

        # Не дозволяємо зберегти випадкову службову відповідь замість опису.
        return description.strip('"').strip()

    except Exception as exc:
        raise RuntimeError(f"Не вдалося розпізнати одяг через Gemini: {exc}") from exc


def _wardrobe_lines(wardrobe_items: Iterable[Any]) -> list[str]:
    """Перетворює записи БД (file_id, description, id, category) на текст."""
    lines = []
    for item in wardrobe_items:
        if isinstance(item, (tuple, list)) and len(item) >= 4:
            file_id, description, item_id, category = item[:4]
            lines.append(
                f"ID {item_id} | категорія: {category} | опис: {description}"
            )
        else:
            lines.append(str(item))
    return lines


def _ask_openai(prompt: str, max_tokens: int = 700) -> str | None:
    client = _get_openai_client()
    if client is None:
        return None

    try:
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=max_tokens,
        )
        if response.choices and response.choices[0].message.content:
            return response.choices[0].message.content.strip()
    except Exception as exc:
        print(f"Помилка OpenAI: {exc}")
    return None


def generate_outfit_recommendation(
    weather_info: dict, wardrobe_items: list, event: str
) -> str:
    temp = weather_info.get("temp", weather_info.get("temperature", 12))
    feels_like = weather_info.get("feels_like", weather_info.get("feels_like_temperature", temp))
    condition = weather_info.get("description", weather_info.get("condition", "погодні умови невідомі"))
    wind_data = weather_info.get("wind", {})
    wind = wind_data.get("speed", 0) if isinstance(wind_data, dict) else wind_data
    humidity = weather_info.get("humidity", "невідомо")
    items_text = "\n".join(f"- {line}" for line in _wardrobe_lines(wardrobe_items))

    weather_header = (
        f"🌡️ Температура: {temp}°C (відчувається як {feels_like}°C)\n"
        f"☁️ Погода: {condition}\n"
        f"💨 Вітер: {wind} м/с | 💧 Вологість: {humidity}%\n\n"
    )

    prompt = (
        "Ти — практичний персональний стиліст. Склади образ лише з речей, "
        "які є в наведеному гардеробі. Не додавай вигадані речі; якщо певної "
        "категорії немає, так і напиши. Врахуй температуру, відчутну температуру, "
        "погоду та подію. Відповідай українською, структуровано:\n"
        "👕 Базовий верх\n🧥 Середній шар\n🧥 Верхній одяг\n"
        "👖 Низ\n👟 Взуття\n💍 Аксесуари\n✨ Чому цей образ доречний\n\n"
        f"Погода: {temp}°C, відчувається як {feels_like}°C, {condition}, "
        f"вітер {wind} м/с. Подія: {event}.\n"
        f"ГАРДЕРОБ:\n{items_text}"
    )

    recommendation = _ask_openai(prompt, max_tokens=650)
    if recommendation:
        return weather_header + recommendation

    return (
        weather_header
        + "Не вдалося отримати рекомендацію від ШІ. Перевірте OPENAI_API_KEY "
          "та доступність сервісу. Щоб не вигадувати речі, образ автоматично "
          "не сформовано."
    )


def generate_trip_itinerary(
    weather_desc: str, wardrobe_items: list, destination: str, days: int
) -> str:
    items_text = "\n".join(f"- {line}" for line in _wardrobe_lines(wardrobe_items))
    prompt = (
        "Ти — персональний стиліст для планування подорожей. Склади компактну "
        "капсулу та окремий комплект на кожен день поїздки. Використовуй лише "
        "речі з наданого гардероба; не вигадуй відсутні предмети. Якщо категорії "
        "бракує, прямо вкажи це. Враховуй прогноз погоди. Відповідай українською.\n\n"
        f"Місто: {destination}\nТривалість: {days} днів\n"
        f"Прогноз: {weather_desc}\nГАРДЕРОБ:\n{items_text}\n\n"
        "Спочатку переліч компактну капсулу, потім розпиши образи за днями "
        "(верх, низ, взуття, верхній шар та аксесуари)."
    )
    result = _ask_openai(prompt, max_tokens=1000)
    if result:
        return result
    return (
        "Не вдалося сформувати план подорожі через ШІ. Перевірте OPENAI_API_KEY "
        "та доступність сервісу."
    )


def generate_shopping_recommendation(wardrobe_items: list) -> str:
    items_text = "\n".join(f"- {line}" for line in _wardrobe_lines(wardrobe_items))
    prompt = (
        "Ти — персональний стиліст. Проаналізуй наведений гардероб і визнач "
        "можливі прогалини в базових речах. Запропонуй 3–4 покупки, але не "
        "стверджуй, що користувач уже має речі, яких немає у списку. Поясни, "
        "з чим із наявного гардероба поєднувати кожну рекомендацію. "
        "Відповідай українською.\n\n"
        f"ГАРДЕРОБ:\n{items_text}"
    )
    result = _ask_openai(prompt, max_tokens=650)
    if result:
        return result
    return (
        "Не вдалося проаналізувати гардероб через ШІ. Перевірте OPENAI_API_KEY "
        "та доступність сервісу."
    )
