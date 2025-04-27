from flask import Flask, jsonify

app = Flask(__name__)

products = [
    {
        "item_id": "1",
        "name": "Архив с картинами",
        "price": 100,
        "file_id": "1bc7kIbT9a7sofbzBdDiuaKBOgBw8RMhR"  # Замени на file_id архива
    },
    {
        "item_id": "2",
        "name": "Картина 2",
        "price": 150,
        "file_id": "YOUR_FILE_ID_2"  # file_id для Картины 2
    }
]

@app.route('/api/products')
def get_products():
    return jsonify(products)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)