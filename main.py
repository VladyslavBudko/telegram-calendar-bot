import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)
from datetime import datetime, timedelta

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Список событий
events = [
    {"user": "Alice", "title": "Встреча с командой", "date": "2025-04-24", "color": "🔵", "comments": []},
    {"user": "Bob", "title": "Демо-показ", "date": "2025-04-25", "color": "🟢", "comments": []},
    {"user": "Alice", "title": "Звонок клиенту", "date": "2025-04-26", "color": "🔵", "comments": []}
]

ADDING, REMOVING, COMMENTING, EDITING, SELECTING = range(5)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Выберите действие:', reply_markup=main_menu())

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📅 Просмотреть календарь", callback_data='view_calendar')],
        [InlineKeyboardButton("➕ Добавить событие", callback_data='add_event_menu')]
    ])

async def add_event_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("🌐 Событие для всех", callback_data='add_event_public')],
        [InlineKeyboardButton("🙋‍♂️ Событие для меня", callback_data='add_event_private')],
        [InlineKeyboardButton("🔁 Старт", callback_data='back_to_main')]
    ]
    await query.edit_message_text("Выберите тип события:", reply_markup=InlineKeyboardMarkup(keyboard))

async def view_calendar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    now = datetime.now()
    end = now + timedelta(days=30)
    filtered = [e for e in events if now.strftime('%Y-%m-%d') <= e['date'] <= end.strftime('%Y-%m-%d')]
    filtered.sort(key=lambda e: e['date'])
    keyboard = [
        [InlineKeyboardButton("📅 Неделя", callback_data='calendar_week'),
         InlineKeyboardButton("🗓️ Месяц", callback_data='calendar_month'),
         InlineKeyboardButton("📆 Год", callback_data='calendar_year')]
    ]
    for idx, event in enumerate(filtered):
        text = f"{event['color']} {event['date']} — {event['title']} ({event['user']})"
        keyboard.append([InlineKeyboardButton(text, callback_data=f"select_{idx}")])
    keyboard.append([InlineKeyboardButton("🔁 Старт", callback_data='back_to_main')])
    await query.edit_message_text("События за месяц:", reply_markup=InlineKeyboardMarkup(keyboard))

async def select_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    idx = int(query.data.split("_")[1])
    context.user_data['selected_event'] = idx
    event = events[idx]
    user = update.effective_user.first_name

    buttons = [[InlineKeyboardButton("💬 Комментировать", callback_data='comment_event')]]
    if event['user'] == user:
        buttons.insert(0, [InlineKeyboardButton("✏️ Редактировать", callback_data='edit_event')])
        buttons.append([InlineKeyboardButton("🗑 Удалить", callback_data='remove_event')])
    buttons.append([InlineKeyboardButton("🔁 Старт", callback_data='back_to_main')])
    text = f"{event['color']} {event['date']}\n{event['title']} ({event['user']})"
    if event['comments']:
        text += "\n\n💬 Комментарии:\n"
        for c in event['comments']:
            text += f"- {c}\n"
    await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(buttons))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.callback_query.data
    if data == 'view_calendar':
        await view_calendar(update, context)
    elif data == 'add_event_menu':
        await add_event_menu(update, context)
    elif data in ['add_event_public', 'add_event_private']:
        context.user_data['visibility'] = '🟢' if data == 'add_event_public' else '🟣'
        await update.callback_query.edit_message_text("Введите: дата (ГГГГ.ММ.ДД) название события")
        return ADDING
    elif data == 'back_to_main':
        await start(update.callback_query, context)
    elif data.startswith("select_"):
        await select_event(update, context)
        return SELECTING
    elif data == 'remove_event':
        await update.callback_query.edit_message_text("Удаляем... Напиши любой текст для подтверждения")
        return REMOVING
    elif data == 'comment_event':
        await update.callback_query.edit_message_text("Введите комментарий")
        return COMMENTING
    elif data == 'edit_event':
        await update.callback_query.edit_message_text("Введите новую дату и название")
        return EDITING

async def add_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        date_str, title = update.message.text.strip().split(" ", 1)
        datetime.strptime(date_str, "%Y.%m.%d")
        user = update.effective_user.first_name
        visibility = context.user_data.get('visibility', '🟣')
        events.append({"user": user, "title": title, "date": date_str.replace(".", "-"), "color": visibility, "comments": []})
        await update.message.reply_text(f"Добавлено: {date_str} — {title}", reply_markup=main_menu())
    except:
        await update.message.reply_text("Неверный формат. Введите: дата (ГГГГ.ММ.ДД) название события")
    return ConversationHandler.END

async def remove_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        idx = context.user_data.get("selected_event")
        user = update.effective_user.first_name
        if events[idx]['user'] != user:
            await update.message.reply_text("Вы можете удалять только свои события.", reply_markup=main_menu())
        else:
            removed = events.pop(idx)
            await update.message.reply_text(f"Удалено: {removed['date']} — {removed['title']}", reply_markup=main_menu())
    except:
        await update.message.reply_text("Ошибка при удалении.", reply_markup=main_menu())
    return ConversationHandler.END

async def comment_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        comment = update.message.text.strip()
        idx = context.user_data.get("selected_event")
        user = update.effective_user.first_name
        events[idx]["comments"].append(f"{user}: {comment}")
        await update.message.reply_text("Комментарий добавлен.", reply_markup=main_menu())
    except:
        await update.message.reply_text("Ошибка добавления комментария.", reply_markup=main_menu())
    return ConversationHandler.END

async def edit_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        parts = update.message.text.strip().split(" ", 1)
        idx = context.user_data.get("selected_event")
        new_date, new_title = parts[0], parts[1]
        user = update.effective_user.first_name
        if events[idx]['user'] != user:
            await update.message.reply_text("Редактировать можно только свои события.", reply_markup=main_menu())
        else:
            events[idx]['date'] = new_date.replace(".", "-")
            events[idx]['title'] = new_title
            await update.message.reply_text(f"Обновлено: {new_date} — {new_title}", reply_markup=main_menu())
    except:
        await update.message.reply_text("Формат: дата новое_название", reply_markup=main_menu())
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Действие отменено.", reply_markup=main_menu())
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
            SELECTING: [CallbackQueryHandler(button_handler)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    app.run_polling()