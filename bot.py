import asyncio
import logging
import sys
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, Router, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from config import API_TOKEN
from database import SessionLocal, Service, Master, TimeSlot, User, Appointment
from sqlalchemy.orm import joinedload

# Настройка логгера
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

# Создание объекта бота
bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
router = Router()

# Хранение временных данных о записи пользователя
user_booking_data = {}


# Обработчик первого взаимодействия
@router.message(F.text == "/start")
async def first_interaction(message: Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Старт", callback_data="start")],
        ]
    )
    await message.answer("Добро пожаловать! Нажмите 'Старт', чтобы начать.", reply_markup=keyboard)


# Обработчик кнопки "Старт"
@router.callback_query(F.data == "start")
async def start_handler(callback_query: CallbackQuery):
    await send_main_menu(callback_query.message)


# Функция для отправки главного меню
async def send_main_menu(message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Посмотреть услуги", callback_data="services")],
            [InlineKeyboardButton(text="Мои записи", callback_data="my_bookings")],
        ]
    )
    await message.edit_text("Выберите действие:", reply_markup=keyboard)


# Обработчик команды "Посмотреть услуги"
@router.callback_query(F.data == "services")
async def services_handler(callback_query: CallbackQuery):
    with SessionLocal() as session:
        services = session.query(Service).all()

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=f"{service.name} - {service.cost} руб.", callback_data=f"service_{service.id}")]
                for service in services
            ] + [
                [InlineKeyboardButton(text="Назад в меню", callback_data="back_to_menu")],
            ]
        )
    await callback_query.message.edit_text("Выберите услугу:", reply_markup=keyboard)


# Обработчик кнопки "Назад в меню"
@router.callback_query(F.data == "back_to_menu")
async def back_to_menu_handler(callback_query: CallbackQuery):
    await send_main_menu(callback_query.message)


# Обработчик выбора услуги
@router.callback_query(F.data.startswith("service_"))
async def select_service_handler(callback_query: CallbackQuery):
    service_id = int(callback_query.data.split("_")[1])
    with SessionLocal() as session:
        service = session.query(Service).filter(Service.id == service_id).first()

    user_booking_data[callback_query.from_user.id] = {"service_id": service_id, "service_name": service.name}

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Выбрать мастера", callback_data="select_master")],
            [InlineKeyboardButton(text="Выбрать время (мастер не важен)", callback_data="select_time_no_master")],
            [InlineKeyboardButton(text="Назад в меню", callback_data="back_to_menu")],
        ]
    )
    await callback_query.message.edit_text("Как вы хотите продолжить?", reply_markup=keyboard)


# Обработчик выбора мастера
@router.callback_query(F.data == "select_master")
async def select_master_handler(callback_query: CallbackQuery):
    with SessionLocal() as session:
        masters = session.query(Master).all()

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=master.name, callback_data=f"master_{master.id}")]
                for master in masters
            ] + [
                [InlineKeyboardButton(text="Назад в меню", callback_data="back_to_menu")],
            ]
        )
    await callback_query.message.edit_text("Выберите мастера:", reply_markup=keyboard)


# Обработчик выбора мастера
@router.callback_query(F.data.startswith("master_"))
async def show_calendar_for_master(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    master_id = int(callback_query.data.split("_")[1])
    user_booking_data[user_id]["master_id"] = master_id

    await show_calendar(callback_query.message, user_id, week_offset=0)


# Обработчик выбора времени без мастера
@router.callback_query(F.data == "select_time_no_master")
async def show_calendar_no_master(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    user_booking_data[user_id]["master_id"] = None  # Сбрасываем выбор мастера

    await show_calendar(callback_query.message, user_id, week_offset=0)


# Показ календаря
async def show_calendar(message, user_id, week_offset):
    today = datetime.now().date()
    start_of_week = today + timedelta(weeks=week_offset)
    dates = [start_of_week + timedelta(days=i) for i in range(7)]

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=date.strftime("%d %b %Y"), callback_data=f"date_{date.isoformat()}_{week_offset}")]
            for date in dates
        ] + [
            [InlineKeyboardButton(text="⬅️ Пред. неделя", callback_data=f"change_week_{week_offset - 1}"),
             InlineKeyboardButton(text="След. неделя ➡️", callback_data=f"change_week_{week_offset + 1}")],
            [InlineKeyboardButton(text="Назад в меню", callback_data="back_to_menu")],
        ]
    )
    await message.edit_text("Выберите дату:", reply_markup=keyboard)


# Обработчик выбора недели
@router.callback_query(F.data.startswith("change_week_"))
async def change_week_handler(callback_query: CallbackQuery):
    week_offset = int(callback_query.data.split("_")[2])
    user_id = callback_query.from_user.id

    await show_calendar(callback_query.message, user_id, week_offset)


