import asyncio
import logging
import sys
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, Router, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import aiogram.exceptions

from config import API_TOKEN
from database import SessionLocal, Service, Master, TimeSlot, User, Appointment, TimeSlotStatus, \
    master_service_association
from sqlalchemy.orm import joinedload

# Настройка логгера
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

# Создание объекта бота с использованием DefaultBotProperties
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
    new_text = "Выберите действие:"
    try:
        await message.edit_text(new_text, reply_markup=keyboard)
    except aiogram.exceptions.TelegramBadRequest as e:
        if "message is not modified" in str(e):
            pass
        else:
            raise


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
    new_text = "Выберите услугу:"
    try:
        await callback_query.message.edit_text(new_text, reply_markup=keyboard)
    except aiogram.exceptions.TelegramBadRequest as e:
        if "message is not modified" in str(e):
            pass
        else:
            raise


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
        # Получаем мастеров, предоставляющих эту услугу
        masters = service.masters

    user_booking_data[callback_query.from_user.id] = {
        "service_id": service_id,
        "service_name": service.name,
        "service_duration": service.duration  # Store duration in minutes
    }

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Выбрать мастера", callback_data="select_master")],
            [InlineKeyboardButton(text="Выбрать время (мастер не важен)", callback_data="select_time_no_master")],
            [InlineKeyboardButton(text="Назад", callback_data="services")],
            [InlineKeyboardButton(text="Назад в меню", callback_data="back_to_menu")],
        ]
    )
    new_text = "Как вы хотите продолжить?"
    try:
        await callback_query.message.edit_text(new_text, reply_markup=keyboard)
    except aiogram.exceptions.TelegramBadRequest as e:
        if "message is not modified" in str(e):
            pass
        else:
            raise


# Обработчик выбора мастера
@router.callback_query(F.data == "select_master")
async def select_master_handler(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    service_id = user_booking_data[user_id]["service_id"]
    with SessionLocal() as session:
        service = session.query(Service).filter(Service.id == service_id).first()
        masters = service.masters

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                                [InlineKeyboardButton(
                                    text=f"{master.name} (Рейтинг: {master.rating})",
                                    callback_data=f"master_{master.id}"
                                )]
                                for master in masters
                            ] + [
                                [InlineKeyboardButton(text="Назад", callback_data=f"service_{service_id}")],
                                [InlineKeyboardButton(text="Назад в меню", callback_data="back_to_menu")],
                            ]
        )
    new_text = "Выберите мастера:"
    try:
        await callback_query.message.edit_text(new_text, reply_markup=keyboard)
    except aiogram.exceptions.TelegramBadRequest as e:
        if "message is not modified" in str(e):
            pass
        else:
            raise


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
    # Определяем текущий понедельник
    today = datetime.now().date()
    current_week_start = today - timedelta(days=today.weekday())  # Понедельник текущей недели
    max_weeks = 3  # Максимальное количество дополнительных недель (текущая неделя + 3 = 4 недели)
    week_offset = max(0, min(week_offset, max_weeks))  # Ограничиваем week_offset

    # Начало недели для отображения
    week_start = current_week_start + timedelta(weeks=week_offset)
    week_end = week_start + timedelta(days=6)  # Воскресенье этой недели

    dates_with_slots = []
    with SessionLocal() as session:
        service_id = user_booking_data[user_id]["service_id"]
        service_duration = user_booking_data[user_id]["service_duration"]
        master_id = user_booking_data[user_id].get("master_id")

        # Получаем мастеров, предоставляющих выбранную услугу
        if master_id is None:
            masters = session.query(Master).join(master_service_association).filter(master_service_association.c.service_id == service_id).all()
            master_ids = [master.id for master in masters]
        else:
            master_ids = [master_id]

        for i in range(7):  # Проходим по дням недели
            date = week_start + timedelta(days=i)
            start_datetime = datetime.combine(date, datetime.min.time())
            end_datetime = start_datetime + timedelta(days=1)

            # Получаем все свободные слоты мастеров, предоставляющих выбранную услугу
            all_slots = session.query(TimeSlot).options(
                joinedload(TimeSlot.master)
            ).filter(
                TimeSlot.master_id.in_(master_ids),
                TimeSlot.start_time >= start_datetime,
                TimeSlot.start_time < end_datetime,
                TimeSlot.status == TimeSlotStatus.free
            ).order_by(TimeSlot.master_id, TimeSlot.start_time).all()

            available_slots = find_available_slots(all_slots, service_duration)

            if available_slots:
                dates_with_slots.append(date)

    if not dates_with_slots:
        week_start_str = week_start.strftime("%d.%m")
        week_end_str = week_end.strftime("%d.%m")
        message_text = f"На неделю с {week_start_str} по {week_end_str} свободных окошек нет."
    else:
        message_text = "Выберите дату:"

    # Формируем кнопки для дат
    date_buttons = [
        [InlineKeyboardButton(text=date.strftime("%d %b %Y"), callback_data=f"date_{date.isoformat()}_{week_offset}")]
        for date in dates_with_slots
    ]

    # Кнопки навигации по неделям
    navigation_buttons = []
    if week_offset > 0:
        navigation_buttons.append(InlineKeyboardButton(text="⬅️ Пред. неделя", callback_data=f"change_week_{week_offset - 1}"))
    if week_offset < max_weeks:
        navigation_buttons.append(InlineKeyboardButton(text="След. неделя ➡️", callback_data=f"change_week_{week_offset + 1}"))

    # Кнопка "Назад"
    back_callback = "select_master" if user_booking_data[user_id].get("master_id") is not None else f"service_{user_booking_data[user_id]['service_id']}"

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=date_buttons + [
            navigation_buttons,
            [InlineKeyboardButton(text="Назад", callback_data=back_callback)],
            [InlineKeyboardButton(text="Назад в меню", callback_data="back_to_menu")],
        ]
    )

    # Проверяем изменения перед отправкой
    try:
        await message.edit_text(message_text, reply_markup=keyboard)
    except aiogram.exceptions.TelegramBadRequest as e:
        if "message is not modified" in str(e):
            pass
        else:
            raise



