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
        query.message.reply_text('Выберите картинку!')

dp.add_handler(CommandHandler('start', start))
dp.add_handler(CallbackQueryHandler(button_callback))

@app.route('/telegram', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), updater.bot)
    dp.process_update(update)
    return 'OK'

@app.route('/')
def index():
    return 'Bot is running'