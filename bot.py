import json
import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackContext, filters

load_dotenv()

async def start(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton(
            "🖼 Купить картину",
            web_app=WebAppInfo(url=os.getenv("WEB_APP_URL", "https://imageshopbot-2chsz4t2c-art-bots-projects.vercel.app/"))
        )]
    ]
    await update.message.reply_text(
        "Добро пожаловать в магазин!",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_web_app_data(update: Update, context: CallbackContext):
    try:
        data = json.loads(update.effective_message.web_app_data.data)
        item_id = data.get('item_id', 'не указан')
        await update.message.reply_text(f"✅ Спасибо за покупку! ID товара: {item_id}")
    except (json.JSONDecodeError, KeyError) as e:
        await update.message.reply_text("❌ Ошибка обработки данных покупки.")

async def help_command(update: Update, context: CallbackContext):
    await update.message.reply_text("Используйте /start для начала работы с магазином.")

def main():
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        print("Ошибка: TELEGRAM_TOKEN не найден в .env")
        return
    
    app = Application.builder().token(token).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_web_app_data))
    
    print("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()