import requests
from flask import Flask, request
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest
import qrcode
from io import BytesIO
from PIL import Image
import time
import base58  # Для декодирования Tron-адресов

app = Flask(__name__)
BOT_TOKEN = "7981458266:AAGp5jIgvf_KHN_P_7pBURBnYqrT-X89mNQ"
bot = Bot(token=BOT_TOKEN)
TRON_WALLET_ADDRESS = "TMMbcqzcN6fFEXeq5TWqHk4nDUsmrVypng"  # Замените на ваш Tron-адрес
TRONGRID_API_KEY = "6ab0dfd8-2f14-489d-82a3-c30f630fb0a8"  # Замените на ваш API-ключ TronGrid
USDT_CONTRACT_ADDRESS = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"  # Контракт USDT (TRC-20) в сети Tron

# Хранилище заказов (временное, для демонстрации; в продакшене используйте БД)
pending_orders = {}

def get_usdt_price_in_rub():
    """Получаем курс USDT/RUB с CoinGecko"""
    try:
        response = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=tether&vs_currencies=rub")
        data = response.json()
        return data["tether"]["rub"]
    except Exception as e:
        print(f"Ошибка при получении курса USDT: {str(e)}")
        return None

def generate_qr_code(payment_url):
    """Генерируем QR-код для оплаты"""
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(payment_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer

def tron_address_to_hex(address):
    """Преобразуем Tron-адрес из Base58 в HEX"""
    decoded = base58.b58decode(address)
    hex_address = "41" + decoded[1:-4].hex()  # Tron-адреса начинаются с 0x41
    return hex_address

def start(update):
    keyboard = [[InlineKeyboardButton("Купить картину", callback_data='buy_painting')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    bot.send_message(chat_id=update.message.chat_id, text='Добро пожаловать в магазин!', reply_markup=reply_markup)

def button_callback(update):
    query = update.callback_query
    try:
        query.answer()
    except BadRequest as e:
        print(f"Ошибка при ответе на callback: {str(e)}")

    bot.send_message(chat_id=query.message.chat_id, text='Кнопка "Купить картину" нажата')

    if query.data == 'buy_painting':
        try:
            bot.send_message(chat_id=query.message.chat_id, text='Запрашиваю список картин...')
            response = requests.get('https://imageshopbot.vercel.app/api/products')
            products = response.json()
            bot.send_message(chat_id=query.message.chat_id, text=f'Получено {len(products)} картин')
        except Exception as e:
            bot.send_message(chat_id=query.message.chat_id, text='Ошибка при загрузке картин: ' + str(e))
            return

        keyboard = [
            [InlineKeyboardButton(product['name'], callback_data=f"select_painting_{product['item_id']}")]
            for product in products
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        bot.send_message(chat_id=query.message.chat_id, text='Выберите картину:', reply_markup=reply_markup)
    elif query.data.startswith('select_painting_'):
        painting_id = query.data.split('_')[-1]
        response = requests.get('https://imageshopbot.vercel.app/api/products')
        products = response.json()
        selected_painting = next((p for p in products if p['item_id'] == painting_id), None)

        if selected_painting:
            bot.send_message(chat_id=query.message.chat_id, text=f"Вы выбрали картину с ID: {painting_id}!")

            # Получаем курс USDT/RUB
            usdt_price_rub = get_usdt_price_in_rub()
            if not usdt_price_rub:
                bot.send_message(chat_id=query.message.chat_id, text="Не удалось получить курс USDT. Попробуйте позже.")
                return

            # Конвертируем цену картины в USDT
            price_rub = selected_painting['price']  # Цена в рублях
            price_usdt = price_rub / usdt_price_rub  # Цена в USDT
            price_usdt_units = int(price_usdt * 1e6)  # USDT имеет 6 десятичных знаков (1 USDT = 10^6 единиц)

            # Формируем данные для оплаты
            payment_url = f"tron:{TRON_WALLET_ADDRESS}?amount={price_usdt}&token=USDT&message=Payment for painting {painting_id}"
            qr_code_buffer = generate_qr_code(payment_url)

            # Отправляем пользователю данные для оплаты
            bot.send_message(
                chat_id=query.message.chat_id,
                text=f"Пожалуйста, переведите {price_usdt:.2f} USDT (TRC-20) на адрес:\n{TRON_WALLET_ADDRESS}\n\nСумма в рублях: {price_rub} RUB"
            )
            bot.send_photo(
                chat_id=query.message.chat_id,
                photo=qr_code_buffer,
                caption="Сканируйте QR-код для оплаты (USDT TRC-20)"
            )

            # Сохраняем заказ
            pending_orders[query.message.chat_id] = {
                "painting_id": painting_id,
                "price_usdt_units": price_usdt_units,
                "timestamp": time.time()
            }

            # Запускаем проверку оплаты
            check_payment(query.message.chat_id)
        else:
            bot.send_message(chat_id=query.message.chat_id, text="Картина не найдена.")

def check_payment(chat_id):
    """Проверяем оплату через TronGrid"""
    order = pending_orders.get(chat_id)
    if not order:
        return

    painting_id = order["painting_id"]
    price_usdt_units = order["price_usdt_units"]
    start_time = order["timestamp"]

    # Преобразуем Tron-адрес в HEX
    wallet_hex = tron_address_to_hex(TRON_WALLET_ADDRESS)

    # Проверяем транзакции на адрес (в течение 10 минут)
    timeout = 600  # 10 минут
    last_checked_tx = None

    while time.time() - start_time < timeout:
        try:
            # Запрашиваем транзакции на адрес через TronGrid
            url = f"https://api.trongrid.io/v1/accounts/{TRON_WALLET_ADDRESS}/transactions/trc20"
            headers = {"TRON-PRO-API-KEY": TRONGRID_API_KEY}
            params = {"limit": 50}
            if last_checked_tx:
                params["min_timestamp"] = int(last_checked_tx * 1000)
            response = requests.get(url, headers=headers, params=params)
            data = response.json()

            # Проверяем последние транзакции
            transactions = data.get("data", [])
            for tx in transactions:
                # Проверяем, что транзакция связана с USDT
                if tx["token_info"]["address"] != USDT_CONTRACT_ADDRESS:
                    continue

                # Проверяем, что получатель — наш адрес
                if tx["to"] != TRON_WALLET_ADDRESS:
                    continue

                # Проверяем сумму
                value = int(tx["value"])  # Сумма в единицах USDT (1 USDT = 10^6)
                if value >= price_usdt_units:
                    # Оплата найдена
                    bot.send_message(
                        chat_id=chat_id,
                        text=f"Оплата подтверждена! Вы купили картину с ID: {painting_id}. Спасибо за покупку!"
                    )
                    del pending_orders[chat_id]
                    return

                # Обновляем время последней проверенной транзакции
                last_checked_tx = max(last_checked_tx or 0, int(tx["block_timestamp"]) / 1000)

            # Ждём 30 секунд перед следующей проверкой
            time.sleep(30)
        except Exception as e:
            print(f"Ошибка при проверке оплаты: {str(e)}")
            time.sleep(30)

    # Если время ожидания истекло
    if chat_id in pending_orders:
        bot.send_message(chat_id=chat_id, text="Время ожидания оплаты истекло. Попробуйте снова.")
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