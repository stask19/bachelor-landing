import sqlite3

def init_database():
    conn = sqlite3.connect('cars.db')
    cursor = conn.cursor()

    cursor.execute('DROP TABLE IF EXISTS cars')
    cursor.execute('DROP TABLE IF EXISTS users')
    cursor.execute('DROP TABLE IF EXISTS orders')

    cursor.execute('''
        CREATE TABLE cars (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model TEXT NOT NULL,
            price_score REAL NOT NULL,
            comfort_score REAL NOT NULL,
            clearance_score REAL NOT NULL,
            reason TEXT NOT NULL,
            image_url TEXT NOT NULL,
            is_available INTEGER DEFAULT 1
        )
    ''')

    cursor.execute('''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            car_id INTEGER,
            order_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (car_id) REFERENCES cars(id)
        )
    ''')

    cars_data = [
        ("Opel Insignia", 0.6, 0.7, 0.4, "Оптимальний баланс динаміки та економії для міста.", "/static/images/insignia.jpg", 1),
        ("Audi SQ5", 0.1, 0.9, 0.8, "Потужний та преміальний кросовер з високим кліренсом для будь-яких доріг.", "/static/images/sq5.jpg", 1),
        ("Volkswagen Passat B8", 0.4, 0.8, 0.5, "Ідеальний баланс між ціною, комфортом та практичністю.", "/static/images/passat.jpg", 1),
        ("Toyota Camry 70", 0.2, 0.9, 0.4, "Максимальний комфорт та представницький клас.", "/static/images/camry_v70.jpg", 1),
        ("Renault Megane", 0.8, 0.5, 0.3, "Максимальна економія пального та низька вартість оренди.", "/static/images/megane_rs.jpg", 1),
        ("BMW 3 Series", 0.1, 0.9, 0.3, "Динамічний седан для любителів активного драйву.", "/static/images/bmw3_g20.jpg", 1),
        ("Skoda Octavia", 0.9, 0.3, 0.6, "Надійна класика: доступна в оренді та з хорошим кліренсом.", "/static/images/octavia_rs.jpg", 1),
        ("Ford Focus RS", 0.7, 0.4, 0.4, "Відмінна керованість та економія коштів для повсякденних поїздок.", "/static/images/focus_rs.jpg", 1)
    ]

    cursor.executemany('''
        INSERT INTO cars (model, price_score, comfort_score, clearance_score, reason, image_url, is_available)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', cars_data)

    conn.commit()
    conn.close()
    print("✅ Базу даних успішно оновлено! Створено таблиці cars, users, orders.")

if __name__ == '__main__':
    init_database()