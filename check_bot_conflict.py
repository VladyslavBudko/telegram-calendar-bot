import requests
import os

TOKEN = os.getenv("BOT_TOKEN") or "ВСТАВЬ_ТУТ_СВОЙ_ТОКЕН_ЕСЛИ_НЕ_ИСПОЛЬЗУЕШЬ_.env"

url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"

try:
    response = requests.get(url)
    data = response.json()

    if not data["ok"] and "Conflict" in data.get("description", ""):
        print("❌ Бот уже запущен где-то ещё (getUpdates занят)")
    elif data["ok"]:
        print("✅ Всё чисто. Бот не занят другим процессом")
        print(f"Обновления: {data['result']}")
    else:
        print("⚠️ Что-то пошло не так:", data)
except Exception as e:
    print("Ошибка при обращении к Telegram API:", e)