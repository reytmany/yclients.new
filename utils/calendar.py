from datetime import datetime, timedelta
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery  # Добавлен CallbackQuery
from sqlalchemy.orm import joinedload
from database import SessionLocal, TimeSlot, TimeSlotStatus, master_service_association, Master

# Импортируем хранилище данных пользователя
from handlers.services_handler import user_booking_data


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
            masters = session.query(master_service_association).filter(
                master_service_association.c.service_id == service_id
            ).all()
            master_ids = [master.master_id for master in masters]
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
    except Exception as e:
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

# Обработчик выбора даты

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

    start_datetime = datetime.combine(selected_date, datetime.min.time())
    end_datetime = start_datetime + timedelta(days=1)

    with SessionLocal() as session:
        if master_id is None:
            masters = session.query(Master).join(master_service_association).filter(
                master_service_association.c.service_id == service_id).all()
            master_ids = [master.id for master in masters]
        else:
            master_ids = [master_id]

        all_slots = session.query(TimeSlot).options(
            joinedload(TimeSlot.master)
        ).filter(
            TimeSlot.master_id.in_(master_ids),
            TimeSlot.start_time >= start_datetime,
            TimeSlot.start_time < end_datetime,
            TimeSlot.status == TimeSlotStatus.free
        ).order_by(TimeSlot.master_id, TimeSlot.start_time).all()

        available_slots = find_available_slots(all_slots, service_duration)

        if not available_slots:
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="Назад", callback_data=f"change_week_{week_offset}")],
                    [InlineKeyboardButton(text="Назад в меню", callback_data="back_to_menu")],
                ]
            )
            new_text = "Нет доступных слотов на эту дату."
            await callback_query.message.edit_text(new_text, reply_markup=keyboard)
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

    new_text = "Выберите время:"
    await callback_query.message.edit_text(new_text, reply_markup=keyboard)
