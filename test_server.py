from flask import Flask, send_from_directory, jsonify, make_response
import json

app = Flask(__name__)

@app.route('/')
def index():
    response = make_response(send_from_directory('static', 'index.html'))
    response.headers['Content-Type'] = 'text/html; charset=utf-8'
    return response

@app.route('/api/products')
def get_products():
    try:
        with open('static/products.json', 'r', encoding='utf-8') as f:
            products = json.load(f)
        return jsonify(products)
    except FileNotFoundError:
        return jsonify([]), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)