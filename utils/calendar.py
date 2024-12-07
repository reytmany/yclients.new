from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from database import SessionLocal, TimeSlot, TimeSlotStatus, master_service_association
from sqlalchemy.orm import joinedload
from datetime import datetime, timedelta
from aiogram.fsm.context import FSMContext

async def show_calendar(message: Message, state: FSMContext, week_offset: int):
    # Определяем текущий понедельник
    today = datetime.now().date()
    current_week_start = today - timedelta(days=today.weekday())  # Понедельник текущей недели
    max_weeks = 3  # Максимальное количество дополнительных недель (текущая неделя + 3 = 4 недели)
    week_offset = max(0, min(week_offset, max_weeks))  # Ограничиваем week_offset

    # Начало недели для отображения
    week_start = current_week_start + timedelta(weeks=week_offset)
    week_end = week_start + timedelta(days=6)  # Воскресенье этой недели

    # Получаем данные из состояния
    data = await state.get_data()
    service_id = data.get("service_id")
    service_duration = data.get("service_duration")
    master_id = data.get("master_id")

    if not service_id or not service_duration:
        await message.edit_text("Ошибка: данные услуги или длительности отсутствуют. Пожалуйста, начните заново.")
        return

    dates_with_slots = []
    with SessionLocal() as session:
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
    back_callback = "select_master" if master_id is not None else f"service_{service_id}"

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
