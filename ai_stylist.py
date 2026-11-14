"""AI-функції бота «Шо одіти?» на базі Google Gemini.

Усі текстові функції та аналіз фотографій використовують Gemini.
Збережено публічні назви функцій і сигнатури, які викликає bot.py.
"""
import re
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

def _trip_wardrobe_lines(wardrobe_items):
    """Готує перелік речей для подорожі без ID та точних дублікатів."""
    lines = []
    seen = set()

    for item in wardrobe_items or []:
        if isinstance(item, (tuple, list)) and len(item) >= 4:
            description = str(item[1]).strip()
        else:
            description = str(item).strip()

        if not description:
            continue

        normalized = re.sub(
            r"[^\w]+", " ", description.casefold()
        ).strip()

        if normalized in seen:
            continue

        seen.add(normalized)
        lines.append(description)

    return lines


def _validate_trip_capsule_count(text: str, min_items: int, max_items: int):
    """Рахує унікальні одиниці одягу в капсулі, не враховуючи взуття й аксесуари."""
    lines = text.splitlines()
    start = next((i for i, line in enumerate(lines)
                  if "компактна капсула" in line.casefold()), None)
    if start is None:
        return None, "Не знайдено розділ «Компактна капсула для подорожі»."

    end = next((i for i in range(start + 1, len(lines))
                if "образи за днями" in lines[i].casefold()), None)
    if end is None:
        return None, "Не знайдено розділ «Образи за днями поїздки»."

    clothing_categories = (
        "верхній одяг", "теплі шари", "футболки", "базовий верх",
        "штани", "джинси", "інший низ", "спідниці", "сукні",
    )
    current_category = None
    counted_items = set()

    for raw_line in lines[start + 1:end]:
        line = raw_line.strip()
        if not line:
            continue
        category_line = re.sub(r"[*#:_`]", "", line).casefold()
        if "взуття" in category_line or "аксесуари" in category_line:
            current_category = "excluded"
            continue
        item_match = re.match(r"^(?:[-•*]|\d+[.)])\s+(.+)$", line)
        if not item_match and any(
            name in category_line for name in clothing_categories
        ):
            current_category = "clothing"
            continue
        if current_category != "clothing":
            continue
        if not item_match:
            continue
        item = re.sub(r"[*_`]", "", item_match.group(1)).strip()
        normalized = re.sub(r"[^\w]+", " ", item.casefold()).strip()
        if normalized:
            counted_items.add(normalized)

    count = len(counted_items)
    if not min_items <= count <= max_items:
        return count, (
            f"У капсулі {count} одиниць одягу; потрібно від "
            f"{min_items} до {max_items}. Взуття й аксесуари не рахуються."
        )
    return count, None


