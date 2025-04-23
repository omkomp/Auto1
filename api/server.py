from flask import Flask, jsonify
import json

app = Flask(__name__)

@app.route('/api/products')
def get_products():
    try:
        with open('static/products.json', 'r', encoding='utf-8') as f:
            products = json.load(f)
        return jsonify(products)
    except FileNotFoundError:
        return jsonify([]), 404