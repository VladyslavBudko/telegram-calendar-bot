# debug_env.py

import os
from dotenv import load_dotenv

# Загружаем переменные из .env файла
load_dotenv()

# Пытаемся получить значение переменной MONGO_URI
mongo_uri = os.getenv("MONGO_URI")

# Печатаем результат
print("MONGO_URI:", mongo_uri if mongo_uri else "⛔ Не найдена! Проверь .env файл")