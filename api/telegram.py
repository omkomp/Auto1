from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, Dispatcher, CommandHandler, CallbackQueryHandler

app = Flask(__name__)
updater = Updater("YOUR_BOT_TOKEN", use_context=True)  # Замените YOUR_BOT_TOKEN на ваш токен
dp = updater.dispatcher

# Обработчик команды /start
def start(update, context):
    keyboard = [[InlineKeyboardButton("Купить картину", callback_data='buy_painting')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Добро пожаловать в магазин!', reply_markup=reply_markup)

# Обработчик нажатия на кнопку
def button_callback(update, context):
    query = update.callback_query
    query.answer()
    if query.data == 'buy_painting':
        query.message.reply_text('Выберите картину!')

# Регистрация обработчиков
dp.add_handler(CommandHandler('start', start))
dp.add_handler(CallbackQueryHandler(button_callback))

# Маршрут для Telegram webhook
@app.route('/telegram', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), updater.bot)
    dp.process_update(update)
    return 'OK'

# Корневой маршрут для проверки
@app.route('/')
def index():
    return 'Bot is running'