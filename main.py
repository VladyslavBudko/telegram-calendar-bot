
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
    {"user": "Alice", "title": "Встреча с командой", "date": "2025-04-24", "color": "🔵", "comments": []},
    {"user": "Bob", "title": "Демо-показ", "date": "2025-04-25", "color": "🟢", "comments": []},
    {"user": "Alice", "title": "Звонок клиенту", "date": "2025-04-26", "color": "🔵", "comments": []}
]

ADDING, REMOVING, COMMENTING, EDITING = range(4)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📅 Посмотреть календарь", callback_data='view_calendar')],
        [InlineKeyboardButton("📝 События", callback_data='event_menu')]
    ]
    await update.message.reply_text('Выберите действие:', reply_markup=InlineKeyboardMarkup(keyboard))

async def event_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("➕ Добавить", callback_data='add_event')],
        [InlineKeyboardButton("✏️ Редактировать", callback_data='edit_event')],
        [InlineKeyboardButton("➖ Удалить", callback_data='remove_event')],
        [InlineKeyboardButton("💬 Комментарий", callback_data='comment_event')],
        [InlineKeyboardButton("⬅️ Назад", callback_data='back_to_main')]
    ]
    text = "Меню событий:\n- Добавить\n- Удалить\n- Редактировать\n- Комментировать"
    await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))

async def view_calendar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = "🗓️ События по дням:\n\n"
    for idx, event in enumerate(events, 1):
        text += f"{idx}. {event['color']} {event['date']}\n{event['title']} ({event['user']})\n"
        if event['comments']:
            text += "💬 Комментарии:\n"
            for c in event['comments']:
                text += f"- {c}\n"
        text += "\n"
    await query.edit_message_text(text=text)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.callback_query.data
    if data == 'view_calendar':
        await view_calendar(update, context)
    elif data == 'event_menu':
        await event_menu(update, context)
    elif data == 'back_to_main':
        await start(update.callback_query, context)
    elif data == 'add_event':
        await update.callback_query.edit_message_text("Введите: дата название события")
        return ADDING
    elif data == 'remove_event':
        await update.callback_query.edit_message_text("Введите номер события для удаления")
        return REMOVING
    elif data == 'comment_event':
        await update.callback_query.edit_message_text("Введите: номер комментарий")
        return COMMENTING
    elif data == 'edit_event':
        await update.callback_query.edit_message_text("Введите: номер новая_дата новое_название")
        return EDITING

async def add_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        date, title = update.message.text.strip().split(" ", 1)
        user = update.effective_user.first_name
        events.append({"user": user, "title": title, "date": date, "color": "🟣", "comments": []})
        await update.message.reply_text(f"Добавлено: {date} — {title}")
    except:
        await update.message.reply_text("Неверный формат. Введите: дата название")
    return ConversationHandler.END

async def remove_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        idx = int(update.message.text.strip()) - 1
        if 0 <= idx < len(events):
            removed = events.pop(idx)
            await update.message.reply_text(f"Удалено: {removed['date']} — {removed['title']}")
        else:
            await update.message.reply_text("Неверный номер.")
    except:
        await update.message.reply_text("Ошибка. Введите номер события.")
    return ConversationHandler.END

async def comment_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        number, comment = update.message.text.strip().split(" ", 1)
        idx = int(number) - 1
        if 0 <= idx < len(events):
            user = update.effective_user.first_name
            events[idx]["comments"].append(f"{user}: {comment}")
            await update.message.reply_text("Комментарий добавлен.")
        else:
            await update.message.reply_text("Неверный номер.")
    except:
        await update.message.reply_text("Формат: номер комментарий")
    return ConversationHandler.END

async def edit_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        parts = update.message.text.strip().split(" ", 2)
        idx = int(parts[0]) - 1
        new_date, new_title = parts[1], parts[2]
        if 0 <= idx < len(events):
            events[idx]['date'] = new_date
            events[idx]['title'] = new_title
            await update.message.reply_text(f"Обновлено: {new_date} — {new_title}")
        else:
            await update.message.reply_text("Неверный номер.")
    except:
        await update.message.reply_text("Формат: номер новая_дата новое_название")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Действие отменено.")
    return ConversationHandler.END

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler)],
        states={
            ADDING: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_event)],
            REMOVING: [MessageHandler(filters.TEXT & ~filters.COMMAND, remove_event)],
            COMMENTING: [MessageHandler(filters.TEXT & ~filters.COMMAND, comment_event)],
            EDITING: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_event)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    app.run_polling()
