import sqlite3

DB_NAME = "wardrobe.db"

def init_db():
    """Створює базу даних та всі таблиці (ОНОВЛЕНО)."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # 1. Таблиця для одягу
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clothes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            file_id TEXT NOT NULL,
            description TEXT NOT NULL,
            category TEXT DEFAULT 'Інше',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 2. Таблиця для збереження міст
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id INTEGER PRIMARY KEY,
            city TEXT NOT NULL
        )
    ''')
    
    # 3. НОВА ТАБЛИЦЯ: База товарів для рекомендацій з Rozetka
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS shopping_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price INTEGER NOT NULL,
            url TEXT NOT NULL,
            category TEXT NOT NULL, -- Наприклад: 'Джинси', 'Худі', 'Светр', 'Куртка', 'Взуття'
            gender TEXT DEFAULT 'Унісекс' -- 'Жіночий', 'Чоловічий', 'Унісекс'
        )
    ''')
    
    conn.commit()
    conn.close()
    
    # Автоматично наповнимо базу тестовими товарами, якщо вона порожня
    _populate_default_shopping_items()

def _populate_default_shopping_items():
    """Наповнює таблицю базовими товарами, якщо вона порожня."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM shopping_items')
    if cursor.fetchone()[0] == 0:
        # Широкий асортимент товарів для динамічного вибору
        items = [
            # Джинси та штани
            ("Джинси жіночі Sinsay Сині", 199, "https://rozetka.com.ua", "Джинси", "Жіночий"),
            ("Джинси жіночі Diverse LUA Чорні", 299, "https://rozetka.com.ua", "Джинси", "Жіночий"),
            ("Штани карго чоловічі теплі Чорні", 899, "https://rozetka.com.ua", "Штани", "Чоловічий"),
            # Худі та светри
            ("Худі базове Zara Бордове", 1499, "https://rozetka.com.ua", "Худі", "Жіночий"),
            ("Бавовняний светр Diverse Рудий", 699, "https://rozetka.com.ua", "Светр", "Унісекс"),
            ("Чоловічий флісовий худі сірий", 750, "https://rozetka.com.ua", "Худі", "Чоловічий"),
            # Верхній одяг
            ("Куртка-бомбер демісезонна Чорна", 1850, "https://rozetka.com.ua", "Куртка", "Унісекс"),
            ("Стьобане пальто жіноче Бежеве", 2400, "https://rozetka.com.ua", "Куртка", "Жіночий"),
            # Взуття та аксесуари
            ("Білі шкіряні кросівки повсякденні", 1200, "https://rozetka.com.ua", "Взуття", "Унісекс"),
            ("Парасоля-автомат міцна Чорна", 450, "https://rozetka.com.ua", "Аксесуари", "Унісекс")
        ]
        cursor.executemany('''
            INSERT INTO shopping_items (name, price, url, category, gender)
            VALUES (?, ?, ?, ?, ?)
        ''', items)
        conn.commit()
    conn.close()

def get_all_shopping_items():
    """Повертає всі доступні товари з бази даних."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT name, price, url, category, gender FROM shopping_items')
    items = cursor.fetchall()
    conn.close()
    return items



def add_clothing(user_id: int, file_id: str, description: str, category: str = "Інше"):
    """Додає нову річ до гардеробу користувача."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO clothes (user_id, file_id, description, category)
        VALUES (?, ?, ?, ?)
    ''', (user_id, file_id, description, category))
    conn.commit()
    conn.close()

def get_user_wardrobe(user_id: int):
    """Повертає список речей у форматі кортежів (file_id, description, id)."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT file_id, description, id FROM clothes WHERE user_id = ?', (user_id,))
    items = cursor.fetchall()
    conn.close()
    return items

def delete_clothing(user_id: int, clothing_id: int) -> bool:
    """Видаляє річ з гардероба користувача за її ID."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM clothes WHERE user_id = ? AND id = ?', (user_id, clothing_id))
    conn.commit()
    changes = conn.total_changes
    conn.close()
    return changes > 0

def update_clothing_description(user_id: int, clothing_id: int, new_description: str) -> bool:
    """Оновлює опис (назву) речей за її ID."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('UPDATE clothes SET description = ? WHERE user_id = ? AND id = ?', (new_description, user_id, clothing_id))
    conn.commit()
    changes = conn.total_changes
    conn.close()
    return changes > 0

def save_user_city(user_id: int, city: str):
    """Зберігає або оновлює місто користувача."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO user_settings (user_id, city) 
        VALUES (?, ?)
        ON CONFLICT(user_id) DO UPDATE SET city = excluded.city
    ''', (user_id, city))
    conn.commit()
    conn.close()

def get_user_city(user_id: int) -> str:
    """Повертає місто користувача, або 'Lviv' за замовчуванням."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT city FROM user_settings WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else "Lviv"

if __name__ == "__main__":
    init_db()
