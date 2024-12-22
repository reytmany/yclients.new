from datetime import datetime, timedelta
from sqlalchemy.orm import sessionmaker
from database import (
    Base, Service, Master, TimeSlot, Appointment, Review, Admin,
    master_service_association, TimeSlotStatus, AppointmentStatus
)
from sqlalchemy import create_engine

# Настройка подключения к базе данных
engine = create_engine("sqlite:///database.db", echo=False)
SessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(engine)


def setup_test_data():
    with SessionLocal() as session:
        # Очистка таблиц
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
        master1 = Master(name="Марина", login="marina", password="pass123", rating=4.5, telegram_id="@marina")
        master1.services.extend([service1])

        master2 = Master(name="Анна", login="anna", password="pass123", rating=4.0, telegram_id="@anna")
        master2.services.extend([service2, service3])

        master3 = Master(name="Яна", login="yana", password="pass123", rating=4.3, telegram_id="@yana")
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
        admin = Admin(name="Администратор", login="admin", password="admin123")
        session.add(admin)
        session.commit()

        print("Тестовые данные успешно созданы.")


if __name__ == "__main__":
    setup_test_data()