# Обработчик выбора недели
@router.callback_query(F.data.startswith("change_week_"))
async def change_week_handler(callback_query: CallbackQuery):
    week_offset = int(callback_query.data.split("_")[2])
    user_id = callback_query.from_user.id

    # Сохраняем текущий week_offset
    user_booking_data[user_id]['week_offset'] = week_offset

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
        await callback_query.message.edit_text("Ошибка: данные записи не найдены.")
        return
    master_id = booking_data.get("master_id")
    service_id = booking_data.get("service_id")
    service_duration = booking_data.get("service_duration")  # Duration in minutes

    # Сохраняем текущий week_offset
    user_booking_data[user_id]['week_offset'] = week_offset

    start_datetime = datetime.combine(selected_date, datetime.min.time())
    end_datetime = start_datetime + timedelta(days=1)

    with SessionLocal() as session:
        if master_id is None:
            masters = session.query(Master).join(master_service_association).filter(
                master_service_association.c.service_id == service_id).all()
            master_ids = [master.id for master in masters]
        else:
            master_ids = [master_id]

        # Получаем все свободные слоты мастеров, предоставляющих выбранную услугу
        all_slots = session.query(TimeSlot).options(
            joinedload(TimeSlot.master)
        ).filter(
            TimeSlot.master_id.in_(master_ids),
            TimeSlot.start_time >= start_datetime,
            TimeSlot.start_time < end_datetime,
            TimeSlot.status == TimeSlotStatus.free
        ).order_by(TimeSlot.master_id, TimeSlot.start_time).all()

        # Ищем доступные слоты, которые могут вместить продолжительность услуги
        available_slots = find_available_slots(all_slots, service_duration)

        if not available_slots:
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="Назад", callback_data=f"change_week_{week_offset}")],
                    [InlineKeyboardButton(text="Назад в меню", callback_data="back_to_menu")],
                ]
            )
            new_text = "Нет доступных слотов на эту дату."
            try:
                await callback_query.message.edit_text(new_text, reply_markup=keyboard)
            except aiogram.exceptions.TelegramBadRequest as e:
                if "message is not modified" in str(e):
                    pass
                else:
                    raise
            return

        # Формируем клавиатуру внутри контекста сессии
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

    # Отправляем сообщение после закрытия сессии
    new_text = "Выберите время:"
    try:
        await callback_query.message.edit_text(new_text, reply_markup=keyboard)
    except aiogram.exceptions.TelegramBadRequest as e:
        if "message is not modified" in str(e):
            pass
        else:
            raise


