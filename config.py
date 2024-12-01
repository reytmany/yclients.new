#config.py

API_TOKEN = '7576874796:AAHuxsjia58-Zge-AlxE_5Zd-cPJhSlawyM'

import os

# Получаем значение из переменных окружения или используем дефолтное значение
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///project.db")  # Для реальной базы данных
TEST_DATABASE_URL = "sqlite:///test_database.db"  # Для тестовой базы данных


'''
python3 tests/test_bd.py
export TEST_MODE=True
export TEST_MODE=False
python3 bot.py
python3 test_data.py
'''