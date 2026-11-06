import os
import urllib.parse as urlparse
import psycopg2

DB_URL = os.getenv("DATABASE_URL")

def get_db_connection():
    """Створює безпечне підключення до бази даних PostgreSQL через URL."""
    if not DB_URL:
        # Резервне підключення для локального тестування, якщо немає змінної оточення
        raise ValueError("❌ Помилка: Змінна оточення DATABASE_URL не знайдена на Render!")
    
    # Розбираємо URL для сумісності з psycopg2
    url = urlparse.urlparse(DB_URL)
    dbname = url.path[1:]
    user = url.username
    password = url.password
    host = url.hostname
    port = url.port

    return psycopg2.connect(
        dbname=dbname,
        user=user,
        password=password,
        host=host,
        port=port
    )

def init_db():
    """Створює в PostgreSQL всі необхідні таблиці."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Таблиця для одягу користувачів
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
    
    # 2. Таблиця для збереження міст
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id BIGINT PRIMARY KEY,
            city TEXT NOT NULL
        )
    ''')
    
    # 3. Таблиця товарів для рекомендацій з Rozetka
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
    
    # Наповнюємо базу дефолтними товарами
    _populate_default_shopping_items()

def _populate_default_shopping_items():
    """Наповнює таблицю базовими товарами Rozetka, якщо вона порожня."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM shopping_items')
    if cursor.fetchone()[0] == 0:
        items = [
            ("Джинси жіночі Sinsay Сині", 199, "https://rozetka.com.ua", "Джинси", "Жіночий"),
            ("Джинси жіночі Diverse LUA Чорні", 299, "https://rozetka.com.ua", "Джинси", "Жіночий"),
            ("Штани карго чоловічі теплі Чорні", 899, "https://rozetka.com.ua", "Штани", "Чоловічий"),
            ("Худі базове Zara Бордове", 1499, "https://rozetka.com.ua", "Худі", "Жіночий"),
            ("Бавовняний светр Diverse Рудий", 699, "https://rozetka.com.ua", "Светр", "Унісекс"),
            ("Чоловічий флісовий худі сірий", 750, "https://rozetka.com.ua", "Худі", "Чоловічий"),
            ("Куртка-бомбер демісезонна Чорна", 1850, "https://rozetka.com.ua", "Куртка", "Унісекс"),
            ("Стьобане пальто жіноче Бежеве", 2400, "https://rozetka.com.ua", "Куртка", "Жіночий"),
            ("Білі шкіряні кросівки повсякденні", 1200, "https://rozetka.com.ua", "Взуття", "Унісекс"),
            ("Парасоля-автомат міцна Чорна", 450, "https://rozetka.com.ua", "Аксесуари", "Унісекс")
        ]
        cursor.executemany('''
            INSERT INTO shopping_items (name, price, url, category, gender)
            VALUES (%s, %s, %s, %s, %s)
        ''', items)
        conn.commit()
        
    cursor.close()
    conn.close()

def get_all_shopping_items():
    """Повертає всі доступні товари з бази даних."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT name, price, url, category, gender FROM shopping_items')
    items = cursor.fetchall()
    cursor.close()
    conn.close()
    return items

def add_clothing(user_id: int, file_id: str, description: str, category: str = "Інше"):
    """Додає нову річ до гардеробу користувача."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO clothes (user_id, file_id, description, category)
        VALUES (%s, %s, %s, %s)
    ''', (user_id, file_id, description, category))
    conn.commit()
    cursor.close()
    conn.close()

def get_user_wardrobe(user_id: int):
    """Повертає список речей у форматі кортежів (file_id, description, id, category)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    # ДОДАНО стовбець category у вибірку
    cursor.execute('SELECT file_id, description, id, category FROM clothes WHERE user_id = %s', (user_id,))
    items = cursor.fetchall()
    cursor.close()
    conn.close()
    return items


def delete_clothing(user_id: int, clothing_id: int) -> bool:
    """Видаляє річ з гардероба користувача за її ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM clothes WHERE user_id = %s AND id = %s', (user_id, clothing_id))
    conn.commit()
    changes = cursor.rowcount
    cursor.close()
    conn.close()
    return changes > 0

def update_clothing_description(user_id: int, clothing_id: int, new_description: str) -> bool:
    """Оновлює опис (назву) речей за її ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE clothes SET description = %s WHERE user_id = %s AND id = %s', (new_description, user_id, clothing_id))
    conn.commit()
    changes = cursor.rowcount
    cursor.close()
    conn.close()
    return changes > 0

def save_user_city(user_id: int, city: str):
    """Зберігає або оновлює місто користувача."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO user_settings (user_id, city) 
        VALUES (%s, %s)
        ON CONFLICT(user_id) DO UPDATE SET city = EXCLUDED.city
    ''', (user_id, city))
    conn.commit()
    cursor.close()
    conn.close()

def get_user_city(user_id: int) -> str:
    """Повертає місто користувача, або 'Lviv' за замовчуванням."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT city FROM user_settings WHERE user_id = %s', (user_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row[0] if row else "Lviv"


