import logging
import uuid
import sqlite3
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, request, jsonify, render_template, g, has_request_context
from flask_cors import CORS
import numpy as np
from functools import lru_cache
from werkzeug.middleware.profiler import ProfilerMiddleware

class RequestIdFilter(logging.Filter):
    def filter(self, record):
        if has_request_context():
            record.request_id = getattr(g, 'request_id', 'SYSTEM')
        else:
            record.request_id = 'SYSTEM'
        return True

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - [%(request_id)s] - %(levelname)s - [%(module)s] - %(message)s')

file_handler = logging.FileHandler("backend_system.log", encoding='utf-8')
file_handler.setFormatter(formatter)
file_handler.addFilter(RequestIdFilter())

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
stream_handler.addFilter(RequestIdFilter())

logger.addHandler(file_handler)
logger.addHandler(stream_handler)

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    return render_template('index.html')

app.wsgi_app = ProfilerMiddleware(app.wsgi_app, restrictions=[10])

@app.before_request
def assign_request_id():
    g.request_id = request.headers.get('X-Request-ID', str(uuid.uuid4()))
    if request.path != '/api/frontend-logs': # Не логуємо самі логи
        logger.info(f"Отримано запит: {request.method} {request.path}")

@app.after_request
def log_response_info(response):
    if request.path != '/api/frontend-logs':
        logger.info(f"Відповідь сервера: статус {response.status_code}")
    response.headers['X-Request-ID'] = g.request_id
    return response

@app.errorhandler(404)
def resource_not_found(e):
    logger.warning(f"Спроба доступу до неіснуючого ресурсу: {request.url}")
    return jsonify({"error": "Ресурс не знайдено", "code": 404}), 404

def get_cars_from_db():
    """Дістає всі доступні автомобілі з бази SQLite"""
    try:
        conn = sqlite3.connect('backend/cars.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, model, price_score, comfort_score, clearance_score, reason, image_url FROM cars WHERE is_available = 1")
        rows = cursor.fetchall()
        
        cars = []
        for row in rows:
            cars.append({
                "id": row[0],
                "model": row[1],
                "scores": np.array([row[2], row[3], row[4]]),
                "reason": row[5],
                "image_url": row[6]
            })
        conn.close()
        return cars
    except sqlite3.OperationalError:
        conn = sqlite3.connect('cars.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, model, price_score, comfort_score, clearance_score, reason, image_url FROM cars WHERE is_available = 1")
        rows = cursor.fetchall()
        
        cars = []
        for row in rows:
            cars.append({
                "id": row[0],
                "model": row[1],
                "scores": np.array([row[2], row[3], row[4]]),
                "reason": row[5],
                "image_url": row[6]
            })
        conn.close()
        return cars
    except Exception as e:
        logger.error(f"Помилка підключення до БД: {str(e)}")
        return []

@lru_cache(maxsize=128)
def calculate_ahp_cached(p_vs_c, p_vs_cl, c_vs_cl):
    criteria_matrix = np.array([
        [1,         p_vs_c,       p_vs_cl],
        [1/p_vs_c,  1,            c_vs_cl],
        [1/p_vs_cl, 1/c_vs_cl,    1      ]
    ])

    col_sums = criteria_matrix.sum(axis=0)
    norm_matrix = criteria_matrix / col_sums
    weights = norm_matrix.mean(axis=1) 

    cars = get_cars_from_db()

    best_car, best_score, best_reason = None, 0, ""

    for car in cars:
        final_score = np.sum(car["scores"] * weights)
        if final_score > best_score:
            best_score, best_car, best_reason = final_score, car["model"], car["reason"]

    return weights, best_car, best_score, best_reason

@app.route('/api/recommend', methods=['POST'])
def recommend_car():
    try:
        data = request.json
        logger.debug(f"Отримано вхідні дані: {data}")

        weights, best_car, best_score, best_reason = calculate_ahp_cached(
            float(data['price_vs_comfort']),
            float(data['price_vs_clearance']),
            float(data['comfort_vs_clearance'])
        )

        logger.info(f"Система підібрала авто: {best_car} (Оцінка: {best_score:.2f})")

        conn = sqlite3.connect('cars.db')
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM cars WHERE model = ?', (best_car,))
        db_row = cursor.fetchone()
        car_id = db_row[0] if db_row else 0
        conn.close()

        result = {
            "id": car_id,
            "model": best_car,
            "score": round(best_score * 100, 1),
            "reason": best_reason
        }
        return jsonify(result)

    except Exception as e:
        logger.critical(f"Критична помилка в модулі AHP: {str(e)}", exc_info=True)
        return jsonify({"error": "Внутрішня помилка сервера при розрахунку"}), 500

@app.route('/api/frontend-logs', methods=['POST'])
def receive_frontend_logs():
    log_data = request.json
    logger.error(f"FRONTEND ERROR: {log_data.get('message')} | Файл: {log_data.get('url')} | Рядок: {log_data.get('line')}")
    return jsonify({"status": "Log received"}), 200

def send_email_notification(user_email, user_name, car_model):
    sender_email = "staskulizhka@gmail.com" 
    sender_password = "yhcgoggyantakksr" 
    
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = user_email
    msg['Subject'] = f"Підтвердження бронювання авто - {car_model}"

    body = f"Вітаємо, {user_name}!\n\nВи успішно забронювали автомобіль {car_model}.\nСтатус вашого замовлення: Підтверджено.\nНаш менеджер зв'яжеться з вами найближчим часом для уточнення деталей передачі ключів.\n\nДякуємо, що обрали наш сервіс!"
    msg.attach(MIMEText(body, 'plain', 'utf-8'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, user_email, msg.as_string())
        server.quit()
        print(f"✅ Лист успішно надіслано на {user_email}")
        return True
    except Exception as e:
        print(f"❌ Помилка відправки листа: {e}")
        return False

@app.route('/api/book', methods=['POST'])
def book_car():
    data = request.json
    car_id = data.get('car_id')
    full_name = data.get('full_name')
    email = data.get('email')
    phone = data.get('phone')

    if not all([car_id, full_name, email, phone]):
        return jsonify({"status": "error", "message": "Всі поля обов'язкові"}), 400

    conn = sqlite3.connect('cars.db')
    cursor = conn.cursor()

    try:
        cursor.execute('SELECT model, is_available FROM cars WHERE id = ?', (car_id,))
        car = cursor.fetchone()
        
        if not car:
            return jsonify({"status": "error", "message": "Авто не знайдено"}), 404
        if car[1] == 0:
            return jsonify({"status": "error", "message": "Це авто вже заброньовано"}), 400

        car_model = car[0]

        cursor.execute('INSERT INTO users (full_name, email, phone) VALUES (?, ?, ?)', (full_name, email, phone))
        user_id = cursor.lastrowid

        cursor.execute('INSERT INTO orders (user_id, car_id) VALUES (?, ?)', (user_id, car_id))

        cursor.execute('UPDATE cars SET is_available = 0 WHERE id = ?', (car_id,))

        conn.commit()

        send_email_notification(email, full_name, car_model)

        return jsonify({"status": "success", "message": "Бронювання успішне!"})

    except Exception as e:
        conn.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        conn.close()

if __name__ == '__main__':
    app.run(debug=True, threaded=True, port=5000)