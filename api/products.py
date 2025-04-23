from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/api/products', methods=['GET'])
def get_products():
    return jsonify({"products": ["item1", "item2"]})

if __name__ == "__main__":
    app.run()