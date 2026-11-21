"""AI-функції бота «Шо одіти?» на базі Google Gemini.

Усі текстові функції та аналіз фотографій використовують Gemini.
Збережено публічні назви функцій і сигнатури, які викликає bot.py.
"""
import json
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


def analyze_clothing_image_structured(image_bytes: bytes) -> dict[str, str]:
    """Аналізує фото одягу та повертає структуровані характеристики українською."""
    if not isinstance(image_bytes, (bytes, bytearray)) or not image_bytes:
        raise ValueError("Не отримано дані фотографії.")

    mime_type = _detect_image_mime(bytes(image_bytes))
    client = _get_gemini_client()

    try:
        from google.genai import types

        prompt = (
            "Ти — уважний асистент для каталогізації одягу. Проаналізуй прикріплену "
            "фотографію та поверни результат СТРОГО як JSON-об'єкт українською мовою "
            "з такими ключами: title, description, category, color, material, style.\n"
            "Вимоги до полів:\n"
            "- title: коротка конкретна назва речі (наприклад, «Світло-сірі широкі джинси»).\n"
            "- description: одне-два речення з фактичним описом видимих особливостей.\n"
            "- category: лише одне значення з переліку: «верх», «низ», «взуття», «аксесуари».\n"
            "- color: основний видимий колір і відтінок.\n"
            "- material: видимий матеріал або фактура; не визначай склад тканини лише за виглядом.\n"
            "- style: фасон або крій, який можна встановити за фото.\n"
            "Не вигадуй бренд, склад тканини, сезон, призначення чи деталі, яких не видно. "
            "Якщо характеристику неможливо достовірно визначити, поверни для неї порожній рядок. "
            "Не додавай Markdown, пояснень або тексту поза JSON."
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
                    config=types.GenerateContentConfig(
                        temperature=0.2,
                        max_output_tokens=400,
                        response_mime_type="application/json",
                    ),
                )
                raw_result = (getattr(response, "text", None) or "").strip()
                if not raw_result:
                    raise RuntimeError("Gemini не повернув характеристик фотографії.")

                # Деякі моделі можуть обгорнути JSON у Markdown-код-блок.
                raw_result = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_result, flags=re.IGNORECASE)
                data = json.loads(raw_result)
                if not isinstance(data, dict):
                    raise ValueError("Gemini повернув результат не у форматі JSON-об'єкта.")

                fields = ("title", "description", "category", "color", "material", "style")
                result = {
                    field: str(data.get(field) or "").strip()
                    for field in fields
                }
                allowed_categories = {"верх", "низ", "взуття", "аксесуари"}
                category = result["category"].casefold()
                if category not in allowed_categories:
                    result["category"] = ""
                else:
                    result["category"] = category

                if not result["title"]:
                    result["title"] = result["description"][:80].strip()
                if not result["description"]:
                    result["description"] = result["title"]
                if not result["title"] and not result["description"]:
                    raise ValueError("Gemini не визначив тип речі.")
                return result
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


def analyze_clothing_image(image_bytes: bytes) -> str:
    """Сумісна зі старим bot.py функція: повертає лише опис речі."""
    result = analyze_clothing_image_structured(image_bytes)
    return result["description"]


