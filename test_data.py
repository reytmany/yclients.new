from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base, Service, Master, TimeSlot, Appointment, master_service_association

# Настройка подключения к базе данных
engine = create_engine("sqlite:///database.db")
SessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(engine)

def setup_test_data():
    with SessionLocal() as session:
        # Удаляем старые данные
        session.query(Appointment).delete()
        session.query(TimeSlot).delete()
        session.query(Master).delete()
        session.query(Service).delete()
        session.commit()

        # Создаем услуги
        service1 = Service(name="Укладка", duration=120, cost=2000)
        service2 = Service(name="Маникюр с покрытием", duration=90, cost=1800)
        session.add_all([service1, service2])
        session.commit()

        # Создаем мастеров и привязываем к услугам
        master1 = Master(name="Марина", experience=5, rating=4.5)
        master1.services.append(service1)  # Марина предоставляет услугу "Укладка"
        master2 = Master(name="Анна", experience=3, rating=4.0)
        master2.services.append(service2)  # Анна предоставляет услугу "Маникюр с покрытием"
        session.add_all([master1, master2])
        session.commit()

        # Добавляем временные слоты для мастеров на следующую неделю
        masters = session.query(Master).all()
        today = datetime.now()
        next_week_start = today + timedelta(days=(7 - today.weekday()))
        next_week_end = next_week_start + timedelta(days=6)

        for master in masters:
            current_date = next_week_start
            while current_date <= next_week_end:
                current_time = current_date.replace(hour=9, minute=0, second=0, microsecond=0)
                end_time = current_date.replace(hour=19, minute=0, second=0, microsecond=0)
                while current_time < end_time:
                    session.add(TimeSlot(
                        master_id=master.id,
                        start_time=current_time,
                        end_time=current_time + timedelta(minutes=30),
                        status="free"
                    ))
                    current_time += timedelta(minutes=30)
                current_date += timedelta(days=1)
        session.commit()

    print("Тестовые данные обновлены.")

if __name__ == "__main__":
    setup_test_data()
