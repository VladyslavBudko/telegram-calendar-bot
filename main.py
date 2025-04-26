
import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)
import telegram

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
EVENTS_FILE = "events.json"
MODS_FILE = "moderators.json"

def load_events():
    try:
        with open(EVENTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_events(events):
    with open(EVENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)

def load_mods():
    try:
        with open(MODS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_mods(mods):
    with open(MODS_FILE, "w", encoding="utf-8") as f:
        json.dump(mods, f, ensure_ascii=False, indent=2)

events = load_events()
moderators = load_mods()

ADDING, COMMENTING, REMOVING, EDITING, SELECTING, PROMOTING = range(6)

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📅 Календарь", callback_data="view_calendar")],
        [InlineKeyboardButton("➕ Добавить событие", callback_data="event_menu")]
    ])

def period_buttons():
    return [
        [InlineKeyboardButton("📆 Неделя", callback_data="period_week"),
         InlineKeyboardButton("🗓 Месяц", callback_data="period_month"),
         InlineKeyboardButton("📅 Год", callback_data="period_year")],
        [InlineKeyboardButton("🔁 Старт", callback_data="back_to_main")]
    ]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Выберите действие:", reply_markup=main_menu())

async def view_calendar(update: Update, context: ContextTypes.DEFAULT_TYPE, period="month"):
    query = update.callback_query
    await query.answer()
    now = datetime.now()
    user = update.effective_user.first_name
    filtered = []
    for event in events:
        try:
            d = datetime.strptime(event['date'], "%Y.%m.%d")
            is_visible = event['visibility'] == "public" or event['user'] == user
            if not is_visible:
                continue
            if period == "week" and now <= d <= now + timedelta(weeks=1):
                filtered.append((d, event))
            elif period == "month" and now.month == d.month and now.year == d.year:
                filtered.append((d, event))
            elif period == "year" and now.year == d.year:
                filtered.append((d, event))
        except:
            continue
    filtered.sort(key=lambda x: x[0])
    keyboard = []
    for _, e in filtered:
        text = f"{e['color']} {e['date']} — {e['title']} ({e['user']})"
        keyboard.append([InlineKeyboardButton(text, callback_data=f"select_{events.index(e)}")])
    keyboard += period_buttons()
    try:
        await query.edit_message_text("🗓️ События:", reply_markup=InlineKeyboardMarkup(keyboard))
    except telegram.error.BadRequest as e:
        if "Message is not modified" not in str(e):
            raise

async def select_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    idx = int(query.data.split("_")[1])
    context.user_data['selected_event'] = idx
    e = events[idx]
    user = update.effective_user.first_name
    text = f"{e['color']} {e['date']}\\n{e['title']} ({e['user']})"
    if e['comments']:
        text += "\\n💬 Комментарии:\\n"
        for c in e['comments']:
            text += f"- {c}\\n"
    buttons = [[InlineKeyboardButton("💬 Комментировать", callback_data="comment_event")]]
    if e['user'] == user or user in moderators:
        buttons.insert(0, [InlineKeyboardButton("✏️ Редактировать", callback_data="edit_event")])
        buttons.append([InlineKeyboardButton("🗑 Удалить", callback_data="remove_event")])
    buttons.append([InlineKeyboardButton("🔁 Старт", callback_data="back_to_main")])
    await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(buttons))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.callback_query.data
    if data == "view_calendar":
        await view_calendar(update, context)
    elif data == "event_menu":
        await event_menu(update, context)
    elif data == "back_to_main":
        await start(update.callback_query, context)
    elif data.startswith("period_"):
        await view_calendar(update, context, data.split("_")[1])
    elif data.startswith("select_"):
        await select_event(update, context)
        return SELECTING
    elif data in ["public_event", "private_event"]:
        context.user_data['visibility'] = "public" if data == "public_event" else "private"
        await update.callback_query.edit_message_text("Введите: дата (ГГГГ.ММ.ДД) название события")
        return ADDING
    elif data == "comment_event":
        await update.callback_query.edit_message_text("Введите комментарий:")
        return COMMENTING
    elif data == "edit_event":
        await update.callback_query.edit_message_text("Введите новую дату и название:")
        return EDITING
    elif data == "remove_event":
        await update.callback_query.edit_message_text("Напишите 'да', чтобы подтвердить удаление")
        return REMOVING
    elif data == "promote_user":
        user = update.effective_user.first_name
        if user in moderators:
            await update.callback_query.edit_message_text("Введите имя пользователя, которому выдать права модератора:")
            return PROMOTING
        else:
            await update.callback_query.edit_message_text("Только модератор может выдавать права.")
            return ConversationHandler.END