def _wardrobe_lines(wardrobe_items: Iterable[Any]) -> list[str]:
    """Перетворює записи БД на перелік речей без службових ID."""
    lines = []
    for item in wardrobe_items or []:
        if isinstance(item, (tuple, list)) and len(item) >= 4:
            _file_id, description, _item_id, category = item[:4]
            lines.append(f"категорія: {category} | опис: {description}")
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
    """Формує 4 обґрунтовані рекомендації покупок на основі всього гардероба."""
    wardrobe_lines = _wardrobe_lines(wardrobe_items)
    items_text = "\n".join(f"- {line}" for line in wardrobe_lines)

    if not items_text:
        items_text = "Гардероб поки порожній."

    prompt = (
        "Ти — уважний персональний стиліст. Проведи комплексний аналіз УСЬОГО "
        "наведеного гардероба та визнач найважливіші прогалини. "
        "Перевір окремо всі наявні категорії та їх наповненість: верхній одяг; "
        "светри, кофти й кардигани; футболки, сорочки та інший одяг для верху; "
        "штани, джинси й інший одяг для низу; спідниці та сукні; взуття; "
        "а також інші категорії, якщо вони є у списку. "
        "Не обмежуйся пошуком повністю відсутніх категорій: враховуй також, "
        "чи достатньо речей певного типу, чи відповідають вони різним сезонам "
        "і чи дають змогу складати різноманітні комплекти. "
        "Особливо перевір, чи є взуття для відповідного сезону, але не "
        "пропонуй взуття автоматично, якщо наявне взуття вже покриває потреби. "
        "Так само не пропонуй автоматично речі з інших категорій без підстав. "
        "На основі цього аналізу запропонуй РІВНО 4 різні й конкретні покупки, "
        "які дадуть найбільшу користь саме цьому гардеробу. "
        "Кожна рекомендація має бути окремим пунктом із нумерацією 1., 2., 3., 4. "
        "Для кожної покупки коротко поясни: чому її варто придбати та з якими "
        "конкретними наявними речами або категоріями її можна поєднувати. "
        "Не рекомендуй речі, які вже є в гардеробі в достатній кількості. "
        "Не вигадуй, що користувач має речі, яких немає у списку. "
        "Якщо певна категорія відсутня або недостатньо представлена, "
        "використовуй це як підставу для рекомендації. Якщо категорія вже "
        "добре представлена, обери інші реальні прогалини. "
        "Не вигадуй бренди, магазини, ціни чи характеристики наявних речей. "
        "Не додавай вступу, висновку або додаткових пунктів поза чотирма "
        "рекомендаціями. Відповідай українською простим текстом.\n\n"
        f"ГАРДЕРОБ КОРИСТУВАЧА:\n{items_text}"
    )

    try:
        result = _ask_gemini(prompt, max_tokens=1200).strip()
        numbered_items = re.findall(r"(?m)^\s*[1-4][.)]\s+.+$", result)

        if len(numbered_items) != 4:
            correction_prompt = (
                "Перероби свою попередню відповідь. Потрібно надати РІВНО "
                "4 різні рекомендації покупок, не менше й не більше. "
                "Оформи їх окремими рядками з нумерацією 1., 2., 3., 4. "
                "Кожна рекомендація повинна бути конкретною, обґрунтованою "
                "аналізом гардероба та пояснювати, з чим поєднувати покупку. "
                "Не додавай вступу, висновку чи інших пунктів. "
                "Відповідай українською.\n\n"
                f"ПОПЕРЕДНЯ ВІДПОВІДЬ:\n{result}\n\n"
                f"ДАНІ ГАРДЕРОБА:\n{items_text}"
            )
            result = _ask_gemini(correction_prompt, max_tokens=1200).strip()
            numbered_items = re.findall(r"(?m)^\s*[1-4][.)]\s+.+$", result)

        if len(numbered_items) != 4:
            print(
                "Gemini не повернув рівно 4 рекомендації покупок "
                "навіть після повторного запиту."
            )
            return (
                "Не вдалося сформувати повний список із 4 рекомендацій. "
                "Спробуйте ще раз пізніше."
            )

        return result

    except Exception as exc:
        print(f"Помилка Gemini під час рекомендацій покупок: {exc}")
        return (
            "Не вдалося проаналізувати гардероб через Gemini. "
            "Спробуйте ще раз пізніше."
        )



