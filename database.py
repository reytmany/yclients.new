from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Float, Table
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import enum


Base = declarative_base()


engine = create_engine('sqlite:///database.db', echo=False)


SessionLocal = sessionmaker(bind=engine)

master_service_association = Table(
    'master_service_association',
    Base.metadata,
    Column('master_id', Integer, ForeignKey('masters.id')),
    Column('service_id', Integer, ForeignKey('services.id'))
)

class Service(Base):
    __tablename__ = 'services'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    cost = Column(Integer, nullable=False)
    duration = Column(Integer, nullable=False)  # Duration in minutes

    masters = relationship('Master', secondary=master_service_association, back_populates='services')
    appointments = relationship("Appointment", back_populates="service")

    def __repr__(self):
        return f"<Service(id={self.id}, name={self.name}, cost={self.cost}, duration={self.duration})>"


class Master(Base):
    __tablename__ = 'masters'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    rating = Column(Float, nullable=False)

    services = relationship('Service', secondary=master_service_association, back_populates='masters')
    time_slots = relationship("TimeSlot", back_populates="master")
    appointments = relationship("Appointment", back_populates="master")

    def __repr__(self):
        return f"<Master(id={self.id}, name={self.name}, rating={self.rating})>"


class TimeSlotStatus(enum.Enum):
    free = 'free'
    booked = 'booked'


class TimeSlot(Base):
    __tablename__ = 'timeslots'

    id = Column(Integer, primary_key=True)
    master_id = Column(Integer, ForeignKey('masters.id'), nullable=False)  # Теперь nullable=False
    start_time = Column(DateTime, nullable=False)
    status = Column(Enum(TimeSlotStatus), default=TimeSlotStatus.free, nullable=False)

    master = relationship("Master", back_populates="time_slots")
    appointment = relationship("Appointment", back_populates="timeslot", uselist=False)

    def __repr__(self):
        return f"<TimeSlot(id={self.id}, master_id={self.master_id}, start_time={self.start_time}, status={self.status})>"


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(String, nullable=False, unique=True)

    appointments = relationship("Appointment", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, telegram_id={self.telegram_id})>"


class AppointmentStatus(enum.Enum):
    scheduled = 'scheduled'
    completed = 'completed'
    cancelled = 'cancelled'


class Appointment(Base):
    __tablename__ = 'appointments'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    master_id = Column(Integer, ForeignKey('masters.id'), nullable=False)
    service_id = Column(Integer, ForeignKey('services.id'), nullable=False)
    timeslot_id = Column(Integer, ForeignKey('timeslots.id'), nullable=False)
    status = Column(Enum(AppointmentStatus), default=AppointmentStatus.scheduled, nullable=False)

    user = relationship("User", back_populates="appointments")
    master = relationship("Master", back_populates="appointments")
    service = relationship("Service", back_populates="appointments")
    timeslot = relationship("TimeSlot", back_populates="appointment")

    def __repr__(self):
        return f"<Appointment(id={self.id}, user_id={self.user_id}, master_id={self.master_id}, service_id={self.service_id}, timeslot_id={self.timeslot_id}, status={self.status})>"


# Создаем таблицы в базе данных
Base.metadata.create_all(engine)


