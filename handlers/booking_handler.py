from aiogram import Router, F
from database import SessionLocal, Appointment, User, TimeSlot, TimeSlotStatus
from sqlalchemy.orm import joinedload
from states import BookingStates

router = Router()

from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database import SessionLocal, TimeSlot, Master, master_service_association, TimeSlotStatus
from datetime import datetime, timedelta
from aiogram.fsm.context import FSMContext
from utils.calendar import find_available_slots
import logging

@router.callback_query(F.data.startswith("date_"))
async def date_selected_handler(callback_query: CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    logging.info(f"Handling date selection for user_id {user_id}")

    # Получение данных из FSMContext
    booking_data = await state.get_data()

    if not booking_data:
        logging.error(f"Booking data not found for user_id {user_id}")
        await callback_query.message.edit_text(
            "Ошибка: данные записи не найдены. Пожалуйста, начните заново.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="Назад в меню", callback_data="back_to_menu")]
                ]
            )
        )
        return

    # Извлечение данных из callback_data
    data_parts = callback_query.data.split("_")
    try:
        date_iso = data_parts[1]
        week_offset = int(data_parts[2])
        selected_date = datetime.fromisoformat(date_iso).date()
        logging.info(f"Selected date: {selected_date}, week_offset: {week_offset}")
    except Exception as e:
        logging.error(f"Error parsing date data for user_id {user_id}: {e}")
        await callback_query.message.edit_text("Ошибка обработки даты.")
        return

    # Данные из FSMContext
    master_id = booking_data.get("master_id")
    service_id = booking_data.get("service_id")
    service_duration = booking_data.get("service_duration")

    start_datetime = datetime.combine(selected_date, datetime.min.time())
    end_datetime = start_datetime + timedelta(days=1)

    # Поиск доступных слотов
    with SessionLocal() as session:
        try:
            if master_id is None:
                masters = session.query(Master).join(master_service_association).filter(
                    master_service_association.c.service_id == service_id
                ).all()
                master_ids = [master.id for master in masters]
            else:
                master_ids = [master_id]
            available_slots = []
            for master_id in master_ids:
                print(master_id)
                all_slots = session.query(TimeSlot).filter(
                    TimeSlot.master_id == master_id,
                    TimeSlot.start_time >= start_datetime,
                    TimeSlot.start_time < end_datetime,
                    TimeSlot.status == TimeSlotStatus.free
                ).order_by(TimeSlot.start_time).all()

            for slot in find_available_slots(all_slots, service_duration):
                available_slots.append(slot)

            logging.info(f"Found {len(available_slots)} available slots for user_id {user_id}")
        except Exception as e:
            logging.error(f"Error fetching slots for user_id {user_id}: {e}")
            await callback_query.message.edit_text("Ошибка при загрузке доступных слотов.")
            return

    if not available_slots:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Назад", callback_data=f"change_week_{week_offset}")],
                [InlineKeyboardButton(text="Назад в меню", callback_data="back_to_menu")],
            ]
        )
        await callback_query.message.edit_text("Нет доступных слотов на эту дату.", reply_markup=keyboard)
        return

    # Формирование клавиатуры с доступными слотами
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=f"{slot.start_time.strftime('%H:%M')} ({slot.master.name})",
                callback_data=f"slot_{slot.id}"
            )]
            for slot in available_slots
        ] + [
            [InlineKeyboardButton(text="Назад", callback_data=f"change_week_{week_offset}")],
            [InlineKeyboardButton(text="Назад в меню", callback_data="back_to_menu")],
        ]
    )

    await callback_query.message.edit_text("Выберите время:", reply_markup=keyboard)



@router.callback_query(F.data.startswith("slot_"))
async def confirm_booking_handler(callback_query: CallbackQuery, state: FSMContext):
    slot_id = int(callback_query.data.split("_")[1])

    with SessionLocal() as session:
        slot = session.query(TimeSlot).options(joinedload(TimeSlot.master)).filter(TimeSlot.id == slot_id).first()

    await state.update_data(slot_id=slot_id, slot_time=slot.start_time, master_id=slot.master.id)

    data = await state.get_data()
    service_name = data["service_name"]
    slot_time = slot.start_time.strftime('%Y-%m-%d %H:%M')
    week_offset = data.get("week_offset", 0)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Подтверждаю", callback_data="confirm_booking")],
            [InlineKeyboardButton(text="Назад", callback_data="previous_step")],
            [InlineKeyboardButton(text="Назад в меню", callback_data="back_to_menu")],
        ]
    )
    await state.set_state(BookingStates.confirming)
    await callback_query.message.edit_text(
        f"Вы хотите записаться на:\nУслуга: {service_name}\nВремя: {slot_time}\nВсе верно?",
        reply_markup=keyboard
    )



