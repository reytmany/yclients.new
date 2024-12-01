from sqlalchemy import create_engine
from database import Base

# Создаём подключение к базе данных
engine = create_engine('sqlite:///database.db')

# Создаём все таблицы в базе данных
Base.metadata.create_all(engine)