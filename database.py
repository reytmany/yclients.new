from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Table, create_engine, event
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timedelta

Base = declarative_base()

# Настройка подключения к базе данных
DATABASE_URL = "sqlite:///database.db"  # Укажите путь к базе данных
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Функция для инициализации базы данных
def init_db(database_url: str = DATABASE_URL):
    """Инициализация базы данных."""
    global engine, SessionLocal
    engine = create_engine(database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Ассоциативная таблица для услуг, предоставляемых мастером
master_service_association = Table(
    'master_service_association', Base.metadata,
    Column('master_id', Integer, ForeignKey('masters.id')),
    Column('service_id', Integer, ForeignKey('services.id'))
)


class User(Base):   # Модель клиента
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    telegram_id = Column(String, unique=True)  # Идентификатор пользователя в Telegram
    name = Column(String)
    phone = Column(String)

    # Отношение с записями на приём (Appointment)
    appointments = relationship('Appointment', back_populates='user')

    # Отношение с отзывами (Review)
    reviews = relationship('Review', back_populates='user')

    # Отношение с состоянием пользователя
    state = relationship('UserState', uselist=False, back_populates='user')


class UserState(Base):
    __tablename__ = 'user_states'
    user_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    current_state = Column(String)
    previous_state = Column(String)
    data = Column(String)  # Дополнительные данные, если нужны

    # Отношение с пользователем
    user = relationship('User', back_populates='state')


class Master(Base):  # Модель мастера
    __tablename__ = 'masters'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    experience = Column(Integer)  # Опыт работы в годах
    rating = Column(Float, default=0.0)  # Средний рейтинг мастера

    # Связь с услугами через ассоциативную таблицу
    services = relationship('Service', secondary=master_service_association, back_populates='masters')

    # Отношение с временными слотами (TimeSlot)
    timeslots = relationship('TimeSlot', back_populates='master')

    # Отношение с отзывами (Review)
    reviews = relationship('Review', back_populates='master')

    # Дополнительное поле для идентификатора в Telegram (для уведомлений)
    telegram_id = Column(String, unique=True)


class Admin(Base):  # Модель администратора
    __tablename__ = 'admins'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    password_hash = Column(String)  # Хэш пароля администратора


class Service(Base):  # Модель услуги
    __tablename__ = 'services'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    duration = Column(Integer)  # Длительность услуги в минутах
    cost = Column(Float)  # Стоимость услуги

    # Связь с мастерами через ассоциативную таблицу
    masters = relationship('Master', secondary=master_service_association, back_populates='services')


class TimeSlot(Base):  # Модель временного слота
    __tablename__ = 'timeslots'

    id = Column(Integer, primary_key=True)
    master_id = Column(Integer, ForeignKey('masters.id'), nullable=True)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    status = Column(String)  # Возможные значения: 'free', 'booked', 'not_working'
    day = Column(Integer)
    month = Column(Integer)

    # Отношение с мастером
    master = relationship('Master', back_populates='timeslots')

    # Отношение с записью на приём (Appointment)
    appointment = relationship('Appointment', back_populates='timeslot', uselist=False)

    # Автоматическое обновление полей day и month при добавлении или обновлении TimeSlot
    @staticmethod
    def set_day_month(mapper, connection, target):
        if target.start_time:
            target.day = target.start_time.day
            target.month = target.start_time.month

# События для автоматического заполнения day и month перед вставкой и обновлением
event.listen(TimeSlot, 'before_insert', TimeSlot.set_day_month)
event.listen(TimeSlot, 'before_update', TimeSlot.set_day_month)


class Appointment(Base):  # Модель записи на приём
    __tablename__ = 'appointments'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    master_id = Column(Integer, ForeignKey('masters.id'), nullable=True)
    service_id = Column(Integer, ForeignKey('services.id'))
    timeslot_id = Column(Integer, ForeignKey('timeslots.id'))
    status = Column(String)  # Возможные значения: 'scheduled', 'completed', 'cancelled'

    # Отношение с пользователем
    user = relationship('User', back_populates='appointments')

    # Отношение с мастером
    master = relationship('Master')

    # Отношение с услугой
    service = relationship('Service')

    # Отношение с временным слотом
    timeslot = relationship('TimeSlot', back_populates='appointment')


class Review(Base):  # Модель отзыва
    __tablename__ = 'reviews'

    id = Column(Integer, primary_key=True)
    master_id = Column(Integer, ForeignKey('masters.id'))
    user_id = Column(Integer, ForeignKey('users.id'))
    rating = Column(Integer)  # Оценка мастера (от 1 до 5)
    comment = Column(String)  # Текстовый отзыв пользователя

    # Отношение с мастером
    master = relationship('Master', back_populates='reviews')

    # Отношение с пользователем
    user = relationship('User', back_populates='reviews')