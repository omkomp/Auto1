import requests
from flask import Flask, request
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest
import qrcode
from io import BytesIO
from PIL import Image
import time
import base58
import os

app = Flask(__name__)
BOT_TOKEN = "7981458266:AAGp5jIgvf_KHN_P_7pBURBnYqrT-X89mNQ"
bot = Bot(token=BOT_TOKEN)
TRON_WALLET_ADDRESS = os.getenv("TRON_WALLET_ADDRESS")
TRONGRID_API_KEY = os.getenv("TRONGRID_API_KEY")
USDT_CONTRACT_ADDRESS = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"

if not TRON_WALLET_ADDRESS or not TRONGRID_API_KEY:
    raise ValueError("TRON_WALLET_ADDRESS или TRONGRID_API_KEY не заданы в переменных окружения!")

pending_orders = {}

def get_usdt_price_in_rub():
    try:
        response = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=tether&vs_currencies=rub")
        data = response.json()
        return data["tether"]["rub"]
    except Exception as e:
        print(f"Ошибка при получении курса USDT: {str(e)}")
        return None

def generate_qr_code(payment_url):
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(payment_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer

def tron_address_to_hex(address):
    decoded = base58.b58decode(address)
    hex_address = "41" + decoded[1:-4].hex()
    return hex_address

def start(update):
    chat_id = update.message.chat_id
    # Если есть активный заказ, удаляем его при новом /start
    if chat_id in pending_orders:
        del pending_orders[chat_id]
    keyboard = [[InlineKeyboardButton("Купить картину", callback_data='buy_painting')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    bot.send_message(chat_id=chat_id, text='Добро пожаловать в магазин!', reply_markup=reply_markup)

def button_callback(update):
    query = update.callback_query
    chat_id = query.message.chat_id

    # Убрали query.answer() для предотвращения ошибки
    bot.send_message(chat_id=chat_id, text='Кнопка "Купить картину" нажата')

    if query.data == 'buy_painting':
        try:
            bot.send_message(chat_id=chat_id, text='Запрашиваю список картин...')
            response = requests.get('https://imageshopbot.vercel.app/api/products')
            products = response.json()
            bot.send_message(chat_id=chat_id, text=f'Получено {len(products)} картин')
        except Exception as e:
            bot.send_message(chat_id=chat_id, text='Ошибка при загрузке картин: ' + str(e))
            return

        keyboard = [
            [InlineKeyboardButton(product['name'], callback_data=f"select_painting_{product['item_id']}")]
            for product in products
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        bot.send_message(chat_id=chat_id, text='Выберите картину:', reply_markup=reply_markup)
    elif query.data.startswith('select_painting_'):
        # Проверяем, есть ли уже активный заказ
        if chat_id in pending_orders:
            bot.send_message(chat_id=chat_id, text="У вас уже есть активный заказ. Дождитесь его завершения или нажмите 'Отменить заказ'.",
                             reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Отменить заказ", callback_data='cancel_order')]]))
            return

        painting_id = query.data.split('_')[-1]
        response = requests.get('https://imageshopbot.vercel.app/api/products')
        products = response.json()
        selected_painting = next((p for p in products if p['item_id'] == painting_id), None)

        if selected_painting:
            bot.send_message(chat_id=chat_id, text=f"Вы выбрали картину с ID: {painting_id}!")

            usdt_price_rub = get_usdt_price_in_rub()
            if not usdt_price_rub:
                bot.send_message(chat_id=chat_id, text="Не удалось получить курс USDT. Попробуйте позже.")
                return

            price_rub = selected_painting['price']
            price_usdt = price_rub / usdt_price_rub
            price_usdt_units = int(price_usdt * 1e6)

            payment_url = f"tron:{TRON_WALLET_ADDRESS}?amount={price_usdt}&token=USDT&message=Payment for painting {painting_id}"
            qr_code_buffer = generate_qr_code(payment_url)

            bot.send_message(
                chat_id=chat_id,
                text=f"Пожалуйста, переведите {price_usdt:.2f} USDT (TRC-20) на адрес:\n{TRON_WALLET_ADDRESS}\n\nСумма в рублях: {price_rub} RUB"
            )
            bot.send_photo(
                chat_id=chat_id,
                photo=qr_code_buffer,
                caption="Сканируйте QR-код для оплаты (USDT TRC-20)",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Отменить заказ", callback_data='cancel_order')]])
            )

            pending_orders[chat_id] = {
                "painting_id": painting_id,
                "price_usdt_units": price_usdt_units,
                "timestamp": time.time(),
                "processed": False
            }

            check_payment(chat_id)
        else:
            bot.send_message(chat_id=chat_id, text="Картина не найдена.")
    elif query.data == 'cancel_order':
        if chat_id in pending_orders:
            del pending_orders[chat_id]
            bot.send_message(chat_id=chat_id, text="Заказ отменён. Начните заново с /start.")
        else:
            bot.send_message(chat_id=chat_id, text="Нет активного заказа для отмены.")

def check_payment(chat_id):
    order = pending_orders.get(chat_id)
    if not order or order.get("processed"):
        return

    painting_id = order["painting_id"]
    price_usdt_units = order["price_usdt_units"]
    start_time = order["timestamp"]

    wallet_hex = tron_address_to_hex(TRON_WALLET_ADDRESS)

    timeout = 600
    last_checked_tx = None

    while time.time() - start_time < timeout:
        if chat_id not in pending_orders or pending_orders[chat_id]["processed"]:
            return

        try:
            url = f"https://api.trongrid.io/v1/accounts/{TRON_WALLET_ADDRESS}/transactions/trc20"
            headers = {"TRON-PRO-API-KEY": TRONGRID_API_KEY}
            params = {"limit": 50}
            if last_checked_tx:
                params["min_timestamp"] = int(last_checked_tx * 1000)
            response = requests.get(url, headers=headers, params=params)
            data = response.json()

            transactions = data.get("data", [])
            for tx in transactions:
                if tx["token_info"]["address"] != USDT_CONTRACT_ADDRESS:
                    continue

                if tx["to"] != TRON_WALLET_ADDRESS:
                    continue

                value = int(tx["value"])
                if value >= price_usdt_units:
                    bot.send_message(
                        chat_id=chat_id,
                        text=f"Оплата подтверждена! Вы купили картину с ID: {painting_id}. Спасибо за покупку!"
                    )
                    if chat_id in pending_orders:
                        pending_orders[chat_id]["processed"] = True
                        del pending_orders[chat_id]
                    return

                last_checked_tx = max(last_checked_tx or 0, int(tx["block_timestamp"]) / 1000)

            time.sleep(30)
        except Exception as e:
            print(f"Ошибка при проверке оплаты: {str(e)}")
            time.sleep(30)

    if chat_id in pending_orders and not pending_orders[chat_id]["processed"]:
        bot.send_message(chat_id=chat_id, text="Время ожидания оплаты истекло. Попробуйте снова.")
        pending_orders[chat_id]["processed"] = True
        del pending_orders[chat_id]

@app.route('/telegram', methods=['POST', 'GET'])
def webhook():
    if request.method == 'POST':
        try:
            update = Update.de_json(request.get_json(force=True), bot)
            if update.message and update.message.text == '/start':
                start(update)
            elif update.callback_query:
                print("Получен callback от Telegram")
                button_callback(update)
            return 'OK'
        except Exception as e:
            print(f"Ошибка в webhook: {str(e)}")
            return 'Error', 500
    return 'Webhook is running'

@app.route('/')
def index():
    return 'Bot is running'