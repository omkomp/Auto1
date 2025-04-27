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
processed_callbacks = set()
ORDER_TIMEOUT = 24 * 60 * 60  # 24 часа в секундах

def cleanup_old_orders():
    current_time = time.time()
    expired_orders = []
    for chat_id, order in pending_orders.items():
        if current_time - order["timestamp"] > ORDER_TIMEOUT:
            expired_orders.append(chat_id)
    for chat_id in expired_orders:
        print(f"Удалён устаревший заказ для chat_id: {chat_id}")
        del pending_orders[chat_id]

def get_usdt_price_in_rub():
    print("Запрос курса USDT/RUB...")
    try:
        response = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=tether&vs_currencies=rub")
        response.raise_for_status()
        data = response.json()
        price = data["tether"]["rub"]
        print(f"Курс USDT/RUB: {price}")
        return price
    except Exception as e:
        print(f"Ошибка при получении курса USDT: {str(e)}")
        return None

def generate_qr_code(payment_url):
    print("Генерация QR-кода...")
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(payment_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    print("QR-код сгенерирован.")
    return buffer

def tron_address_to_hex(address):
    print("Преобразование Tron-адреса в HEX...")
    decoded = base58.b58decode(address)
    hex_address = "41" + decoded[1:-4].hex()
    print(f"Tron-адрес в HEX: {hex_address}")
    return hex_address

def check_payment(chat_id):
    print(f"Ручная проверка оплаты для chat_id: {chat_id}")
    order = pending_orders.get(chat_id)
    if not order or order.get("processed"):
        bot.send_message(chat_id=chat_id, text="Заказ не найден или уже обработан.")
        print(f"Заказ для chat_id {chat_id} не найден или уже обработан.")
        return

    painting_id = order["painting_id"]
    price_usdt_units = order["price_usdt_units"]
    print(f"Проверка оплаты: painting_id={painting_id}, price_usdt_units={price_usdt_units}")

    # Получаем информацию о картине, чтобы взять file_id
    response = requests.get('https://imageshopbot.vercel.app/api/products')
    products = response.json()
    selected_painting = next((p for p in products if p['item_id'] == painting_id), None)
    if not selected_painting or "file_id" not in selected_painting:
        bot.send_message(chat_id=chat_id, text="Ошибка: файл картины не найден.")
        print("Файл картины не найден в списке продуктов.")
        return

    file_id = selected_painting["file_id"]
    print(f"Используемый file_id: {file_id}")

    wallet_hex = tron_address_to_hex(TRON_WALLET_ADDRESS)

    try:
        print("Запрос транзакций TronGrid...")
        url = f"https://api.trongrid.io/v1/accounts/{TRON_WALLET_ADDRESS}/transactions/trc20"
        headers = {"TRON-PRO-API-KEY": TRONGRID_API_KEY}
        params = {"limit": 50}
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        print(f"Получены транзакции: {data}")

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
                    text=f"Оплата подтверждена! Вы купили картину с ID: {painting_id}. Вот ваш файл:"
                )
                # Отправляем файл пользователю
                bot.send_document(
                    chat_id=chat_id,
                    document=file_id,
                    filename=f"archive_{painting_id}.zip" if painting_id == "1" else f"painting_{painting_id}.jpg"
                )
                if chat_id in pending_orders:
                    pending_orders[chat_id]["processed"] = True
                    del pending_orders[chat_id]
                print(f"Оплата подтверждена для chat_id: {chat_id}, файл отправлен.")
                return

        bot.send_message(chat_id=chat_id, text="Оплата пока не подтверждена. Попробуйте снова через несколько минут.",
                         reply_markup=InlineKeyboardMarkup([
                             [InlineKeyboardButton("Проверить оплату", callback_data='check_payment')],
                             [InlineKeyboardButton("Отменить заказ", callback_data='cancel_order')]
                         ]))
        print("Транзакция не найдена.")
    except Exception as e:
        print(f"Ошибка при проверке оплаты: {str(e)}")
        bot.send_message(chat_id=chat_id, text="Произошла ошибка при проверке оплаты. Попробуйте снова.",
                         reply_markup=InlineKeyboardMarkup([
                             [InlineKeyboardButton("Проверить оплату", callback_data='check_payment')],
                             [InlineKeyboardButton("Отменить заказ", callback_data='cancel_order')]
                         ]))
        return

