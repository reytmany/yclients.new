from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.orm import joinedload
from database import SessionLocal, Service, Master, TimeSlot, TimeSlotStatus, master_service_association, User, Appointment
import logging
from datetime import datetime, timedelta

from master_bot import delete_send_telegram_notification

from utils.calendar import show_calendar

# Создаем роутер
router = Router()

# Хранилище данных для текущего выбора пользователя
user_booking_data = {}

logging.basicConfig(level=logging.INFO)
# Обработчик команды "Посмотреть услуги"
@router.callback_query(F.data == "services")
async def services_handler(callback_query: CallbackQuery):
    with SessionLocal() as session:
        services = session.query(Service).all()

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"{service.name} - {service.cost} руб.",
                                  callback_data=f"service_{service.id}")]
            for service in services
        ] + [
            [InlineKeyboardButton(text="Назад в меню", callback_data="back_to_menu")],
        ]
    )
    await callback_query.message.edit_text("Выберите услугу:", reply_markup=keyboard)


# Обработчик выбора услуги
# При выборе услуги
from states import BookingStates

@router.callback_query(F.data.startswith("service_"))
async def select_service_handler(callback_query: CallbackQuery, state: FSMContext):
    service_id = int(callback_query.data.split("_")[1])

    with SessionLocal() as session:
        service = session.query(Service).filter(Service.id == service_id).first()

    # Сохраняем данные в состоянии FSM
    await state.update_data(service_id=service_id, service_name=service.name, service_duration=service.duration)

    # Устанавливаем состояние выбора мастера
    await state.set_state(BookingStates.selecting_master)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Выбрать мастера", callback_data="select_master")],
            [InlineKeyboardButton(text="Выбрать время (мастер не важен)", callback_data="select_time_no_master")],
            [InlineKeyboardButton(text="Назад", callback_data="back_to_menu")],
        ]
    )
    await callback_query.message.edit_text("Как вы хотите продолжить?", reply_markup=keyboard)
@router.callback_query(F.data == "select_master")
async def select_master_handler(callback_query: CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    data = await state.get_data()
    service_id = data.get("service_id")

    if not service_id:
        await callback_query.message.edit_text("Ошибка: услуга не выбрана.")
        return

    with SessionLocal() as session:
        service = session.query(Service).filter(Service.id == service_id).first()
        if not service or not service.masters:
            await callback_query.message.edit_text("Нет доступных мастеров для выбранной услуги.")
            return

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(
                    text=f"{master.name} (Рейтинг: {master.rating})",
                    callback_data=f"master_{master.id}"
                )]
                for master in service.masters
            ] + [
                [InlineKeyboardButton(text="Назад", callback_data=f"service_{service_id}")],
                [InlineKeyboardButton(text="Назад в меню", callback_data="back_to_menu")],
            ]
        )
    await callback_query.message.edit_text("Выберите мастера:", reply_markup=keyboard)


# Обработчик выбора мастера
@router.callback_query(F.data.startswith("master_"))
async def select_master_calendar_handler(callback_query: CallbackQuery, state: FSMContext):
    master_id = int(callback_query.data.split("_")[1])
    await state.update_data(master_id=master_id)  # Сохраняем выбор мастера в состояние

    await show_calendar(callback_query.message, state, week_offset=0)


# Обработчик выбора времени без мастера
@router.callback_query(F.data == "select_time_no_master")
async def select_time_no_master_handler(callback_query: CallbackQuery, state: FSMContext):
    await state.update_data(master_id=None)  # Устанавливаем, что мастер не выбран

    await show_calendar(callback_query.message, state, week_offset=0)
