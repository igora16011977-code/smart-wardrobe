import os
import urllib.parse as urlparse
import psycopg2

DB_URL = os.getenv("DATABASE_URL")

def get_db_connection():
    if not DB_URL:
        raise ValueError("❌ Критична помилка: Змінна DATABASE_URL порожня на Render!")
    
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
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id BIGINT PRIMARY KEY,
            city TEXT NOT NULL DEFAULT 'Lviv'
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clothes (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            file_id TEXT NOT NULL,
            description TEXT NOT NULL,
            category TEXT DEFAULT 'Інше',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS shopping_items (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            price INTEGER NOT NULL,
            url TEXT NOT NULL,
            category TEXT NOT NULL,
            gender TEXT DEFAULT 'Унісекс'
        )
    ''')
    conn.commit()
    cursor.close()
    conn.close()

def _detect_category(description: str) -> str:
    desc = description.lower()
    if any(w in desc for w in ["худі", "футболка", "кофта", "олімпійка", "зіпка", "лонгслів", "светр", "топ"]): return "верх"
    if any(w in desc for w in ["джинси", "штани", "брюки", "карго", "джоггери", "шорти", "спідниця"]): return "низ"
    if any(w in desc for w in ["кросівки", "взуття", "кеди", "черевики"]): return "взуття"
    if any(w in desc for w in ["ланцюжок", "кулон", "підвіска", "кільце", "перстень", "браслет", "намисто", "прикрас"]): return "аксесуари"
    return "Інше"

def add_clothing(user_id: int, file_id: str, description: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    category = _detect_category(description)
    cursor.execute('''
        INSERT INTO clothes (user_id, file_id, description, category)
        VALUES (%s, %s, %s, %s)
    ''', (user_id, file_id, description, category))
    conn.commit()
    cursor.close()
    conn.close()

def get_user_wardrobe(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT file_id, description, id, category FROM clothes WHERE user_id = %s', (user_id,))
    items = cursor.fetchall()
    cursor.close()
    conn.close()
    return items

def get_user_city(user_id: int) -> str:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT city FROM user_settings WHERE user_id = %s', (user_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row[0] if row else "Lviv"

def save_user_city(user_id: int, city: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO user_settings (user_id, city) VALUES (%s, %s)
        ON CONFLICT(user_id) DO UPDATE SET city = EXCLUDED.city
    ''', (user_id, city))
    conn.commit()
    cursor.close()
    conn.close()

