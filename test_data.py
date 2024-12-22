from datetime import datetime, timedelta
from sqlalchemy.orm import sessionmaker
from database import (
    Base, Service, Master, TimeSlot, Appointment, Review, Admin,
    master_service_association, TimeSlotStatus, AppointmentStatus, User
)
from sqlalchemy import create_engine

# Настройка подключения к базе данных
engine = create_engine("sqlite:///database.db", echo=False)
SessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(engine)


def setup_test_data():
    with SessionLocal() as session:
        # Очистка таблиц, кроме пользователей
        session.query(Appointment).delete()
        session.query(TimeSlot).delete()
        session.query(master_service_association).delete()
        session.query(Master).delete()
        session.query(Service).delete()
        session.query(Review).delete()
        session.query(Admin).delete()
        session.commit()

        # Добавление услуг
        service1 = Service(name="Укладка", duration=120, cost=2000)  # 2 часа
        service2 = Service(name="Маникюр", duration=90, cost=1800)  # 1.5 часа
        service3 = Service(name="Педикюр", duration=60, cost=1500)  # 1 час
        session.add_all([service1, service2, service3])
        session.commit()

        # Добавление мастеров
        master1 = Master(name="Марина", login="master1", password="abcdefgh", telegram_id='1', total_rating=0,
                         num_reviews=0)
        master1.services.extend([service1])
        master2 = Master(name="Анна", login="master2", password="pass1234", telegram_id='23', total_rating=0,
                         num_reviews=0)
        master2.services.extend([service2, service3])
        master3 = Master(name="Яна", login="master3", password="123passw", telegram_id=916808487, total_rating=0,
                         num_reviews=0)
        master3.services.extend([service2, service3])
        session.add_all([master1, master2, master3])
        session.commit()

        # Генерация слотов для мастеров
        today = datetime.now()
        next_week_start = today - timedelta(days=(today.weekday()))
        next_week_end = next_week_start + timedelta(days=6)

        for master in session.query(Master).all():
            current_date = next_week_start
            while current_date <= next_week_end + timedelta(days=14):
                current_time = current_date.replace(hour=9, minute=0, second=0, microsecond=0)
                end_time = current_date.replace(hour=19, minute=0, second=0, microsecond=0)
                while current_time < end_time:
                    session.add(TimeSlot(
                        master_id=master.id,
                        start_time=current_time,
                        status=TimeSlotStatus.free
                    ))
                    current_time += timedelta(minutes=15)
                current_date += timedelta(days=1)
        session.commit()

        # Добавление администратора
        admin = Admin(login="admin", password="admin123")
        session.add(admin)
        session.commit()

        # Получение существующего пользователя
        user = session.query(User).filter(User.telegram_id == "916808487").first()
        if not user:
            print("Пользователь с ID 916808487 не найден!")
            return

        # Добавление завершённых процедур
        # Маникюр у Яны
        timeslot1 = TimeSlot(
            master_id=master3.id,
            start_time=datetime(2024, 12, 18, 14, 0),  # 18.12.2024 14:00
            status=TimeSlotStatus.booked
        )
        session.add(timeslot1)
        session.commit()

        appointment1 = Appointment(
            user_id=user.id,
            master_id=master3.id,
            service_id=service2.id,
            timeslot_id=timeslot1.id,
            status=AppointmentStatus.completed
        )
        session.add(appointment1)

        # Педикюр у Анны
        timeslot2 = TimeSlot(
            master_id=master2.id,
            start_time=datetime(2024, 12, 20, 10, 0),  # 20.12.2024 10:00
            status=TimeSlotStatus.booked
        )
        session.add(timeslot2)
        session.commit()

        appointment2 = Appointment(
            user_id=user.id,
            master_id=master2.id,
            service_id=service3.id,
            timeslot_id=timeslot2.id,
            status=AppointmentStatus.completed
        )
        session.add(appointment2)

        session.commit()

        print("Тестовые данные успешно созданы.")


if __name__ == "__main__":
    setup_test_data()
