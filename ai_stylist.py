"""AI-функції бота «Шо одіти?» на базі Google Gemini.

Усі текстові функції та аналіз фотографій використовують Gemini.
Збережено публічні назви функцій і сигнатури, які викликає bot.py.
"""

import os
import time
from typing import Any, Iterable

import config


_RETRY_DELAYS = (2, 5, 10)
_RETRYABLE_CODES = {429, 500, 502, 503, 504}


def _get_gemini_client():
    """Створює клієнт Gemini або повертає зрозумілу помилку конфігурації."""
    api_key = getattr(config, "GEMINI_API_KEY", None) or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Не налаштовано GEMINI_API_KEY. Перевірте Render → Environment."
        )

    try:
        from google import genai
        return genai.Client(api_key=api_key)
    except ImportError as exc:
        raise RuntimeError(
            "Не встановлено пакет google-genai. Перевірте requirements.txt."
        ) from exc
    except Exception as exc:
        raise RuntimeError(f"Не вдалося ініціалізувати Gemini: {exc}") from exc


def _is_retryable_error(exc: Exception) -> bool:
    """Визначає тимчасові помилки API, для яких варто повторити запит."""
    code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    if code in _RETRYABLE_CODES:
        return True

    text = str(exc).upper()
    return any(marker in text for marker in (
        "429", "RESOURCE_EXHAUSTED", "500", "INTERNAL SERVER ERROR",
        "502", "BAD GATEWAY", "503", "UNAVAILABLE", "504",
        "GATEWAY TIMEOUT", "SERVICE UNAVAILABLE",
    ))


def _ask_gemini(prompt: str, max_tokens: int = 700) -> str:
    """Надсилає текстовий запит до Gemini з повторними спробами."""
    if not prompt or not prompt.strip():
        raise ValueError("Порожній запит до Gemini.")

    client = _get_gemini_client()
    from google.genai import types

    model_name = (
        os.getenv("GEMINI_MODEL")
        or getattr(config, "GEMINI_MODEL", None)
        or "gemini-3.5-flash-lite"
    )

    for attempt in range(len(_RETRY_DELAYS) + 1):
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.4,
                    max_output_tokens=max_tokens,
                ),
            )
            result = (getattr(response, "text", None) or "").strip()
            if not result:
                raise RuntimeError("Gemini не повернув текстової відповіді.")
            return result
        except Exception as exc:
            if not _is_retryable_error(exc) or attempt >= len(_RETRY_DELAYS):
                raise RuntimeError(f"Помилка запиту до Gemini: {exc}") from exc

            delay = _RETRY_DELAYS[attempt]
            print(
                f"Gemini тимчасово недоступний (спроба {attempt + 1}/"
                f"{len(_RETRY_DELAYS) + 1}). Повтор через {delay} с."
            )
            time.sleep(delay)

    raise RuntimeError("Не вдалося отримати відповідь від Gemini.")


def _detect_image_mime(image_bytes: bytes) -> str:
    """Визначає MIME-тип зображення за сигнатурою файлу."""
    if not image_bytes:
        raise ValueError("Отримано порожній файл фотографії.")
    if image_bytes.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if image_bytes.startswith(b"RIFF") and image_bytes[8:12] == b"WEBP":
        return "image/webp"
    raise ValueError(
        "Формат фотографії не розпізнано. Надішліть JPG, PNG або WEBP."
    )


def analyze_clothing_image(image_bytes: bytes) -> str:
    """Аналізує фото одягу та повертає короткий фактичний опис українською."""
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
            "не видно. Якщо колір неоднозначний, прямо зазнач це.\n"
            "Поверни лише один опис одним реченням, без вступу, списків та емодзі."
        )
        image_part = types.Part.from_bytes(data=bytes(image_bytes), mime_type=mime_type)
        model_name = (
            os.getenv("GEMINI_MODEL")
            or getattr(config, "GEMINI_MODEL", None)
            or "gemini-3.5-flash-lite"
        )

        for attempt in range(len(_RETRY_DELAYS) + 1):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=[prompt, image_part],
                    config=types.GenerateContentConfig(max_output_tokens=160),
                )
                description = (getattr(response, "text", None) or "").strip()
                if not description:
                    raise RuntimeError("Gemini не повернув опис фотографії.")
                return description.strip('"').strip()
            except Exception as exc:
                if not _is_retryable_error(exc) or attempt >= len(_RETRY_DELAYS):
                    raise
                delay = _RETRY_DELAYS[attempt]
                print(
                    f"Gemini тимчасово недоступний під час аналізу фото "
                    f"(спроба {attempt + 1}/{len(_RETRY_DELAYS) + 1}). "
                    f"Повтор через {delay} с."
                )
                time.sleep(delay)
    except Exception as exc:
        raise RuntimeError(f"Не вдалося розпізнати одяг через Gemini: {exc}") from exc

    raise RuntimeError("Не вдалося розпізнати одяг через Gemini.")


def _wardrobe_lines(wardrobe_items: Iterable[Any]) -> list[str]:
    """Перетворює записи БД на зрозумілий перелік речей."""
    lines = []
    for item in wardrobe_items or []:
        if isinstance(item, (tuple, list)) and len(item) >= 4:
            _file_id, description, item_id, category = item[:4]
            lines.append(f"ID {item_id} | категорія: {category} | опис: {description}")
        else:
            lines.append(str(item))
    return lines