# Обработчик выбора даты
@router.callback_query(F.data.startswith("date_"))
async def date_selected_handler(callback_query: CallbackQuery):
    data_parts = callback_query.data.split("_")
    date_iso = data_parts[1]
    week_offset = int(data_parts[2])
    selected_date = datetime.fromisoformat(date_iso).date()
    user_id = callback_query.from_user.id
    booking_data = user_booking_data.get(user_id)
    if not booking_data:
        await callback_query.message.answer("Ошибка: данные записи не найдены.")
        return
    master_id = booking_data.get("master_id")
    service_id = booking_data.get("service_id")

    with SessionLocal() as session:
        service = session.query(Service).filter(Service.id == service_id).first()
        if master_id:
            available_slots = session.query(TimeSlot).options(
                joinedload(TimeSlot.master)
            ).filter(
                TimeSlot.master_id == master_id,
                TimeSlot.start_time >= datetime.combine(selected_date, datetime.min.time()),
                TimeSlot.start_time < datetime.combine(selected_date + timedelta(days=1), datetime.min.time()),
                TimeSlot.status == 'free'
            ).all()
        else:
            available_slots = session.query(TimeSlot).options(
                joinedload(TimeSlot.master)
            ).filter(
                TimeSlot.start_time >= datetime.combine(selected_date, datetime.min.time()),
                TimeSlot.start_time < datetime.combine(selected_date + timedelta(days=1), datetime.min.time()),
                TimeSlot.status == 'free'
            ).all()

        if not available_slots:
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="Назад", callback_data=f"change_week_{week_offset}")],
                    [InlineKeyboardButton(text="Назад в меню", callback_data="back_to_menu")],
                ]
            )
            await callback_query.message.edit_text("Нет доступных слотов на эту дату.", reply_markup=keyboard)
            return

        # Формируем клавиатуру внутри контекста сессии
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(
                    text=f"{slot.start_time.strftime('%H:%M')} ({slot.master.name if slot.master else 'Любой'})",
                    callback_data=f"slot_{slot.id}"
                )]
                for slot in available_slots
            ] + [
                [InlineKeyboardButton(text="Назад", callback_data=f"change_week_{week_offset}")],
                [InlineKeyboardButton(text="Назад в меню", callback_data="back_to_menu")],
            ]
        )

    # Отправляем сообщение после закрытия сессии
    await callback_query.message.edit_text("Выберите время:", reply_markup=keyboard)


# Обработчик выбора времени
@router.callback_query(F.data.startswith("slot_"))
async def confirm_booking_handler(callback_query: CallbackQuery):
    slot_id = int(callback_query.data.split("_")[1])
    user_id = callback_query.from_user.id

    with SessionLocal() as session:
        slot = session.query(TimeSlot).options(joinedload(TimeSlot.master)).filter(TimeSlot.id == slot_id).first()
        user_booking_data[user_id]["slot_id"] = slot_id
        user_booking_data[user_id]["slot_time"] = slot.start_time

        master_name = slot.master.name if slot.master else "Любой"

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Подтверждаю", callback_data="confirm_booking")],
                [InlineKeyboardButton(text="Изменить запись", callback_data="change_booking")],
                [InlineKeyboardButton(text="Назад в меню", callback_data="back_to_menu")],
            ]
        )

        # Отправляем сообщение внутри сессии
        await callback_query.message.edit_text(
            f"Вы хотите записаться на:\n"
            f"Дата и время: <b>{slot.start_time.strftime('%Y-%m-%d %H:%M')}</b>\n"
            f"Услуга: <b>{user_booking_data[user_id]['service_name']}</b>\n"
            f"Мастер: <b>{master_name}</b>\n"
            f"Все верно?",
            reply_markup=keyboard
        )


# Обработчик подтверждения записи
@router.callback_query(F.data == "confirm_booking")
async def save_booking(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    booking_data = user_booking_data.get(user_id)

    if not booking_data:
        await callback_query.message.answer("Ошибка: данные записи не найдены.")
        return

    slot_id = booking_data.get("slot_id")
    if not slot_id:
        await callback_query.message.answer("Ошибка: выбранное время не найдено.")
        return

    service_id = booking_data.get("service_id")

    with SessionLocal() as session:
        slot = session.query(TimeSlot).filter(TimeSlot.id == slot_id).first()

        if slot.status != 'free':
            await callback_query.message.answer("Извините, это время уже занято.")
            return

        slot.status = "booked"

        # Получаем или создаем пользователя
        user = session.query(User).filter(User.telegram_id == str(user_id)).first()
        if not user:
            user = User(telegram_id=str(user_id))
            session.add(user)
            session.commit()

        # Создаем запись на прием
        appointment = Appointment(
            user_id=user.id,
            master_id=slot.master_id,
            service_id=service_id,
            timeslot_id=slot.id,
            status='scheduled'
        )
        session.add(appointment)
        session.commit()

    # Клавиатура с опциями после подтверждения
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Вернуться в меню", callback_data="back_to_menu")],
            [InlineKeyboardButton(text="Мои записи", callback_data="my_bookings")],
        ]
    )

    await callback_query.message.edit_text(
        f"Спасибо! Ваша запись подтверждена:\nДата: {booking_data['slot_time'].strftime('%Y-%m-%d %H:%M')}\n"
        f"Услуга: {booking_data['service_name']}",
        reply_markup=keyboard
    )


# Обработчик кнопки "Мои записи"
@router.callback_query(F.data == "my_bookings")
async def my_bookings_handler(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id

    with SessionLocal() as session:
        user = session.query(User).filter(User.telegram_id == str(user_id)).first()
        if not user:
            await callback_query.message.edit_text(
                "У вас пока нет активных записей.",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="Назад в меню", callback_data="back_to_menu")],
                    ]
                )
            )
            return

        # Загружаем связанные объекты с помощью joinedload
        bookings = session.query(Appointment).options(
            joinedload(Appointment.timeslot).joinedload(TimeSlot.master),
            joinedload(Appointment.service),
            joinedload(Appointment.master)
        ).filter(Appointment.user_id == user.id).all()

        if not bookings:
            await callback_query.message.edit_text(
                "У вас пока нет активных записей.",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="Назад в меню", callback_data="back_to_menu")],
                    ]
                )
            )
            return

        booking_details = "\n".join(
            f"- {booking.timeslot.start_time.strftime('%Y-%m-%d %H:%M')} | {booking.service.name} | Мастер: {booking.master.name if booking.master else 'Любой'}"
            for booking in bookings
        )

    await callback_query.message.edit_text(
        f"Ваши записи:\n{booking_details}",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Назад в меню", callback_data="back_to_menu")],
            ]
        )
    )


# Регистрация роутеров
dp.include_router(router)

# Основная функция
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