# Обработчик кнопки "Мои записи"
@router.callback_query(F.data == "my_bookings")
async def my_bookings_handler(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id

    with SessionLocal() as session:
        user = session.query(User).filter(User.telegram_id == str(user_id)).first()
        if not user:
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="Назад в меню", callback_data="back_to_menu")],
                ]
            )
            await callback_query.message.edit_text("У вас пока нет активных записей.", reply_markup=keyboard)
            return

        bookings = session.query(Appointment).options(
            joinedload(Appointment.timeslot).joinedload(TimeSlot.master),
            joinedload(Appointment.service),
            joinedload(Appointment.master)
        ).join(Appointment.timeslot).filter(
            Appointment.user_id == user.id,
            TimeSlot.start_time > (datetime.utcnow() + timedelta(hours=2, minutes=45)),
            Appointment.status != "cancelled"
        ).all()

        if not bookings:
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="Назад в меню", callback_data="back_to_menu")],
                ]
            )
            await callback_query.message.edit_text("У вас пока нет активных записей.", reply_markup=keyboard)
            return

        # Формируем кнопки "Отменить" для каждой записи
        keyboard_buttons = []
        for booking in bookings:
            button_text = (
                f"{booking.timeslot.start_time.strftime('%Y-%m-%d %H:%M')} | "
                f"{booking.service.name} | Мастер: {booking.master.name}"
            )
            cancel_callback = f"cancel_booking_{booking.id}"
            keyboard_buttons.append([InlineKeyboardButton(text=button_text, callback_data="noop")])
            keyboard_buttons.append([InlineKeyboardButton(text="❌ Отменить", callback_data=cancel_callback)])

    # Добавляем кнопку "Назад в меню"
    keyboard_buttons.append([InlineKeyboardButton(text="Назад в меню", callback_data="back_to_menu")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    await callback_query.message.edit_text("Ваши записи:", reply_markup=keyboard)


@router.callback_query(F.data.startswith("cancel_booking_"))
async def cancel_booking_handler(callback_query: CallbackQuery):
    booking_id = int(callback_query.data.split("_")[2])  # Получаем ID записи

    with SessionLocal() as session:
        # Находим запись
        booking = session.query(Appointment).filter(Appointment.id == booking_id).first()
        if not booking:
            await callback_query.answer("Запись не найдена или уже отменена.", show_alert=True)
            return
        # Помечаем запись как отменённую
        booking.status = "cancelled"

        # Освобождаем все временные слоты, связанные с этой записью
        timeslot = session.query(TimeSlot).filter(TimeSlot.id == booking.timeslot_id).first()
        if not timeslot:
            await callback_query.answer("Связанные временные слоты не найдены.", show_alert=True)
            return

        # Рассчитываем длительность услуги
        service_duration = booking.service.duration  # В минутах
        required_slots = service_duration // 15

        # Ищем последовательные слоты для освобождения
        end_time = timeslot.start_time + timedelta(minutes=service_duration)
        booked_slots = session.query(TimeSlot).filter(
            TimeSlot.master_id == timeslot.master_id,
            TimeSlot.start_time >= timeslot.start_time,
            TimeSlot.start_time < end_time,
            TimeSlot.status == TimeSlotStatus.booked
        ).order_by(TimeSlot.start_time).all()
        print(booking.master_id, booking.user.telegram_id,
                                                booking.timeslot.start_time, booking.service.name)
        for slot in booked_slots:
            slot.status = TimeSlotStatus.free  # Освобождаем слот
        await delete_send_telegram_notification(booking.master_id, booking.user.telegram_id,
                                                booking.timeslot.start_time, booking.service.name)
        session.commit()

    # Обновляем список записей
    await my_bookings_handler(callback_query)


@router.callback_query(F.data == "previous_step")
async def previous_step_handler(callback_query: CallbackQuery, state: FSMContext):
    """Обработчик для кнопки 'Назад'."""
    data = await state.get_data()
    previous_state = await state.get_state()

    if previous_state == BookingStates.confirming.state:
        # Если пользователь находится на этапе подтверждения, возвращаем его к выбору времени
        week_offset = data.get("week_offset", 0)
        await state.set_state(BookingStates.selecting_time)
        await show_calendar(callback_query.message, state, week_offset)
    elif previous_state == BookingStates.selecting_time.state:
        # Если пользователь находится на этапе выбора времени, возвращаем к выбору мастера
        master_id = data.get("master_id")
        service_id = data.get("service_id")

        if master_id:
            await state.set_state(BookingStates.selecting_master)
            await select_master_handler(callback_query, state)
        else:
            await state.set_state(BookingStates.selecting_service)
            await callback_query.message.edit_text(
                "Выберите услугу или действие:",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="Выбрать услугу", callback_data="services")],
                        [InlineKeyboardButton(text="Назад в меню", callback_data="back_to_menu")],
                    ]
                ),
            )
    else:
        await callback_query.message.edit_text("Ошибка: действие для 'Назад' не определено.")
