from flask import Flask, jsonify

app = Flask(__name__)

# Список продуктов с прямыми ссылками на файлы
products = [
    {
        "item_id": "1",
        "name": "Картина 1",
        "price": 100,
        "file_url": "https://drive.google.com/uc?export=download&id=1bc7kIbT9a7sofbzBdDiuaKBOgBw8RMhR"
    },
    {
        "item_id": "2",
        "name": "Картина 2",
        "price": 150,
        "file_url": "https://drive.google.com/uc?export=download&id=16fgRdfJokZvvLqTe8hJthAKu54I6tYtE"
    }
]

@app.route('/api/products')
def get_products():
    return jsonify(products)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)