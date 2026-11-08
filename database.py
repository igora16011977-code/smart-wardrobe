import os
import urllib.parse as urlparse
import psycopg2

DB_URL = os.getenv("DATABASE_URL")

def get_db_connection():
    if not DB_URL:
        raise ValueError("💖 Ой! Змінна DATABASE_URL порожня. Налаштуй базу даних на Render чи локально!")
    url = urlparse.urlparse(DB_URL)
    return psycopg2.connect(
        dbname=url.path[1:],
        user=url.username,
        password=url.password,
        host=url.hostname,
        port=url.port
    )

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    # ХИТРІСТЬ: Перейменували таблиці на user_settings_v2 та clothes_v2, 
    # щоб вони створилися з нуля без очищення бази на Render!
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_settings_v2 (
            user_id BIGINT PRIMARY KEY,
            city TEXT NOT NULL DEFAULT 'Lviv'
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clothes_v2 (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            file_id TEXT NOT NULL,
            description TEXT NOT NULL,
            category TEXT DEFAULT 'верх',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    cursor.close()
    conn.close()

def _detect_category(description: str) -> str:
    desc = description.lower()
    if any(w in desc for w in ["худі", "футболка", "кофта", "олімпійка", "зіпка", "лонгслів", "светр", "топ", "куртка", "пуховик", "бомбер", "толстовка", "піджак", "жакет", "кардиган"]): 
        return "верх"
    if any(w in desc for w in ["джинси", "штани", "брюки", "карго", "джоггери", "шорти", "спідниця", "легінси", "лосини"]): 
        return "низ"
    if any(w in desc for w in ["кросівки", "взуття", "кеди", "черевики", "чоботи", "туфлі", "босоніжки", "уггі"]): 
        return "взуття"
    if any(w in desc for w in ["ланцюжок", "кулон", "підвіска", "кільце", "перстень", "браслет", "намисто", "прикрас", "аксесуар", "сумка", "капелюх", "шапка", "шарф", "окуляри"]): 
        return "аксесуари"
    return "верх"

def add_clothing(user_id: int, file_id: str, description: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    category = _detect_category(description)
    cursor.execute('''
        INSERT INTO clothes_v2 (user_id, file_id, description, category)
        VALUES (%s, %s, %s, %s)
    ''', (user_id, file_id, description, category))
    conn.commit()
    cursor.close()
    conn.close()

def get_user_wardrobe(user_id: int, category: str = "все"):
    conn = get_db_connection()
    cursor = conn.cursor()
    if category == "все":
        cursor.execute('SELECT file_id, description, id, category FROM clothes_v2 WHERE user_id = %s ORDER BY id', (user_id,))
    else:
        cursor.execute('SELECT file_id, description, id, category FROM clothes_v2 WHERE user_id = %s AND category = %s ORDER BY id', (user_id, category.lower()))
    items = cursor.fetchall()
    cursor.close()
    conn.close()
    return items

def delete_clothing(item_id: int, user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM clothes_v2 WHERE id = %s AND user_id = %s', (item_id, user_id))
    conn.commit()
    cursor.close()
    conn.close()

def update_clothing_description(item_id: int, user_id: int, new_desc: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    new_category = _detect_category(new_desc)
    cursor.execute('UPDATE clothes_v2 SET description = %s, category = %s WHERE id = %s AND user_id = %s', (new_desc, new_category, item_id, user_id))
    conn.commit()
    cursor.close()
    conn.close()

def get_user_city(user_id: int) -> str:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT city FROM user_settings_v2 WHERE user_id = %s', (user_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row[0] if row else "Lviv"

def save_user_city(user_id: int, city: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO user_settings_v2 (user_id, city) VALUES (%s, %s)
        ON CONFLICT(user_id) DO UPDATE SET city = EXCLUDED.city
    ''', (user_id, city))
    conn.commit()
    cursor.close()
    conn.close()