def find_available_slots(slots, service_duration):
    required_slots = service_duration // 15
    available_slots = []
    i = 0
    while i < len(slots):
        master_id = slots[i].master_id
        start_index = i
        end_index = i + required_slots
        consecutive_slots = slots[start_index:end_index]

        if len(consecutive_slots) < required_slots:
            i += 1
            continue

        is_consecutive = True
        for j in range(required_slots - 1):
            if (consecutive_slots[j + 1].start_time != consecutive_slots[j].start_time + timedelta(minutes=15) or
                    consecutive_slots[j + 1].status != TimeSlotStatus.free or
                    consecutive_slots[j + 1].master_id != master_id):
                is_consecutive = False
                break

        if is_consecutive:
            available_slots.append(consecutive_slots[0])
            i += required_slots  # Пропускаем проверенные слоты
        else:
            i += 1
    return available_slots


# Обработчик выбора времени
@router.callback_query(F.data.startswith("slot_"))
async def confirm_booking_handler(callback_query: CallbackQuery):
    slot_id = int(callback_query.data.split("_")[1])
    user_id = callback_query.from_user.id
    service_duration = user_booking_data[user_id].get("service_duration")  # Duration in minutes

    with SessionLocal() as session:
        slot = session.query(TimeSlot).options(joinedload(TimeSlot.master)).filter(TimeSlot.id == slot_id).first()
        user_booking_data[user_id]["slot_id"] = slot_id
        user_booking_data[user_id]["slot_time"] = slot.start_time
        user_booking_data[user_id]["master_id"] = slot.master_id  # Сохраняем master_id выбранного слота

        master_name = slot.master.name

        week_offset = user_booking_data[user_id].get('week_offset', 0)
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Подтверждаю", callback_data="confirm_booking")],
                [InlineKeyboardButton(text="Назад",
                                      callback_data=f"date_{slot.start_time.date().isoformat()}_{week_offset}")],
                [InlineKeyboardButton(text="Назад в меню", callback_data="back_to_menu")],
            ]
        )

        new_text = (
            f"Вы хотите записаться на:\n"
            f"Дата и время: <b>{slot.start_time.strftime('%Y-%m-%d %H:%M')}</b>\n"
            f"Услуга: <b>{user_booking_data[user_id]['service_name']}</b>\n"
            f"Мастер: <b>{master_name}</b>\n"
            f"Все верно?"
        )
        try:
            await callback_query.message.edit_text(new_text, reply_markup=keyboard)
        except aiogram.exceptions.TelegramBadRequest as e:
            if "message is not modified" in str(e):
                pass
            else:
                raise