def generate_wardrobe_outfits(wardrobe_items, outfit_count: int = 3, weather_info: dict | None = None) -> dict:
    """Підбирає кілька комплектів лише з речей, переданих із гардероба.

    Очікує список словників із полями id/title/description/category/color/material/style.
    Повертає структурований результат; ID додатково перевіряє сервер.
    """
    items = []
    for item in wardrobe_items or []:
        try:
            item_id = int(item.get("id"))
        except (AttributeError, TypeError, ValueError):
            continue
        items.append({
            "id": item_id,
            "title": str(item.get("title") or "").strip(),
            "description": str(item.get("description") or "").strip(),
            "category": str(item.get("category") or "").strip(),
            "color": str(item.get("color") or "").strip(),
            "material": str(item.get("material") or "").strip(),
            "style": str(item.get("style") or "").strip(),
        })

    if len(items) < 2:
        raise ValueError("Для підбору образу потрібно щонайменше дві речі в гардеробі.")

    outfit_count = max(1, min(int(outfit_count), 3))
    weather_info = weather_info or {}
    temp = weather_info.get("temp", weather_info.get("temperature"))
    feels_like = weather_info.get("feels_like", weather_info.get("feels_like_temperature", temp))
    condition = weather_info.get("description", weather_info.get("condition", "умови невідомі"))
    wind = weather_info.get("wind", weather_info.get("wind_speed", "невідомо"))
    humidity = weather_info.get("humidity", "невідомо")
    rain = weather_info.get("rain", weather_info.get("precipitation", "невідомо"))
    weather_text = (
        f"Температура: {temp if temp is not None else 'невідомо'} °C; "
        f"відчувається як: {feels_like if feels_like is not None else 'невідомо'} °C; "
        f"умови: {condition}; вітер: {wind}; вологість: {humidity}; опади: {rain}."
    )
    prompt = (
        "Ти професійний персональний стиліст. Склади " + str(outfit_count) +
        " різні, практичні комплекти ВИКЛЮЧНО з наведених нижче речей користувача.\n"
        "ОБОВ'ЯЗКОВО спочатку врахуй погоду: " + weather_text + "\n"
        "Безпека комфорту важливіша за естетику. Якщо холодно, не пропонуй відкриті ноги, легкий верх або літнє взуття "
        "без наявного теплого шару/верхнього одягу. За дощу або сильного вітру враховуй захист від опадів і вітру.\n"
        "Не вигадуй речі й не додавай нічого, чого немає в переліку. Якщо для погоди бракує потрібного одягу, "
        "не маскуй це літнім комплектом: обери найбільш теплий можливий варіант із наявного гардероба.\n"
        "У кожному образі прагни до повного комплекту: верх + низ + взуття; додавай верхній одяг/теплий шар, "
        "коли цього вимагає погода. Аксесуари (сумки, ремені, прикраси, окуляри, шарфи, шапки тощо) "
        "обов'язково розглядай як важливу частину стилізації та додавай доречні наявні аксесуари, "
        "але не вигадуй їх і не додавай випадкові. Якщо аксесуарів у шафі немає — не вигадуй.\n"
        "Не повторюй той самий набір речей у різних образах, якщо є альтернативи.\n"
        "Поверни ЛИШЕ JSON без Markdown. Поле reason залиш коротким (до 12 слів), без описів кожної речі. Формат:\n"
        '{"outfits":[{"title":"Коротка назва","reason":"Коротка характеристика образу",'
        '"item_ids":[1,2,3,4]}]}\n'
        "Кожен item_ids містить лише числові ID зі списку. Не повторюй ID в одному образі.\n\n"
        "ГАРДЕРОБ КОРИСТУВАЧА:\n" + json.dumps(items, ensure_ascii=False)
    )

    raw = _ask_gemini(prompt, max_tokens=1200)
    # Витягуємо JSON навіть якщо модель випадково додала кодову огорожу.
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE)
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start < 0 or end <= start:
        raise RuntimeError("Gemini повернув відповідь у невідомому форматі.")
    try:
        result = json.loads(cleaned[start:end + 1])
    except json.JSONDecodeError as exc:
        raise RuntimeError("Gemini повернув некоректний JSON.") from exc

    allowed_ids = {item["id"] for item in items}
    outfits = []
    for outfit in result.get("outfits", []) if isinstance(result, dict) else []:
        if not isinstance(outfit, dict):
            continue
        ids = []
        for value in outfit.get("item_ids", []):
            try:
                item_id = int(value)
            except (TypeError, ValueError):
                continue
            if item_id in allowed_ids and item_id not in ids:
                ids.append(item_id)
        if len(ids) < 2:
            continue
        outfits.append({
            "title": str(outfit.get("title") or "Образ").strip()[:80],
            "reason": str(outfit.get("reason") or "Гармонійне поєднання речей із твоєї шафи.").strip()[:500],
            "item_ids": ids,
        })
        if len(outfits) >= outfit_count:
            break

    if not outfits:
        raise RuntimeError("Не вдалося сформувати образи з наявних речей. Спробуй ще раз.")
    return {"outfits": outfits}
