from flask import Flask, jsonify

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False  # Отключаем экранирование не-ASCII символов

@app.route('/api/products', methods=['GET'])
def get_products():
    products = [
        {"item_id": "1", "name": "Картина 1", "price": 100},
        {"item_id": "2", "name": "Картина 2", "price": 150}
    ]
    return jsonify(products)