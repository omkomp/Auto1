import requests
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, Dispatcher, CommandHandler, CallbackQueryHandler, CallbackContext

app = Flask(__name__)
updater = Updater("7981458266:AAGp5jIgvf_KHN_P_7pBURBnYqrT-X89mNQ", use_context=True)
dp = updater.dispatcher

def start(update: Update, context: CallbackContext) -> None:
    keyboard = [[InlineKeyboardButton("Купить картину", callback_data='buy_painting')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Добро пожаловать в магазин!', reply_markup=reply_markup)

def button_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()

    if query.data == 'buy_painting':
        try:
            response = requests.get('https://imageshopbot.vercel.app/api/products')
            products = response.json()
        except Exception as e:
            query.message.reply_text('Ошибка при загрузке картин: ' + str(e))
            return

        keyboard = [
            [InlineKeyboardButton(product['name'], callback_data=f"select_painting_{product['item_id']}")]
            for product in products
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.message.reply_text('Выберите картину:', reply_markup=reply_markup)

def select_painting_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    painting_id = query.data.split('_')[-1]
    query.message.reply_text(f'Вы выбрали картину с ID: {painting_id}!')

dp.add_handler(CommandHandler('start', start))
dp.add_handler(CallbackQueryHandler(button_callback, pattern='^buy_painting$'))
dp.add_handler(CallbackQueryHandler(select_painting_callback, pattern='^select_painting_'))

@app.route('/telegram', methods=['POST', 'GET'])
def webhook():
    if request.method == 'POST':
        update = Update.de_json(request.get_json(force=True), updater.bot)
        dp.process_update(update)
        return 'OK'
    return 'Webhook is running'

@app.route('/')
def index():
    return 'Bot is running'