from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database import SessionLocal, TimeSlot, User, Appointment, TimeSlotStatus, Master, master_service_association
from datetime import timedelta, datetime
from utils.data_storage import user_booking_data
from aiogram import Router, F
from sqlalchemy.orm import joinedload

router = Router()

@router.callback_query(F.data.startswith("date_"))
async def date_selected_handler(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    data_parts = callback_query.data.split("_")

    try:
        date_iso = data_parts[1]
        week_offset = int(data_parts[2])
        selected_date = datetime.fromisoformat(date_iso).date()
    except Exception as e:
        await callback_query.message.edit_text("Ошибка обработки даты.")
        print(f"Error parsing date: {e}")
        return

    booking_data = user_booking_data.get(user_id)

    # Проверка данных записи
    if not booking_data:
        print(f"Ошибка: данные записи отсутствуют для user_id {user_id}")
        await callback_query.message.edit_text(
            "Ошибка: данные записи не найдены. Пожалуйста, начните заново.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="Назад в меню", callback_data="back_to_menu")]
                ]
            )
        )
        return

    master_id = booking_data.get("master_id")
    service_id = booking_data.get("service_id")
    service_duration = booking_data.get("service_duration")

    start_datetime = datetime.combine(selected_date, datetime.min.time())
    end_datetime = start_datetime + timedelta(days=1)

    with SessionLocal() as session:
        if master_id is None:
            masters = session.query(Master).join(master_service_association).filter(
                master_service_association.c.service_id == service_id).all()
            master_ids = [master.id for master in masters]
        else:
            master_ids = [master_id]

        all_slots = session.query(TimeSlot).filter(
            TimeSlot.master_id.in_(master_ids),
            TimeSlot.start_time >= start_datetime,
            TimeSlot.start_time < end_datetime,
            TimeSlot.status == TimeSlotStatus.free
        ).order_by(TimeSlot.start_time).all()

        available_slots = find_available_slots(all_slots, service_duration)

        if not available_slots:
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="Назад", callback_data=f"change_week_{week_offset}")],
                    [InlineKeyboardButton(text="Назад в меню", callback_data="back_to_menu")],
                ]
            )
            await callback_query.message.edit_text("Нет доступных слотов на эту дату.", reply_markup=keyboard)
            return

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
async def confirm_booking_handler(callback_query: CallbackQuery):
    slot_id = int(callback_query.data.split("_")[1])
    user_id = callback_query.from_user.id

    with SessionLocal() as session:
        slot = session.query(TimeSlot).options(joinedload(TimeSlot.master)).filter(TimeSlot.id == slot_id).first()
        if not slot:
            await callback_query.message.edit_text("Ошибка: слот не найден.")
            return

        user_booking_data[user_id].update({
            "slot_id": slot_id,
            "slot_time": slot.start_time,
            "master_id": slot.master_id
        })

        master_name = slot.master.name
        service_name = user_booking_data[user_id].get("service_name")
        week_offset = user_booking_data[user_id].get('week_offset', 0)

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Подтверждаю", callback_data="confirm_booking")],
                [InlineKeyboardButton(text="Назад", callback_data=f"date_{slot.start_time.date().isoformat()}_{week_offset}")],
                [InlineKeyboardButton(text="Назад в меню", callback_data="back_to_menu")],
            ]
        )

        await callback_query.message.edit_text(
            f"Вы хотите записаться на:\n"
            f"Дата и время: <b>{slot.start_time.strftime('%Y-%m-%d %H:%M')}</b>\n"
            f"Услуга: <b>{service_name}</b>\n"
            f"Мастер: <b>{master_name}</b>\n"
            f"Все верно?",
            reply_markup=keyboard
        )


@router.callback_query(F.data == "confirm_booking")
async def save_booking(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    booking_data = user_booking_data.get(user_id)

    if not booking_data:
        await callback_query.message.edit_text("Ошибка: данные записи не найдены.")
        return

    slot_id = booking_data.get("slot_id")
    if not slot_id:
        await callback_query.message.edit_text("Ошибка: слот не найден.")
        return

    service_id = booking_data.get("service_id")
    service_duration = booking_data.get("service_duration")
    master_id = booking_data.get("master_id")

    with SessionLocal() as session:
        starting_slot = session.query(TimeSlot).options(joinedload(TimeSlot.master)).filter(
            TimeSlot.id == slot_id).first()
        if not starting_slot:
            await callback_query.message.edit_text("Слот больше недоступен.")
            return

        slots_query = session.query(TimeSlot).filter(
            TimeSlot.start_time >= starting_slot.start_time,
            TimeSlot.start_time < starting_slot.start_time + timedelta(minutes=service_duration),
            TimeSlot.master_id == master_id,
            TimeSlot.status == TimeSlotStatus.free
        )

        slots_to_book = slots_query.order_by(TimeSlot.start_time).all()
        if len(slots_to_book) < service_duration // 15:
            await callback_query.message.edit_text("Недостаточно слотов для бронирования.")
            return

        for slot in slots_to_book:
            slot.status = TimeSlotStatus.booked

        user = session.query(User).filter(User.telegram_id == str(user_id)).first()
        if not user:
            user = User(telegram_id=str(user_id))
            session.add(user)

        appointment = Appointment(
            user_id=user.id,
            master_id=master_id,
            service_id=service_id,
            timeslot_id=starting_slot.id,
            status='scheduled'
        )
        session.add(appointment)
        session.commit()

        await callback_query.message.edit_text(
            f"Запись подтверждена на {starting_slot.start_time.strftime('%Y-%m-%d %H:%M')}.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Назад в меню", callback_data="back_to_menu")]
            ])
        )


def find_available_slots(slots, service_duration):
    required_slots = service_duration // 15
    available_slots = []

    i = 0
    while i < len(slots):
        if len(slots[i:i + required_slots]) < required_slots:
            break

        if all(slots[j].status == TimeSlotStatus.free for j in range(i, i + required_slots)):
            available_slots.append(slots[i])
            i += required_slots
        else:
            i += 1
    return available_slots
