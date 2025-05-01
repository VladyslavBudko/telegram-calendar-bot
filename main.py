import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)
import telegram

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")

client = AsyncIOMotorClient(MONGO_URI)
db = client["calendar_bot"]
events_collection = db["events"]
mods_collection = db["moderators"]

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

async def is_moderator(user: str) -> bool:
    return await mods_collection.find_one({"user": user}) is not None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Выберите действие:", reply_markup=main_menu())

async def view_calendar(update: Update, context: ContextTypes.DEFAULT_TYPE, period="month"):
    query = update.callback_query
    try:
        await query.answer()
    except telegram.error.BadRequest as e:
        if "Query is too old" not in str(e):
            raise

    now = datetime.now()
    user = update.effective_user.first_name
    raw_events = await events_collection.find().to_list(length=None)
    filtered = []
    for ev in raw_events:
        try:
            d = datetime.strptime(ev["date"], "%Y.%m.%d")
        except:
            continue
        if ev["visibility"] != "public" and ev["user"] != user:
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
        label = f"{ev['color']} {ev['date']} — {ev['title']} ({ev['user']})"
        keyboard.append([InlineKeyboardButton(label, callback_data=f"select_{ev['_id']}")])
    keyboard += period_buttons()
    try:
        await query.edit_message_text("🗓️ События:", reply_markup=InlineKeyboardMarkup(keyboard))
    except telegram.error.BadRequest as e:
        if "Message is not modified" not in str(e):
            raise

async def event_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except telegram.error.BadRequest:
        pass

    user = update.effective_user.first_name
    buttons = [
        [InlineKeyboardButton("🌍 Событие для всех", callback_data="public_event")],
        [InlineKeyboardButton("👤 Только для меня", callback_data="private_event")]
    ]
    if await is_moderator(user):
        buttons.append([InlineKeyboardButton("🎖 Выдать модератора", callback_data="promote_user")])
    buttons.append([InlineKeyboardButton("🔁 Старт", callback_data="back_to_main")])
    await query.edit_message_text("Выберите тип события:", reply_markup=InlineKeyboardMarkup(buttons))

async def select_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except telegram.error.BadRequest:
        pass

    event_id = query.data.split("_")[1]
    context.user_data["selected_event"] = event_id
    e = await events_collection.find_one({"_id": ObjectId(event_id)})
    if not e:
        await query.edit_message_text("Событие не найдено.")
        return

    text = f"{e['color']} {e['date']}\n{e['title']} ({e['user']})"
    if e.get("comments"):
        text += "\n💬 Комментарии:\n" + "\n".join(f"- {c}" for c in e["comments"])

    user = update.effective_user.first_name
    buttons = [[InlineKeyboardButton("💬 Комментировать", callback_data="comment_event")]]
    if e["user"] == user or await is_moderator(user):
        buttons.insert(0, [InlineKeyboardButton("✏️ Редактировать", callback_data="edit_event")])
        buttons.append([InlineKeyboardButton("🗑 Удалить", callback_data="remove_event")])
    buttons.append([InlineKeyboardButton("🔁 Старт", callback_data="back_to_main")])
    await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(buttons))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

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
    if data in ("public_event", "private_event"):
        context.user_data["visibility"] = "public" if data == "public_event" else "private"
        await query.edit_message_text("Введите: дата (ГГГГ.ММ.ДД) название события")
        return ADDING
    if data == "comment_event":
        await query.edit_message_text("Введите комментарий:")
        return COMMENTING
    if data == "edit_event":
        await query.edit_message_text("Введите новую дату и название:")
        return EDITING
    if data == "remove_event":
        await query.edit_message_text("Введите 'да', чтобы удалить:")
        return REMOVING
    if data == "promote_user":
        await query.edit_message_text("Введите имя нового модератора:")
        return PROMOTING

async def add_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        date, title = update.message.text.strip().split(" ", 1)
        user = update.effective_user.first_name
        visibility = context.user_data.get("visibility", "public")
        event = {
            "user": user,
            "title": title,
            "date": date,
            "color": "🔵" if visibility == "public" else "🟣",
            "comments": [],
            "visibility": visibility
        }
        await events_collection.insert_one(event)
        await update.message.reply_text("Событие добавлено!", reply_markup=main_menu())
    except:
        await update.message.reply_text("Ошибка. Формат: дата (ГГГГ.ММ.ДД) название", reply_markup=main_menu())
    return ConversationHandler.END

async def comment_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    comment = update.message.text.strip()
    user = update.effective_user.first_name
    event_id = context.user_data.get("selected_event")
    if event_id:
        await events_collection.update_one(
            {"_id": ObjectId(event_id)},
            {"$push": {"comments": f"{user}: {comment}"}}
        )
        await update.message.reply_text("Комментарий добавлен.", reply_markup=main_menu())
    return ConversationHandler.END

async def edit_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    event_id = context.user_data.get("selected_event")
    user = update.effective_user.first_name
    try:
        new_date, new_title = update.message.text.strip().split(" ", 1)
        event = await events_collection.find_one({"_id": ObjectId(event_id)})
        if not event:
            await update.message.reply_text("Событие не найдено.", reply_markup=main_menu())
            return ConversationHandler.END
        if event["user"] != user and not await is_moderator(user):
            await update.message.reply_text("Нет прав на редактирование.", reply_markup=main_menu())
            return ConversationHandler.END
        await events_collection.update_one(
            {"_id": ObjectId(event_id)},
            {"$set": {"date": new_date, "title": new_title}}
        )
        await update.message.reply_text("Событие обновлено.", reply_markup=main_menu())
    except:
        await update.message.reply_text("Ошибка редактирования.", reply_markup=main_menu())
    return ConversationHandler.END

async def remove_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    event_id = context.user_data.get("selected_event")
    user = update.effective_user.first_name
    event = await events_collection.find_one({"_id": ObjectId(event_id)})
    if not event:
        await update.message.reply_text("Событие не найдено.", reply_markup=main_menu())
        return ConversationHandler.END
    if event["user"] != user and not await is_moderator(user):
        await update.message.reply_text("Нет прав на удаление.", reply_markup=main_menu())
        return ConversationHandler.END
    if update.message.text.strip().lower() == "да":
        await events_collection.delete_one({"_id": ObjectId(event_id)})
        await update.message.reply_text("Удалено.", reply_markup=main_menu())
    else:
        await update.message.reply_text("Удаление отменено.", reply_markup=main_menu())
    return ConversationHandler.END

async def promote_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_mod = update.message.text.strip()
    user = update.effective_user.first_name
    if await is_moderator(user):
        await mods_collection.update_one(
            {"user": new_mod}, {"$set": {"user": new_mod}}, upsert=True
        )
        await update.message.reply_text(f"{new_mod} теперь модератор.", reply_markup=main_menu())
    else:
        await update.message.reply_text("Недостаточно прав.", reply_markup=main_menu())
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Действие отменено.", reply_markup=main_menu())
    return ConversationHandler.END

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler)],
        states={
            ADDING: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_event)],
            COMMENTING: [MessageHandler(filters.TEXT & ~filters.COMMAND, comment_event)],
            EDITING: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_event)],
            REMOVING: [MessageHandler(filters.TEXT & ~filters.COMMAND, remove_event)],
            PROMOTING: [MessageHandler(filters.TEXT & ~filters.COMMAND, promote_user)],
            SELECTING: [CallbackQueryHandler(button_handler)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=False  # ← для PTB > 20.0 (и чтобы убрать предупреждение)
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    app.run_polling()