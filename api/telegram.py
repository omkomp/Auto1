import requests
from flask import Flask, request
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup

app = Flask(__name__)
BOT_TOKEN = "7981458266:AAGp5jIgvf_KHN_P_7pBURBnYqrT-X89mNQ"
bot = Bot(token=BOT_TOKEN)

def start(update):
    keyboard = [[InlineKeyboardButton("Купить картину", callback_data='buy_painting')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    bot.send_message(chat_id=update.message.chat_id, text='Добро пожаловать в магазин!', reply_markup=reply_markup)

def button_callback(update):
    query = update.callback_query
    query.answer()

    # Отладка: подтверждаем, что функция вызвана
    bot.send_message(chat_id=query.message.chat_id, text='Кнопка "Купить картину" нажата')

    if query.data == 'buy_painting':
        try:
            # Отладка: перед запросом к /api/products
            bot.send_message(chat_id=query.message.chat_id, text='Запрашиваю список картин...')
            response = requests.get('https://imageshopbot.vercel.app/api/products')
            products = response.json()
            # Отладка: после успешного запроса
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
        bot.send_message(chat_id=query.message.chat_id, text=f'Вы выбрали картину с ID: {painting_id}!')

@app.route('/telegram', methods=['POST', 'GET'])
def webhook():
    if request.method == 'POST':
        try:
            update = Update.de_json(request.get_json(force=True), bot)
            if update.message and update.message.text == '/start':
                start(update)
            elif update.callback_query:
                # Отладка: подтверждаем, что получили callback
                print("Получен callback от Telegram")
                button_callback(update)
            return 'OK'
        except Exception as e:
            # Отладка: выводим ошибку в логи
            print(f"Ошибка в webhook: {str(e)}")
            return 'Error', 500
    return 'Webhook is running'

@app.route('/')
def index():
    return 'Bot is running'