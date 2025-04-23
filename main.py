import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)
from datetime import datetime

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Список тестовых событий
events = [
    {"user": "Alice", "title": "Встреча с командой", "date": "2025-04-24", "color": "🔵"},
    {"user": "Bob", "title": "Демо-показ", "date": "2025-04-25", "color": "🟢"},
    {"user": "Alice", "title": "Звонок клиенту", "date": "2025-04-26", "color": "🔵"}
]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Неделя", callback_data='week')],
        [InlineKeyboardButton("Месяц", callback_data='month')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Привет! Я календарный бот 📅. Выберите период:', reply_markup=reply_markup)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    period = query.data
    filtered = events if period == "week" else events  # Упрощённая фильтрация
    text = "🗓️ События:
"
    for event in filtered:
        text += f"{event['color']} {event['date']} — {event['title']} ({event['user']})\n"
    await query.edit_message_text(text=text)

async def add_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Используй: /addevent дата название")
        return
    date = context.args[0]
    title = " ".join(context.args[1:])
    user = update.effective_user.first_name
    color = "🟣"
    events.append({"user": user, "title": title, "date": date, "color": color})
    await update.message.reply_text(f"Событие добавлено: {date} — {title}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("/start — начать\n/addevent — добавить событие (дата название)\n/help — справка")

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addevent", add_event))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(button))
    app.run_polling()
