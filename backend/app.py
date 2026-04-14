from flask import Flask, jsonify, request
from flask_cors import CORS

# Створення екземпляру додатка
app = Flask(__name__)

# Крос-доменні запити
CORS(app)

# API-маршрут (ендпоінт)
@app.route('/api/recommend', methods=['POST'])
def recommend_car():
    # Імітуємо роботу модуля AHP.
    result = {
        "model": "Toyota Camry 70",
        "score": 0.845,
        "reason": "За техніко-економічними показниками та методом AHP цей варіант є оптимальним."
    }
    return jsonify(result)

# Цей блок запускає сервер, якщо файл запущено безпосередньо
if __name__ == '__main__':
    print("Сервер запускається на http://127.0.0.1:5000")
    app.run(debug=True, port=5000)