def _validate_trip_itinerary(text, days):
    """Перевіряє кількість, послідовність днів і складові образів."""

    day_pattern = re.compile(
        r"(?im)^\s*(?:#{1,6}\s*)?(?:✈️\s*)?День\s+(\d+)\b"
    )

    matches = list(day_pattern.finditer(text))
    day_numbers = [int(match.group(1)) for match in matches]

    expected_days = list(range(1, days + 1))

    # Перевіряємо відсутні дні.
    missing_days = [
        number for number in expected_days
        if number not in day_numbers
    ]

    # Перевіряємо повторення та зайві дні.
    duplicates = sorted({
        number for number in day_numbers
        if day_numbers.count(number) > 1
    })

    unexpected_days = sorted({
        number for number in day_numbers
        if number not in expected_days
    })

    structure_issues = []

    if duplicates:
        structure_issues.append(
            "Повторені дні: "
            + ", ".join(map(str, duplicates))
        )

    if unexpected_days:
        structure_issues.append(
            "Зайві дні: "
            + ", ".join(map(str, unexpected_days))
        )

    if len(day_numbers) != days:
        structure_issues.append(
            f"Кількість заголовків днів: {len(day_numbers)}, "
            f"очікується: {days}"
        )

    if day_numbers != expected_days:
        structure_issues.append(
            "Неправильна послідовність днів. "
            f"Очікується: {expected_days}; отримано: {day_numbers}"
        )

    # Визначаємо текстові блоки кожного дня.
    day_sections = {}

    for index, match in enumerate(matches):
        day_number = int(match.group(1))

        start = match.end()
        end = (
            matches[index + 1].start()
            if index + 1 < len(matches)
            else len(text)
        )

        # Зберігаємо перший блок дня, щоб дублікати
        # не перезаписували його під час перевірки.
        if day_number not in day_sections:
            day_sections[day_number] = text[start:end]

    # Перевіряємо складові кожного образу.
    required_fields = [
        "Верх",
        "Верхній шар",
        "Низ",
        "Взуття",
        "Аксесуари",
    ]

    incomplete_days = {}

    for day_number in expected_days:
        section = day_sections.get(day_number, "")

        found_fields = set(re.findall(
            r"(?im)^\s*(?:[-•]\s*)?"
            r"(Верхній шар|Верх|Низ|Взуття|Аксесуари)\s*:",
            section
        ))

        missing_fields = [
            field for field in required_fields
            if field not in found_fields
        ]

        if missing_fields:
            incomplete_days[day_number] = missing_fields

    return missing_days, incomplete_days, structure_issues


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
    """Формує компактну капсулу та перевірені образи на кожен день."""

    items = _trip_wardrobe_lines(wardrobe_items)

    if not items:
        return "У твоєму гардеробі поки немає речей для формування валізи."

    items_text = "\n".join(f"- {item}" for item in items)

    min_clothing_items = 2 * days
    max_clothing_items = 3 * days

    prompt = (
        "Ти — професійний персональний стиліст для подорожей.\n\n"

        f"МІСТО: {destination}\n"
        f"ТРИВАЛІСТЬ: РІВНО {days} ДНІВ.\n"
        f"ПОГОДА: {weather_desc}\n\n"

        f"НАЯВНИЙ ГАРДЕРОБ:\n{items_text}\n\n"

        "ОБОВ'ЯЗКОВІ ПРАВИЛА:\n"
        "1. Використовуй тільки наведені речі.\n"
        "2. Не показуй ID та технічні номери.\n"
        "3. Не повторюй однакову річ у списку капсули.\n"
        "4. Різні речі одного типу не об'єднуй, якщо вони "
        "відрізняються кольором, фасоном або іншими ознаками.\n"
        "5. Не вигадуй одяг, якого немає в гардеробі.\n"
        "6. Повторно використовуй речі в різних комбінаціях.\n"
        "7. Сформуй ОБОВ'ЯЗКОВО рівно стільки днів, скільки "
        "зазначено у тривалості подорожі.\n"
        "8. Не пропускай жодного дня.\n"
        "9. Не завершуй відповідь, поки не сформуєш усі дні.\n\n"
        f"10. Компактна капсула повинна містити від {min_clothing_items} "
        f"до {max_clothing_items} одиниць одягу на всю подорож.\n"
        "11. Не включай до капсули весь гардероб — вибирай лише речі, "
        "які реально потрібні для цієї поїздки.\n"
        "12. Кількість речей має відповідати тривалості подорожі: "
        "для кожного дня використовуй повторні комбінації вже вибраних речей.\n"
        "13. Взуття та аксесуари перелічуй окремо, вони не входять "
        "до зазначеної кількості одягу.\n\n"
        "ФОРМАТ ВІДПОВІДІ:\n\n"

        "### 🧳 Компактна капсула для подорожі\n"
        "Розподіли речі за категоріями. Кожну річ подавай окремим "
        "рядком, який починається з «- »:\n"
        "Верхній одяг і теплі шари:\n- назва речі\n"
        "Футболки та базовий верх:\n- назва речі\n"
        "Штани, джинси та інший низ:\n- назва речі\n"
        "Взуття:\n- назва речі\n"
        "Аксесуари:\n- назва речі\n\n"

        "### ✈️ Образи за днями поїздки\n\n"

        "Для КОЖНОГО дня використовуй точно такий формат:\n\n"

        "### День 1 — назва образу\n"
        "Верх: назва речі.\n"
        "Верхній шар: назва речі або Не потрібен.\n"
        "Низ: назва речі.\n"
        "Взуття: назва речі.\n"
        "Аксесуари: назва речі або У гардеробі немає.\n\n"

        "Потім аналогічно День 2, День 3 і так далі "
        "до останнього дня подорожі.\n\n"

        "Кожен із п'яти пунктів повинен бути присутнім "
        "у кожному дні. Якщо певної речі немає, прямо "
        "зазнач це, не вигадуючи заміну.\n\n"

        "Наприкінці додай 2-3 короткі поради з пакування.\n"
        "Відповідай українською, структуровано та без ID.\n"
    )

    try:
        result = _ask_gemini(prompt, max_tokens=3500)

        missing_days, incomplete_days, structure_issues = (
            _validate_trip_itinerary(result, days)
        )
        capsule_count, capsule_issue = _validate_trip_capsule_count(
            result, min_clothing_items, max_clothing_items
        )
   

        if missing_days or incomplete_days or structure_issues or capsule_issue:

            problems = []

            if missing_days:
                problems.append(
                    "Відсутні дні: "
                    + ", ".join(map(str, missing_days))
                )

            for day, fields in incomplete_days.items():
                problems.append(
                    f"День {day}: відсутні поля "
                    + ", ".join(fields)
                )
            if structure_issues:
                problems.extend(structure_issues)
            if capsule_issue:
                problems.append(capsule_issue)

            correction_prompt = (
                "Ти отримав неповний план подорожі. "
                "Необхідно виправити його.\n\n"

                f"Місто: {destination}\n"
                f"Тривалість: рівно {days} днів.\n"
                f"Погода: {weather_desc}\n\n"

                f"ПОВНИЙ ДОСТУПНИЙ ГАРДЕРОБ:\n{items_text}\n\n"

                f"ПОПЕРЕДНІЙ РЕЗУЛЬТАТ:\n{result}\n\n"

                "ВИЯВЛЕНІ ПРОБЛЕМИ:\n"
                + "\n".join(problems)
                + "\n\n"

                "Створи ВИПРАВЛЕНУ ПОВНУ ВЕРСІЮ плану. "
                "Не пропускай капсулу та жодного дня. "
                "Для кожного дня обов'язково вкажи поля: "
                "Верх:, Верхній шар:, Низ:, Взуття:, Аксесуари:. "
                "Якщо річ не потрібна або відсутня, прямо зазнач це. "
                "Використовуй тільки наданий гардероб. "
                "Не показуй ID. "
                f"У капсулі має бути від {min_clothing_items} до "
                f"{max_clothing_items} унікальних одиниць одягу; "
                "взуття й аксесуари не рахуй. "
                "Кожну річ у капсулі подавай окремим рядком із маркером «- ». "
                f"Створи рівно {days} днів, не більше і не менше. "
                "Поверни повний виправлений план українською."
            )

            result = _ask_gemini(
                correction_prompt,
                max_tokens=3500
            )

            missing_days, incomplete_days, structure_issues = (
                _validate_trip_itinerary(result, days)
            )
            capsule_count, capsule_issue = _validate_trip_capsule_count(
                result, min_clothing_items, max_clothing_items
            )

        if missing_days or incomplete_days or structure_issues or capsule_issue:
            problems = []

            if missing_days:
                problems.append(f"Відсутні дні: {missing_days}")

            if incomplete_days:
                problems.append(f"Неповні дні: {incomplete_days}")

            if structure_issues:
                problems.extend(structure_issues)
            if capsule_issue:
                problems.append(capsule_issue)

            result += "\n\n⚠️ План потребує перевірки: " + "; ".join(problems)

        return result
   
    except Exception as exc:
        print(
            f"Помилка Gemini під час планування подорожі: {exc}"
        )

        return (
            "Не вдалося сформувати план подорожі через Gemini. "
            "Спробуйте ще раз трохи пізніше."
        )



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
