import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)
from datetime import datetime

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

events = [
    {"user": "Alice", "title": "Встреча с командой", "date": "2025-04-24", "color": "🔵"},
    {"user": "Bob", "title": "Демо-показ", "date": "2025-04-25", "color": "🟢"},
    {"user": "Alice", "title": "Звонок клиенту", "date": "2025-04-26", "color": "🔵"}
]

ADDING, REMOVING = range(2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📅 Неделя", callback_data='week')],
        [InlineKeyboardButton("🗓️ Месяц", callback_data='month')],
        [InlineKeyboardButton("➕ Добавить событие", callback_data='add')],
        [InlineKeyboardButton("➖ Удалить событие", callback_data='remove')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Выберите действие:', reply_markup=reply_markup)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data in ["week", "month"]:
        text = "🗓️ События:\\n"
        for idx, event in enumerate(events, 1):
            text += f"{idx}. {event['color']} {event['date']} — {event['title']} ({event['user']})\\n"
        await query.edit_message_text(text=text)
    elif query.data == "add":
        await query.edit_message_text("Введите событие в формате: дата название (например: 2025-05-01 Встреча)")
        return ADDING
    elif query.data == "remove":
        text = "Выберите номер события для удаления:\\n"
        for idx, event in enumerate(events, 1):
            text += f"{idx}. {event['date']} — {event['title']}\\n"
        await query.edit_message_text(text=text)
        return REMOVING

async def add_event_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        parts = update.message.text.strip().split(" ", 1)
        date, title = parts[0], parts[1]
        user = update.effective_user.first_name
        events.append({"user": user, "title": title, "date": date, "color": "🟣"})
        await update.message.reply_text(f"Событие добавлено: {date} — {title}")
    except Exception:
        await update.message.reply_text("Ошибка. Введите в формате: дата название")
    return ConversationHandler.END

async def remove_event_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        idx = int(update.message.text.strip()) - 1
        if 0 <= idx < len(events):
            removed = events.pop(idx)
            await update.message.reply_text(f"Удалено: {removed['date']} — {removed['title']}")
        else:
            await update.message.reply_text("Неверный номер.")
    except ValueError:
        await update.message.reply_text("Введите номер события.")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Действие отменено.")
    return ConversationHandler.END

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button)],
        states={
            ADDING: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_event_text)],
            REMOVING: [MessageHandler(filters.TEXT & ~filters.COMMAND, remove_event_text)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    app.run_polling()