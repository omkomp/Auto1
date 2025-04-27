from flask import Flask, jsonify

app = Flask(__name__)

products = [
    {
        "item_id": "1",
        "name": "Архив с картинами",
        "price": 100,
        "file_id": "BQACAgIAAxkBAAIC22gOg-_yK1vy2Tyl6fg_ub5G777NAAIpewACat1wSMHSihw2gGzBNgQ"  # Замени на file_id архива
    },
    {
        "item_id": "2",
        "name": "Картина 2",
        "price": 150,
        "file_id": "YOUR_FILE_ID_2"  # Замени на file_id Картины 2
    }
]

@app.route('/api/products')
def get_products():
    return jsonify(products)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)