def start(update):
    chat_id = update.message.chat_id
    print(f"Получена команда /start для chat_id: {chat_id}")
    if chat_id in pending_orders:
        del pending_orders[chat_id]
    keyboard = [[InlineKeyboardButton("Купить картину", callback_data='buy_painting')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    print("Отправка приветственного сообщения...")
    bot.send_message(chat_id=chat_id, text='Добро пожаловать в магазин!', reply_markup=reply_markup)
    print("Сообщение отправлено.")

def handle_document(update):
    chat_id = update.message.chat_id
    document = update.message.document
    file_id = document.file_id
    file_name = document.file_name
    print(f"Получен документ от chat_id: {chat_id}, file_id: {file_id}, file_name: {file_name}")
    bot.send_message(chat_id=chat_id, text=f"Получен документ: {file_name}\nfile_id: {file_id}")

def button_callback(update):
    query = update.callback_query
    if not query:
        print("Callback query отсутствует!")
        return

    try:
        query_id = query.id
        chat_id = query.message.chat_id if query.message else None
        query_data = query.data
    except AttributeError as e:
        print(f"Ошибка доступа к полям callback-запроса: {str(e)}")
        return

    if not chat_id or not query_data:
        print(f"Недостаточно данных в callback-запросе: chat_id={chat_id}, data={query_data}")
        return

    if query_id in processed_callbacks:
        print(f"Callback {query_id} уже обработан, пропускаем.")
        return
    processed_callbacks.add(query_id)

    print(f"Получен callback для chat_id: {chat_id}, data: {query_data}")

    # Очистка устаревших заказов перед обработкой
    cleanup_old_orders()

    if query_data == 'buy_painting':
        try:
            print("Отправка сообщения 'Кнопка Купить картину нажата'...")
            bot.send_message(chat_id=chat_id, text='Кнопка "Купить картину" нажата')
            print("Запрос списка картин...")
            bot.send_message(chat_id=chat_id, text='Запрашиваю список картин...')
            response = requests.get('https://imageshopbot.vercel.app/api/products')
            response.raise_for_status()
            products = response.json()
            print(f"Получены продукты: {products}")
            bot.send_message(chat_id=chat_id, text=f'Получено {len(products)} картин')
        except Exception as e:
            print(f"Ошибка при загрузке картин: {str(e)}")
            bot.send_message(chat_id=chat_id, text='Ошибка при загрузке картин: ' + str(e))
            return

        keyboard = [
            [InlineKeyboardButton(product['name'], callback_data=f"select_painting_{product['item_id']}")]
            for product in products
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        bot.send_message(chat_id=chat_id, text='Выберите картину:', reply_markup=reply_markup)
    elif query_data.startswith('select_painting_'):
        if chat_id in pending_orders:
            print(f"Обнаружен активный заказ для chat_id: {chat_id}")
            bot.send_message(chat_id=chat_id, text="У вас уже есть активный заказ. Дождитесь его завершения или нажмите 'Отменить заказ'.",
                             reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Отменить заказ", callback_data='cancel_order')]]))
            return

        painting_id = query_data.split('_')[-1]
        print(f"Выбрана картина с ID: {painting_id}")
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
            print(f"Цена картины: {price_rub} RUB, {price_usdt:.2f} USDT")

            payment_url = f"tron:{TRON_WALLET_ADDRESS}?amount={price_usdt}&token=USDT&message=Payment for painting {painting_id}"
            qr_code_buffer = generate_qr_code(payment_url)

            print("Отправка сообщения с данными для оплаты...")
            bot.send_message(
                chat_id=chat_id,
                text=f"Пожалуйста, переведите {price_usdt:.2f} USDT (TRC-20) на адрес:\n{TRON_WALLET_ADDRESS}\n\nСумма в рублях: {price_rub} RUB"
            )
            print("Отправка QR-кода...")
            bot.send_photo(
                chat_id=chat_id,
                photo=qr_code_buffer,
                caption="Сканируйте QR-код для оплаты (USDT TRC-20)",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Проверить оплату", callback_data='check_payment')],
                    [InlineKeyboardButton("Отменить заказ", callback_data='cancel_order')]
                ])
            )

            pending_orders[chat_id] = {
                "painting_id": painting_id,
                "price_usdt_units": price_usdt_units,
                "timestamp": time.time(),
                "processed": False
            }
            print(f"Заказ сохранён для chat_id: {chat_id}")
        else:
            bot.send_message(chat_id=chat_id, text="Картина не найдена.")
    elif query_data == 'check_payment':
        check_payment(chat_id)
    elif query_data == 'cancel_order':
        print(f"Попытка отмены заказа для chat_id: {chat_id}")
        if chat_id in pending_orders:
            del pending_orders[chat_id]
            bot.send_message(chat_id=chat_id, text="Заказ отменён. Начните заново с /start.")
            print("Заказ успешно отменён.")
        else:
            bot.send_message(chat_id=chat_id, text="Нет активного заказа для отмены.")
            print("Заказ для отмены не найден.")

@app.route('/telegram', methods=['POST', 'GET'])
def webhook():
    print("Получен запрос на /telegram")
    if request.method == 'POST':
        try:
            update = Update.de_json(request.get_json(force=True), bot)
            print(f"Обновление: {update}")
            if update.message and update.message.text == '/start':
                start(update)
            elif update.message and update.message.document:  # Добавляем обработку документов
                handle_document(update)
            elif update.callback_query:
                print("Получен callback от Telegram")
                button_callback(update)
            return 'OK'
        except Exception as e:
            print(f"Ошибка в webhook: {str(e)}")
            return 'Error', 500
    print("Webhook возвращает статус")
    return 'Webhook is running'

@app.route('/')
def index():
    return 'Bot is running'