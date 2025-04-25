
# Телеграм-бот с кнопками, событиями, сохранением в JSON и фильтрацией по периоду
import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
EVENTS_FILE = "events.json"

def load_events():
    try:
        with open(EVENTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_events(events):
    with open(EVENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)

events = load_events()
ADDING, REMOVING, COMMENTING, EDITING, SELECTING = range(5)

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📅 Посмотреть календарь", callback_data='view_calendar')],
        [InlineKeyboardButton("➕ Добавить событие", callback_data='event_menu')]
    ])

def period_buttons():
    return [
        [InlineKeyboardButton("📆 Неделя", callback_data="period_week"),
         InlineKeyboardButton("🗓 Месяц", callback_data="period_month"),
         InlineKeyboardButton("📅 Год", callback_data="period_year")],
        [InlineKeyboardButton("🔁 Старт", callback_data='back_to_main')]
    ]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Выберите действие:", reply_markup=main_menu())

async def event_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("🌍 Событие для всех", callback_data="public_event")],
        [InlineKeyboardButton("👤 Событие для меня", callback_data="private_event")],
        [InlineKeyboardButton("🔁 Старт", callback_data='back_to_main')]
    ]
    await query.edit_message_text("Кто увидит событие?", reply_markup=InlineKeyboardMarkup(keyboard))

async def view_calendar(update: Update, context: ContextTypes.DEFAULT_TYPE, period="month"):
    query = update.callback_query
    await query.answer()
    now = datetime.now()
    filtered = []
    for event in events:
        try:
            d = datetime.strptime(event['date'], "%Y.%m.%d")
            if period == "week" and now <= d <= now + timedelta(weeks=1):
                filtered.append((d, event))
            elif period == "month" and now.month == d.month and now.year == d.year:
                filtered.append((d, event))
            elif period == "year" and now.year == d.year:
                filtered.append((d, event))
        except Exception:
            continue
    filtered.sort()
    keyboard = []
    for i, (_, event) in enumerate(filtered):
        text = f"{event['color']} {event['date']} — {event['title']} ({event['user']})"
        keyboard.append([InlineKeyboardButton(text, callback_data=f"select_{events.index(event)}")])
    keyboard += period_buttons()
    await query.edit_message_text("🗓️ События:", reply_markup=InlineKeyboardMarkup(keyboard))

async def select_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    idx = int(query.data.split("_")[1])
    context.user_data['selected_event'] = idx
    event = events[idx]
    user = update.effective_user.first_name
    text = f"{event['color']} {event['date']}\n{event['title']} ({event['user']})"
    if event['comments']:
        text += "\n💬 Комментарии:\n"
        for c in event['comments']:
            text += f"- {c}\n"
    buttons = [[InlineKeyboardButton("💬 Комментировать", callback_data='comment_event')]]
    if event['user'] == user:
        buttons.insert(0, [InlineKeyboardButton("✏️ Редактировать", callback_data='edit_event')])
        buttons.append([InlineKeyboardButton("🗑 Удалить", callback_data='remove_event')])
    buttons.append([InlineKeyboardButton("🔁 Старт", callback_data='back_to_main')])
    await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(buttons))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.callback_query.data
    if data == 'view_calendar':
        await view_calendar(update, context, period="month")
    elif data == 'event_menu':
        await event_menu(update, context)
    elif data == 'back_to_main':
        await start(update.callback_query, context)
    elif data == 'public_event' or data == 'private_event':
        context.user_data['visibility'] = data
        await update.callback_query.edit_message_text("Введите: дата (ГГГГ.ММ.ДД) название события")
        return ADDING
    elif data.startswith("period_"):
        await view_calendar(update, context, data.split("_")[1])
    elif data.startswith("select_"):
        await select_event(update, context)
        return SELECTING
    elif data == 'remove_event':
        await update.callback_query.edit_message_text("Удалить это событие? Напишите 'да' для подтверждения.")
        return REMOVING
    elif data == 'comment_event':
        await update.callback_query.edit_message_text("Введите комментарий:")
        return COMMENTING
    elif data == 'edit_event':
        await update.callback_query.edit_message_text("Введите новую дату и название:")
        return EDITING

async def add_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        parts = update.message.text.strip().split(" ", 1)
        if len(parts) < 2:
            raise ValueError
        date, title = parts
        user = update.effective_user.first_name
        visibility = context.user_data.get("visibility", "public_event")
        color = "🟣" if visibility == "private_event" else "🔵"
        events.append({"user": user, "title": title, "date": date, "color": color, "comments": []})
        save_events(events)
        await update.message.reply_text(f"Добавлено: {date} — {title}", reply_markup=main_menu())
    except:
        await update.message.reply_text("Формат: дата (ГГГГ.ММ.ДД) название события", reply_markup=main_menu())
    return ConversationHandler.END

async def remove_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    idx = context.user_data.get("selected_event")
    user = update.effective_user.first_name
    if events[idx]['user'] != user:
        await update.message.reply_text("Вы можете удалять только свои события.", reply_markup=main_menu())
    elif update.message.text.strip().lower() == "да":
        removed = events.pop(idx)
        save_events(events)
        await update.message.reply_text(f"Удалено: {removed['date']} — {removed['title']}", reply_markup=main_menu())
    else:
        await update.message.reply_text("Удаление отменено.", reply_markup=main_menu())
    return ConversationHandler.END

async def comment_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        comment = update.message.text.strip()
        idx = context.user_data.get("selected_event")
        user = update.effective_user.first_name
        events[idx]["comments"].append(f"{user}: {comment}")
        save_events(events)
        await update.message.reply_text("Комментарий добавлен.", reply_markup=main_menu())
    except:
        await update.message.reply_text("Ошибка при добавлении комментария.", reply_markup=main_menu())
    return ConversationHandler.END

async def edit_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        parts = update.message.text.strip().split(" ", 1)
        new_date, new_title = parts
        idx = context.user_data.get("selected_event")
        user = update.effective_user.first_name
        if events[idx]['user'] != user:
            await update.message.reply_text("Редактировать можно только свои события.", reply_markup=main_menu())
        else:
            events[idx]['date'] = new_date
            events[idx]['title'] = new_title
            save_events(events)
            await update.message.reply_text(f"Обновлено: {new_date} — {new_title}", reply_markup=main_menu())
    except:
        await update.message.reply_text("Ошибка. Формат: дата название", reply_markup=main_menu())
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
