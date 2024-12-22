from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Float, Table, event
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, Session
from sqlalchemy import create_engine
import enum
import json
import os
 
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
    duration = Column(Integer, nullable=False)
 
    masters = relationship('Master', secondary=master_service_association, back_populates='services')
    appointments = relationship("Appointment", back_populates="service")
 
    def __repr__(self):
        return f"<Service(id={self.id}, name='{self.name}', cost={self.cost}, duration={self.duration})>"
 
class Master(Base):
    __tablename__ = 'masters'
 
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    login = Column(String, nullable=False, unique=True)
    password = Column(String, nullable=False)
    telegram_id = Column(String, nullable=False, unique=True)
    total_rating = Column(Float, nullable=False, default=0)
    num_reviews = Column(Integer, nullable=False, default=0)
 
    services = relationship('Service', secondary=master_service_association, back_populates='masters')
    time_slots = relationship("TimeSlot", back_populates="master")
    appointments = relationship("Appointment", back_populates="master")
    reviews = relationship("Review", back_populates="master")
 
    @property
    def rating(self):
        return self.total_rating / self.num_reviews if self.num_reviews > 0 else 0
 
    def __repr__(self):
        return f"<Master(id={self.id}, name='{self.name}', login='{self.login}', rating={self.rating}, telegram_id='{self.telegram_id}')>"
 
class TimeSlotStatus(enum.Enum):
    free = 'free'
    booked = 'booked'
 
class TimeSlot(Base):
    __tablename__ = 'timeslots'
 
    id = Column(Integer, primary_key=True)
    master_id = Column(Integer, ForeignKey('masters.id'), nullable=False)
    start_time = Column(DateTime, nullable=False)
    status = Column(Enum(TimeSlotStatus), default=TimeSlotStatus.free, nullable=False)
 
    master = relationship("Master", back_populates="time_slots")
    appointment = relationship("Appointment", back_populates="timeslot", uselist=False)
 
    def __repr__(self):
        return f"<TimeSlot(id={self.id}, master_id={self.master_id}, start_time={self.start_time}, status='{self.status.value}')>"
 
class User(Base):
    __tablename__ = 'users'
 
    id = Column(Integer, primary_key=True)
    telegram_id = Column(String, nullable=False, unique=True)
 
    appointments = relationship("Appointment", back_populates="user")
    reviews = relationship("Review", back_populates="user")
 
    def __repr__(self):
        return f"<User(id={self.id}, telegram_id='{self.telegram_id}')>"
 
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
        return (
            f"<Appointment(id={self.id}, user_id={self.user_id}, master_id={self.master_id}, "
            f"service_id={self.service_id}, timeslot_id={self.timeslot_id}, status='{self.status.value}')>"
        )
 
class Review(Base):
    __tablename__ = 'reviews'
 
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    master_id = Column(Integer, ForeignKey('masters.id'), nullable=False)
    rating = Column(Float, nullable=False)
    review_text = Column(String, nullable=False)
 
    user = relationship("User", back_populates="reviews")
    master = relationship("Master", back_populates="reviews")
 
    def __repr__(self):
        return f"<Review(id={self.id}, user_id={self.user_id}, master_id={self.master_id}, rating={self.rating}, review_text='{self.review_text}')>"
 
class Admin(Base):
    __tablename__ = 'admins'
 
    id = Column(Integer, primary_key=True)  
    login = Column(String, nullable=False, unique=True)
    password = Column(String, nullable=False)
 
    def __repr__(self):
        return f"<Admin(id={self.id}, login='{self.login}')>"
 
def export_database(file_path='database_export.json'):
 
    directory = os.path.dirname(file_path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)
 
    data = {}
 
    with Session(engine) as session:
        services = session.query(Service).all()
        data['services'] = [
            {
                'id': service.id,
                'name': service.name,
                'cost': service.cost,
                'duration': service.duration
            }
            for service in services
        ]
 
        masters = session.query(Master).all()
        data['masters'] = [
            {
                'id': master.id,
                'name': master.name,
                'login': master.login,
                'password': master.password,
                'telegram_id': master.telegram_id,
                'total_rating': master.total_rating,
                'num_reviews': master.num_reviews,
                'rating': master.rating
            }
            for master in masters
        ]
 
        master_service_assoc = session.execute(master_service_association.select()).fetchall()
        data['master_service_association'] = [
            {
                'master_id': assoc.master_id,
                'service_id': assoc.service_id
            }
            for assoc in master_service_assoc
        ]
 
        timeslots = session.query(TimeSlot).all()
        data['timeslots'] = [
            {
                'id': slot.id,
                'master_id': slot.master_id,
                'start_time': slot.start_time.isoformat(),
                'status': slot.status.value
            }
            for slot in timeslots
        ]
 
        users = session.query(User).all()
        data['users'] = [
            {
                'id': user.id,
                'telegram_id': user.telegram_id
            }
            for user in users
        ]
 
        appointments = session.query(Appointment).all()
        data['appointments'] = [
            {
                'id': appointment.id,
                'user_id': appointment.user_id,
                'master_id': appointment.master_id,
                'service_id': appointment.service_id,
                'timeslot_id': appointment.timeslot_id,
                'status': appointment.status.value
            }
            for appointment in appointments
        ]
 
        reviews = session.query(Review).all()
        data['reviews'] = [
            {
                'id': review.id,
                'user_id': review.user_id,
                'master_id': review.master_id,
                'rating': review.rating,
                'review_text': review.review_text
            }
            for review in reviews
        ]
 
        admins = session.query(Admin).all()
        data['admins'] = [
            {
                'id': admin.id,
                'login': admin.login,
                'password': admin.password
            }
            for admin in admins
        ]
 
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
 
def update_master_rating(mapper, connection, target):
    master = target.master
    master.total_rating += target.rating
    master.num_reviews += 1
 
def delete_master_rating(mapper, connection, target):
    master = target.master
    master.total_rating -= target.rating
    master.num_reviews -= 1
 
event.listen(Review, 'after_insert', update_master_rating)
event.listen(Review, 'after_delete', delete_master_rating)
 
Base.metadata.create_all(engine)