def generate_outfit_recommendation(
    weather_info: dict, wardrobe_items: list, event: str
) -> str:
    """Формує образ із наявного гардероба з урахуванням погоди та події."""
    weather_info = weather_info or {}
    temp = weather_info.get("temp", weather_info.get("temperature", 12))
    feels_like = weather_info.get(
        "feels_like", weather_info.get("feels_like_temperature", temp)
    )
    condition = weather_info.get(
        "description", weather_info.get("condition", "погодні умови невідомі")
    )
    wind_data = weather_info.get("wind", {})
    wind = wind_data.get("speed", 0) if isinstance(wind_data, dict) else wind_data
    humidity = weather_info.get("humidity", "невідомо")
    items = _wardrobe_lines(wardrobe_items)
    items_text = "\n".join(f"- {line}" for line in items) or "Гардероб поки порожній."

    weather_header = (
        f"🌡️ Температура: {temp}°C (відчувається як {feels_like}°C)\n"
        f"☁️ Погода: {condition}\n"
        f"💨 Вітер: {wind} м/с | 💧 Вологість: {humidity}%\n\n"
    )

    prompt = (
        "Ти — практичний персональний стиліст. Склади доречний образ ВИКЛЮЧНО "
        "з речей, перелічених у гардеробі. Не вигадуй одяг, взуття чи аксесуари. "
        "Якщо потрібної категорії немає, прямо напиши про це. Врахуй температуру, "
        "відчутну температуру, опади/стан погоди, вітер і подію. Для холодної "
        "погоди обов'язково зверни увагу на теплий верхній одяг та взуття, якщо "
        "вони є в гардеробі. Не пропонуй літній або недостатньо теплий комплект "
        "для низької температури. Відповідай українською, стисло й структуровано.\n\n"
        f"ПОГОДА: температура {temp}°C; відчувається як {feels_like}°C; "
        f"умови: {condition}; вітер: {wind} м/с; вологість: {humidity}%.\n"
        f"ПОДІЯ: {event}.\n\n"
        f"ГАРДЕРОБ КОРИСТУВАЧА:\n{items_text}\n\n"
        "Формат відповіді:\n"
        "👕 Верх\n🧥 Верхній одяг/теплий шар\n👖 Низ\n👟 Взуття\n"
        "🧣 Аксесуари (лише якщо є в гардеробі)\n✨ Чому цей комплект доречний.\n"
        "Для кожної речі використовуй її опис або ID зі списку, щоб користувач "
        "міг знайти її у своєму гардеробі."
    )

    try:
        return weather_header + _ask_gemini(prompt, max_tokens=700)
    except Exception as exc:
        print(f"Помилка Gemini під час підбору образу: {exc}")
        return (
            weather_header
            + "Не вдалося отримати рекомендацію від Gemini. "
              "Спробуйте ще раз трохи пізніше."
        )


def generate_trip_itinerary(
    weather_desc: str, wardrobe_items: list, destination: str, days: int
) -> str:
    """Планує капсулу та комплекти на кожен день подорожі через Gemini."""
    items_text = "\n".join(
        f"- {line}" for line in _wardrobe_lines(wardrobe_items)
    ) or "Гардероб поки порожній."
    prompt = (
        "Ти — персональний стиліст для планування подорожей. Склади компактну "
        "капсулу та окремий комплект на кожен день поїздки. Використовуй лише "
        "речі з наданого гардероба; не вигадуй відсутні предмети. Якщо категорії "
        "бракує, прямо вкажи це. Враховуй прогноз погоди та практичність "
        "повторного поєднання речей. Відповідай українською.\n\n"
        f"Місто: {destination}\nТривалість: {days} днів\n"
        f"Прогноз: {weather_desc}\nГАРДЕРОБ:\n{items_text}\n\n"
        "Спочатку переліч компактну капсулу, потім розпиши образи за днями "
        "(верх, низ, взуття, верхній шар та аксесуари). Для кожного дня "
        "використовуй тільки предмети з наведеного гардероба."
    )
    try:
        return _ask_gemini(prompt, max_tokens=1100)
    except Exception as exc:
        print(f"Помилка Gemini під час планування подорожі: {exc}")
        return "Не вдалося сформувати план подорожі через Gemini. Спробуйте ще раз пізніше."


def generate_shopping_recommendation(wardrobe_items: list) -> str:
    """Пропонує покупки на основі наявного гардероба через Gemini."""
    items_text = "\n".join(
        f"- {line}" for line in _wardrobe_lines(wardrobe_items)
    ) or "Гардероб поки порожній."
    prompt = (
        "Ти — персональний стиліст. Проаналізуй наведений гардероб і визнач "
        "можливі прогалини в базових речах. Запропонуй 3–4 доречні покупки, "
        "але не стверджуй, що користувач уже має речі, яких немає у списку. "
        "Для кожної пропозиції поясни, з чим із наявного гардероба її можна "
        "поєднувати. Не вигадуй конкретні бренди, магазини чи ціни. "
        "Відповідай українською.\n\n"
        f"ГАРДЕРОБ:\n{items_text}"
    )
    try:
        return _ask_gemini(prompt, max_tokens=700)
    except Exception as exc:
        print(f"Помилка Gemini під час рекомендацій покупок: {exc}")
        return "Не вдалося проаналізувати гардероб через Gemini. Спробуйте ще раз пізніше."
