"""Робота з PostgreSQL для Telegram-бота «Шо одіти?».

Функції та формат результатів збережені сумісними з bot.py та ai_stylist.py.
Ініціалізація схеми не видаляє і не очищує користувацькі дані.
"""

import os
from contextlib import contextmanager
from typing import Iterator, Optional

import psycopg2


def get_db_connection():
    """Створює з'єднання з PostgreSQL через DATABASE_URL."""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError(
            "Змінна DATABASE_URL порожня. Налаштуйте підключення до PostgreSQL "
            "у змінних середовища Render або локального середовища."
        )

    # psycopg2/libpq самостійно розбирає postgres:// та postgresql:// URI,
    # включно з URL-кодуванням пароля і параметрами на кшталт sslmode=require.
    return psycopg2.connect(db_url)


@contextmanager
def _db_session() -> Iterator[object]:
    """Гарантує commit/rollback і закриття з'єднання."""
    conn = get_db_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Створює відсутні таблиці; наявні записи не змінює і не видаляє."""
    with _db_session() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS user_settings (
                    user_id BIGINT PRIMARY KEY,
                    city TEXT NOT NULL DEFAULT 'Lviv'
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS clothes (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    file_id TEXT NOT NULL,
                    description TEXT NOT NULL,
                    category TEXT DEFAULT 'верх',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )


def _detect_category(description: str) -> str:
    """Визначає категорію речі за її описом."""
    desc = (description or "").casefold()

    if any(
        word in desc
        for word in (
            "худі", "футболка", "кофта", "олімпійка", "зіпка",
            "лонгслів", "светр", "топ", "куртка", "пуховик",
            "бомбер", "толстовка", "піджак", "жакет", "кардиган",
            "сорочка", "блуза", "жилет",
        )
    ):
        return "верх"

    if any(
        word in desc
        for word in (
            "джинси", "штани", "брюки", "карго", "джоггери",
            "шорти", "спідниця", "легінси", "лосини",
        )
    ):
        return "низ"

    if any(
        word in desc
        for word in (
            "кросівки", "взуття", "кеди", "черевики", "чоботи",
            "туфлі", "босоніжки", "уггі", "сандалі",
        )
    ):
        return "взуття"

    if any(
        word in desc
        for word in (
            "ланцюжок", "кулон", "підвіска", "кільце", "перстень",
            "браслет", "намисто", "прикрас", "аксесуар", "сумка",
            "капелюх", "шапка", "шарф", "окуляри", "ремінь", "годинник",
        )
    ):
        return "аксесуари"

    # Зберігаємо попередню поведінку для сумісності: невизначена категорія —
    # «верх». На наступному етапі можна буде вдосконалити класифікацію.
    return "верх"


def add_clothing(user_id: int, file_id: str, description: str) -> None:
    """Додає річ до гардероба користувача."""
    if not file_id:
        raise ValueError("Не передано Telegram file_id фотографії.")
    description = (description or "").strip()
    if not description:
        raise ValueError("Опис речі не може бути порожнім.")

    category = _detect_category(description)
    with _db_session() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO clothes (user_id, file_id, description, category)
                VALUES (%s, %s, %s, %s)
                """,
                (int(user_id), file_id, description, category),
            )


def get_user_wardrobe(user_id: int, category: str = "все"):
    """Повертає речі у форматі (file_id, description, id, category)."""
    with _db_session() as conn:
        with conn.cursor() as cursor:
            if (category or "все").strip().casefold() == "все":
                cursor.execute(
                    """
                    SELECT file_id, description, id, category
                    FROM clothes
                    WHERE user_id = %s
                    ORDER BY id
                    """,
                    (int(user_id),),
                )
            else:
                cursor.execute(
                    """
                    SELECT file_id, description, id, category
                    FROM clothes
                    WHERE user_id = %s AND category = %s
                    ORDER BY id
                    """,
                    (int(user_id), category.strip().casefold()),
                )
            return cursor.fetchall()


def delete_clothing(item_id: int, user_id: int) -> bool:
    """Видаляє лише річ, яка належить зазначеному користувачу."""
    with _db_session() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "DELETE FROM clothes WHERE id = %s AND user_id = %s",
                (int(item_id), int(user_id)),
            )
            return cursor.rowcount > 0


def update_clothing_description(
    item_id: int, user_id: int, new_desc: str
) -> bool:
    """Оновлює опис і категорію речі; повертає True, якщо запис знайдено."""
    new_desc = (new_desc or "").strip()
    if not new_desc:
        raise ValueError("Новий опис речі не може бути порожнім.")

    new_category = _detect_category(new_desc)
    with _db_session() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE clothes
                SET description = %s, category = %s
                WHERE id = %s AND user_id = %s
                """,
                (new_desc, new_category, int(item_id), int(user_id)),
            )
            return cursor.rowcount > 0


def get_user_city(user_id: int) -> str:
    """Повертає місто користувача або Lviv, якщо налаштування ще немає."""
    with _db_session() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT city FROM user_settings WHERE user_id = %s",
                (int(user_id),),
            )
            row = cursor.fetchone()
            return row[0] if row and row[0] else "Lviv"


def save_user_city(user_id: int, city: str) -> None:
    """Зберігає або оновлює місто користувача."""
    city = (city or "").strip()
    if not city:
        raise ValueError("Назва міста не може бути порожньою.")

    with _db_session() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO user_settings (user_id, city)
                VALUES (%s, %s)
                ON CONFLICT (user_id)
                DO UPDATE SET city = EXCLUDED.city
                """,
                (int(user_id), city),
            )