async def add_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        date, title = update.message.text.strip().split(" ", 1)
        user = update.effective_user.first_name
        visibility = context.user_data.get("visibility", "public")
        events.append({
            "user": user,
            "title": title,
            "date": date,
            "color": "🔵" if visibility == "public" else "🟣",
            "comments": [],
            "visibility": visibility
        })
        save_events(events)
        await update.message.reply_text("Событие добавлено!", reply_markup=main_menu())
    except:
        await update.message.reply_text("Ошибка. Формат: дата (ГГГГ.ММ.ДД) название", reply_markup=main_menu())
    return ConversationHandler.END

async def comment_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        idx = context.user_data['selected_event']
        comment = update.message.text.strip()
        user = update.effective_user.first_name
        events[idx]['comments'].append(f"{user}: {comment}")
        save_events(events)
        await update.message.reply_text("Комментарий добавлен.", reply_markup=main_menu())
    except:
        await update.message.reply_text("Ошибка при добавлении комментария.", reply_markup=main_menu())
    return ConversationHandler.END

async def edit_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        idx = context.user_data['selected_event']
        user = update.effective_user.first_name
        parts = update.message.text.strip().split(" ", 1)
        if events[idx]['user'] != user and user not in moderators:
            await update.message.reply_text("Нет прав на редактирование.", reply_markup=main_menu())
            return ConversationHandler.END
        events[idx]['date'], events[idx]['title'] = parts[0], parts[1]
        save_events(events)
        await update.message.reply_text("Событие обновлено.", reply_markup=main_menu())
    except:
        await update.message.reply_text("Ошибка редактирования.", reply_markup=main_menu())
    return ConversationHandler.END

async def remove_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        idx = context.user_data['selected_event']
        user = update.effective_user.first_name
        if events[idx]['user'] != user and user not in moderators:
            await update.message.reply_text("Нет прав на удаление.", reply_markup=main_menu())
            return ConversationHandler.END
        if update.message.text.strip().lower() == "да":
            events.pop(idx)
            save_events(events)
            await update.message.reply_text("Удалено.", reply_markup=main_menu())
        else:
            await update.message.reply_text("Удаление отменено.", reply_markup=main_menu())
    except:
        await update.message.reply_text("Ошибка удаления.", reply_markup=main_menu())
    return ConversationHandler.END

async def promote_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_mod = update.message.text.strip()
    user = update.effective_user.first_name
    if user in moderators:
        if new_mod not in moderators:
            moderators.append(new_mod)
            save_mods(moderators)
            await update.message.reply_text(f"{new_mod} теперь модератор ✅", reply_markup=main_menu())
        else:
            await update.message.reply_text(f"{new_mod} уже является модератором.", reply_markup=main_menu())
    else:
        await update.message.reply_text("У вас нет прав для этого действия.", reply_markup=main_menu())
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Действие отменено.", reply_markup=main_menu())
    return ConversationHandler.END

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler)],
        states={
            ADDING: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_event)],
            COMMENTING: [MessageHandler(filters.TEXT & ~filters.COMMAND, comment_event)],
            REMOVING: [MessageHandler(filters.TEXT & ~filters.COMMAND, remove_event)],
            EDITING: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_event)],
            PROMOTING: [MessageHandler(filters.TEXT & ~filters.COMMAND, promote_user)],
            SELECTING: [CallbackQueryHandler(button_handler)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv)
    app.run_polling()