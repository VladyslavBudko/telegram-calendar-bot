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
    except FileNotFoundError:
        return []

def save_events(events):
    with open(EVENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)

def load_mods():
    try:
        with open(MODS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
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

async def event_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Меню выбора видимости и выдачи прав
    query = update.callback_query
    await query.answer()
    buttons = [
        [InlineKeyboardButton("🌍 Событие для всех", callback_data="public_event")],
        [InlineKeyboardButton("👤 Только для меня", callback_data="private_event")]
    ]
    # добавляем пункт выдачи прав только если сам пользователь — модератор
    user = update.effective_user.first_name
    if user in moderators:
        buttons.append([InlineKeyboardButton("🎖 Выдать модератора", callback_data="promote_user")])
    buttons.append([InlineKeyboardButton("🔁 Старт", callback_data="back_to_main")])
    await query.edit_message_text("Выберите тип события:", reply_markup=InlineKeyboardMarkup(buttons))

async def view_calendar(update: Update, context: ContextTypes.DEFAULT_TYPE, period="month"):
    query = update.callback_query
    await query.answer()
    now = datetime.now()
    user = update.effective_user.first_name
    filtered = []
    for ev in events:
        try:
            d = datetime.strptime(ev['date'], "%Y.%m.%d")
        except:
            continue
        visible = (ev.get('visibility') == "public") or (ev['user'] == user)
        if not visible:
            continue
        if period == "week" and now <= d <= now + timedelta(weeks=1):
            filtered.append((d, ev))
        elif period == "month" and now.month == d.month and now.year == d.year:
            filtered.append((d, ev))
        elif period == "year" and now.year == d.year:
            filtered.append((d, ev))
    filtered.sort(key=lambda x: x[0])
    keyboard = []
    for _, ev in filtered:
        btn = f"{ev['color']} {ev['date']} — {ev['title']} ({ev['user']})"
        keyboard.append([InlineKeyboardButton(btn, callback_data=f"select_{events.index(ev)}")])
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
    ev = events[idx]
    user = update.effective_user.first_name
    text = f"{ev['color']} {ev['date']}\n{ev['title']} ({ev['user']})"
    if ev.get('comments'):
        text += "\n💬 Комментарии:\n" + "\n".join(f"- {c}" for c in ev['comments'])
    buttons = [[InlineKeyboardButton("💬 Комментировать", callback_data="comment_event")]]
    # можно редактировать/удалять свое или чужое если ты модератор
    if ev['user'] == user or user in moderators:
        buttons.insert(0, [InlineKeyboardButton("✏️ Редактировать", callback_data="edit_event")])
        buttons.append([InlineKeyboardButton("🗑 Удалить", callback_data="remove_event")])
    buttons.append([InlineKeyboardButton("🔁 Старт", callback_data="back_to_main")])
    await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(buttons))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.callback_query.data
    if data == "view_calendar":
        return await view_calendar(update, context)
    if data == "event_menu":
        return await event_menu(update, context)
    if data == "back_to_main":
        return await start(update.callback_query, context)
    if data.startswith("period_"):
        return await view_calendar(update, context, data.split("_")[1])
    if data.startswith("select_"):
        return await select_event(update, context)
    if data in ("public_event","private_event"):
        context.user_data['visibility'] = "public" if data=="public_event" else "private"
        await update.callback_query.edit_message_text("Введите: дата (ГГГГ.ММ.ДД) название события")
        return ADDING
    if data == "comment_event":
        await update.callback_query.edit_message_text("Введите комментарий:")
        return COMMENTING
    if data == "edit_event":
        await update.callback_query.edit_message_text("Введите новую дату и название:")
        return EDITING
    if data == "remove_event":
        await update.callback_query.edit_message_text("Напишите 'да' для удаления'")
        return REMOVING
    if data == "promote_user":
        user = update.effective_user.first_name
        if user in moderators:
            await update.callback_query.edit_message_text("Введите имя для повышения:")
            return PROMOTING
        else:
            await update.callback_query.edit_message_text("Только модератор может назначать.")
            return ConversationHandler.END

async def add_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    parts = text.split(" ",1)
    if len(parts)<2:
        await update.message.reply_text("Ошибка. Формат: дата название", reply_markup=main_menu())
        return ConversationHandler.END
    date, title = parts
    user = update.effective_user.first_name
    vis = context.user_data.get('visibility',"public")
    color = "🟣" if vis=="private" else "🔵"
    events.append({"user":user,"title":title,"date":date,"color":color,"comments":[],"visibility":vis})
    save_events(events)
    await update.message.reply_text("Событие добавлено!", reply_markup=main_menu())
    return ConversationHandler.END

async def comment_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    idx = context.user_data.get('selected_event')
    if idx is None:
        return ConversationHandler.END
    comment = update.message.text.strip()
    user = update.effective_user.first_name
    events[idx].setdefault('comments',[]).append(f"{user}: {comment}")
    save_events(events)
    await update.message.reply_text("Комментарий добавлен.", reply_markup=main_menu())
    return ConversationHandler.END

async def edit_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    idx = context.user_data.get('selected_event')
    parts = update.message.text.strip().split(" ",1)
    if len(parts)<2:
        await update.message.reply_text("Ошибка. Формат: дата новое_название", reply_markup=main_menu())
        return ConversationHandler.END
    date, title = parts
    user = update.effective_user.first_name
    ev = events[idx]
    if ev['user']!=user and user not in moderators:
        await update.message.reply_text("Нет прав.", reply_markup=main_menu())
    else:
        ev['date'], ev['title'] = date, title
        save_events(events)
        await update.message.reply_text("Событие обновлено.", reply_markup=main_menu())
    return ConversationHandler.END

async def remove_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    idx = context.user_data.get('selected_event')
    user = update.effective_user.first_name
    ev = events[idx]
    if ev['user']!=user and user not in moderators:
        await update.message.reply_text("Нет прав.", reply_markup=main_menu())
    else:
        if update.message.text.strip().lower()=="да":
            events.pop(idx)
            save_events(events)
            await update.message.reply_text("Удалено.", reply_markup=main_menu())
        else:
            await update.message.reply_text("Отменено.", reply_markup=main_menu())
    return ConversationHandler.END

async def promote_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_mod = update.message.text.strip()
    user = update.effective_user.first_name
    if user in moderators:
        if new_mod not in moderators:
            moderators.append(new_mod)
            save_mods(moderators)
            await update.message.reply_text(f"{new_mod} теперь модератор.", reply_markup=main_menu())
        else:
            await update.message.reply_text(f"{new_mod} уже модератор.", reply_markup=main_menu())
    else:
        await update.message.reply_text("Нет прав.", reply_markup=main_menu())
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Отменено.", reply_markup=main_menu())
    return ConversationHandler.END

if __name__=="__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler)],
        states={
            ADDING: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_event)],
            COMMENTING: [MessageHandler(filters.TEXT & ~filters.COMMAND, comment_event)],
            EDITING: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_event)],
            REMOVING: [MessageHandler(filters.TEXT & ~filters.COMMAND, remove_event)],
            PROMOTING: [MessageHandler(filters.TEXT & ~filters.COMMAND, promote_user)],
            SELECTING: [CallbackQueryHandler(button_handler)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv)
    app.run_polling()