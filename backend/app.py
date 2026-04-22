import logging
import uuid
from flask import Flask, jsonify, request, g, has_request_context 
from flask_cors import CORS
import numpy as np
from werkzeug.middleware.profiler import ProfilerMiddleware
from functools import lru_cache

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
app.wsgi_app = ProfilerMiddleware(app.wsgi_app, restrictions=[10])


@app.before_request
def assign_request_id():
    
    g.request_id = request.headers.get('X-Request-ID', str(uuid.uuid4()))
    logger.info(f"Отримано запит: {request.method} {request.path}")

@app.after_request
def log_response_info(response):
    logger.info(f"Відповідь сервера: статус {response.status_code}")

    response.headers['X-Request-ID'] = g.request_id
    return response


@app.errorhandler(404)
def resource_not_found(e):
    logger.warning(f"Спроба доступу до неіснуючого ресурсу: {request.url}")
    return jsonify({"error": "Ресурс не знайдено", "code": 404}), 404


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
    
    cars = [
        {"model": "Opel Insignia 2.0 CDTi", "scores": np.array([0.6, 0.2, 0.3]), "reason": "Це найвигідніший варіант для вашого бюджету."},
        {"model": "Volkswagen Passat B8", "scores": np.array([0.3, 0.4, 0.4]), "reason": "Це ідеальний баланс між ціною, комфортом та практичністю."},
        {"model": "Toyota Camry 70", "scores": np.array([0.1, 0.4, 0.3]), "reason": "Ви обрали комфорт як пріоритет, і це авто забезпечить його найкраще."}
    ]

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

        result = {
            "model": best_car,
            "score": round(best_score * 100, 1),
            "reason": best_reason
        }
        return jsonify(result)

    except Exception as e:
        logger.critical(f"Критична помилка в модулі AHP: {str(e)}", exc_info=True)
        return jsonify({"error": "Внутрішня помилка сервера при розрахунку"}), 500

if __name__ == '__main__':
    logger.info("=== ЗАПУСК СИСТЕМИ: Сервер Car Rental DSS ініціалізовано ===")
    app.run(debug=True, port=5000)