@router.callback_query(F.data == "confirm_booking")
async def save_booking(callback_query: CallbackQuery, state: FSMContext):
    # Получение данных из состояния FSM
    data = await state.get_data()

    service_id = data.get("service_id")
    master_id = data.get("master_id")
    slot_id = data.get("slot_id")
    service_duration = data.get("service_duration")

    # Проверка на неполноту данных
    if not service_id or not master_id or not slot_id or not service_duration:
        await callback_query.message.edit_text(
            "Ошибка: данные записи неполны. Пожалуйста, начните заново.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="Назад в меню", callback_data="back_to_menu")]
                ]
            )
        )
        return

    with SessionLocal() as session:
        # Проверяем наличие слота
        slot = session.query(TimeSlot).filter(TimeSlot.id == slot_id).first()
        if not slot or slot.status != TimeSlotStatus.free:
            await callback_query.message.edit_text(
                "Извините, выбранное время больше недоступно.",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="Назад", callback_data="back_to_menu")]
                    ]
                )
            )
            return

        # Бронируем слоты
        required_slots = service_duration // 15
        slots_to_book = session.query(TimeSlot).filter(
            TimeSlot.master_id == master_id,
            TimeSlot.start_time >= slot.start_time,
            TimeSlot.start_time < slot.start_time + timedelta(minutes=service_duration),
            TimeSlot.status == TimeSlotStatus.free
        ).order_by(TimeSlot.start_time).all()

        if len(slots_to_book) < required_slots:
            await callback_query.message.edit_text(
                "Извините, выбранное время больше недоступно.",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="Назад в меню", callback_data="back_to_menu")]
                    ]
                )
            )
            return

        for s in slots_to_book:
            s.status = TimeSlotStatus.booked

        # Проверяем, существует ли пользователь
        user_id = callback_query.from_user.id
        user = session.query(User).filter(User.telegram_id == str(user_id)).first()
        if not user:
            user = User(telegram_id=str(user_id))
            session.add(user)
            session.commit()

        # Создаем запись на прием
        appointment = Appointment(
            user_id=user.id,
            master_id=master_id,
            service_id=service_id,
            timeslot_id=slot.id,
            status="scheduled"
        )
        session.add(appointment)

        # Фиксируем изменения
        session.commit()

        # Подготовка сообщения о подтверждении
        confirmation_message = (
            f"Вы успешно записаны на:\n"
            f"Дата: {slot.start_time.strftime('%Y-%m-%d %H:%M')}\n"
            f"Услуга: {data['service_name']}\n"
            f"Мастер: {slot.master.name}"
        )

    # Отправляем сообщение пользователю
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Назад в меню", callback_data="back_to_menu")]
        ]
    )
    await state.clear()
    await callback_query.message.edit_text(confirmation_message, reply_markup=keyboard)
    slot_time = data["slot_time"]
    service_name = data["service_name"]
    await state.update_data(slot_time=slot.start_time, service_name=data["service_name"], service_duration=data["service_duration"])
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Добавить в календарь", callback_data="add_to_calendar")],
            [InlineKeyboardButton(text="Назад в меню", callback_data="back_to_menu")],
        ]
    )
    await callback_query.message.edit_text(
        f"Вы успешно записались на:\n"
        f"Услуга: {service_name}\n"
        f"Время: {slot_time.strftime('%Y-%m-%d %H:%M')}\n"
        f"Вы хотите добавить запись в календарь?",
        reply_markup=keyboard
    )


from icalendar import Calendar, Event
from aiogram.types import FSInputFile
from io import BytesIO

from urllib.parse import urlencode

@router.callback_query(F.data == "add_to_calendar")
async def add_to_calendar(callback_query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    slot_time = data.get("slot_time")
    service_name = data.get("service_name")
    service_duration = data.get("service_duration")

    if not slot_time or not service_name:
        await callback_query.message.edit_text("Ошибка: данные записи неполные. Пожалуйста, начните заново.")
        return

    # Генерация ссылки на Google Calendar
    start_time = slot_time.strftime("%Y%m%dT%H%M%S")
    end_time = (slot_time + timedelta(minutes=service_duration)).strftime("%Y%m%dT%H%M%S")
    query = urlencode({
        "action": "TEMPLATE",
        "text": f"Запись на услугу: {service_name}",
        "dates": f"{start_time}/{end_time}",
        "details": f"Вы записаны на {service_name} в {slot_time.strftime('%H:%M')}.",
        "trp": "false",
    })
    calendar_link = f"https://www.google.com/calendar/render?{query}"

    # Отправка ссылки пользователю
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Добавить в Google Calendar", url=calendar_link)],
            [InlineKeyboardButton(text="Назад в меню", callback_data="back_to_menu")],
        ]
    )
    await callback_query.message.edit_text("Добавьте запись в ваш календарь:", reply_markup=keyboard)