# Обработчик подтверждения записи
@router.callback_query(F.data == "confirm_booking")
async def save_booking(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    booking_data = user_booking_data.get(user_id)

    if not booking_data:
        await callback_query.message.edit_text("Ошибка: данные записи не найдены.")
        return

    slot_id = booking_data.get("slot_id")
    if not slot_id:
        await callback_query.message.edit_text("Ошибка: выбранное время не найдено.")
        return

    service_id = booking_data.get("service_id")
    service_duration = booking_data.get("service_duration")  # Duration in minutes
    required_slots = service_duration // 15
    master_id = booking_data.get("master_id")

    with SessionLocal() as session:
        # Загружаем starting_slot вместе с master
        starting_slot = session.query(TimeSlot).options(joinedload(TimeSlot.master)).filter(
            TimeSlot.id == slot_id).first()

        if not starting_slot:
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="Назад в меню", callback_data="back_to_menu")],
                ]
            )
            await callback_query.message.edit_text("Извините, выбранное время больше недоступно.",
                                                   reply_markup=keyboard)
            return

        # Проверяем доступность необходимых слотов
        slots_query = session.query(TimeSlot).filter(
            TimeSlot.start_time >= starting_slot.start_time,
            TimeSlot.start_time < starting_slot.start_time + timedelta(minutes=service_duration),
            TimeSlot.master_id == master_id,
            TimeSlot.status == TimeSlotStatus.free
        )

        slots_to_book = slots_query.order_by(TimeSlot.start_time).all()

        if len(slots_to_book) < required_slots:
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="Назад в меню", callback_data="back_to_menu")],
                ]
            )
            await callback_query.message.edit_text("Извините, выбранное время больше недоступно.",
                                                   reply_markup=keyboard)
            return

        # Бронируем слоты
        for slot in slots_to_book:
            slot.status = TimeSlotStatus.booked

        # Получаем или создаем пользователя
        user = session.query(User).filter(User.telegram_id == str(user_id)).first()
        if not user:
            user = User(telegram_id=str(user_id))
            session.add(user)

        # Создаем запись на прием
        appointment = Appointment(
            user_id=user.id,
            master_id=master_id,
            service_id=service_id,
            timeslot_id=starting_slot.id,
            status='scheduled'
        )
        session.add(appointment)

        # Фиксируем изменения в базе данных
        session.commit()

        # Формируем сообщение внутри сессии
        new_text = (
            f"Вы успешно записаны на:\n"
            f"Дата: {booking_data['slot_time'].strftime('%Y-%m-%d %H:%M')}\n"
            f"Услуга: {booking_data['service_name']}\n"
            f"Мастер: {starting_slot.master.name}"
        )

    # Отправляем сообщение после закрытия сессии
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Назад в меню", callback_data="back_to_menu")],
        ]
    )
    try:
        await callback_query.message.edit_text(new_text, reply_markup=keyboard)
    except aiogram.exceptions.TelegramBadRequest as e:
        if "message is not modified" in str(e):
            pass
        else:
            raise


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
            new_text = "У вас пока нет активных записей."
            try:
                await callback_query.message.edit_text(new_text, reply_markup=keyboard)
            except aiogram.exceptions.TelegramBadRequest as e:
                if "message is not modified" in str(e):
                    pass
                else:
                    raise
            return

        # Загружаем связанные объекты с помощью joinedload
        bookings = session.query(Appointment).options(
            joinedload(Appointment.timeslot).joinedload(TimeSlot.master),
            joinedload(Appointment.service),
            joinedload(Appointment.master)
        ).filter(Appointment.user_id == user.id).all()

        if not bookings:
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="Назад в меню", callback_data="back_to_menu")],
                ]
            )
            new_text = "У вас пока нет активных записей."
            try:
                await callback_query.message.edit_text(new_text, reply_markup=keyboard)
            except aiogram.exceptions.TelegramBadRequest as e:
                if "message is not modified" in str(e):
                    pass
                else:
                    raise
            return

        booking_details = "\n".join(
            f"- {booking.timeslot.start_time.strftime('%Y-%m-%d %H:%M')} | {booking.service.name} | Мастер: {booking.master.name}"
            for booking in bookings
        )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Назад в меню", callback_data="back_to_menu")],
        ]
    )
    new_text = f"Ваши записи:\n{booking_details}"
    try:
        await callback_query.message.edit_text(new_text, reply_markup=keyboard)
    except aiogram.exceptions.TelegramBadRequest as e:
        if "message is not modified" in str(e):
            pass
        else:
            raise


# Обработчик произвольных текстовых сообщений
@router.message()
async def handle_unrecognized_message(message: Message):
    user_id = message.from_user.id
    booking_data = user_booking_data.get(user_id)

    if booking_data and 'service_id' in booking_data:
        # Пользователь уже выбрал услугу, предлагаем ему выбрать, как продолжить
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Выбрать мастера", callback_data="select_master")],
                [InlineKeyboardButton(text="Выбрать время (мастер не важен)", callback_data="select_time_no_master")],
                [InlineKeyboardButton(text="Назад", callback_data="services")],
                [InlineKeyboardButton(text="Назад в меню", callback_data="back_to_menu")],
            ]
        )
        new_text = "Как вы хотите продолжить?"
        await message.answer("Используйте кнопки для выбора.")
        await message.answer(new_text, reply_markup=keyboard)
    else:
        # Пользователь еще не выбрал услугу, предлагаем ему выбрать услугу
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
        new_text = "Выберите услугу:"
        await message.answer("Используйте кнопки для выбора.")
        await message.answer(new_text, reply_markup=keyboard)


# Регистрация роутеров
dp.include_router(router)


# Основная функция
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
