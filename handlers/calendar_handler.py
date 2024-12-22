from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta

from sqlalchemy.orm import joinedload

from utils.calendar import find_available_slots, show_calendar
from aiogram import Router, F
from database import SessionLocal, TimeSlot, TimeSlotStatus, master_service_association

from states import BookingStates

router = Router()

@router.callback_query(F.data.startswith("change_week_"))
async def change_week_handler(callback_query: CallbackQuery, state: FSMContext):
    week_offset = int(callback_query.data.split("_")[2])
    await show_calendar(callback_query.message, state, week_offset)


@router.callback_query(F.data.startswith("date_"))
async def date_selected_handler(callback_query: CallbackQuery, state: FSMContext):
    data_parts = callback_query.data.split("_")
    date_iso = data_parts[1]
    selected_date = datetime.fromisoformat(date_iso).date()

    # Получение данных из FSM
    data = await state.get_data()
    master_id = data.get("master_id")
    service_id = data.get("service_id")
    service_duration = data.get("service_duration")
    print(data)
    if not service_id or not service_duration:
        await callback_query.message.edit_text(
            "Ошибка: данные записи отсутствуют. Пожалуйста, начните заново.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="Назад в меню", callback_data="back_to_menu")]
                ]
            )
        )
        return

    start_datetime = datetime.combine(selected_date, datetime.min.time())
    end_datetime = start_datetime + timedelta(days=1)

    # Получение доступных слотов
    with SessionLocal() as session:
        if master_id is None:
            master_ids = [
                m.master_id for m in session.query(master_service_association).filter(
                    master_service_association.c.service_id == service_id
                ).all()
            ]
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

        available_slots = [
            {
                "start_time": slot.start_time,
                "master_name": slot.master.name,
                "slot_id": slot.id
            }
            for slot in available_slots
        ]

    # Обработка результата
    if not available_slots:
        await callback_query.message.edit_text(
            "Нет доступных слотов на эту дату.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="Назад", callback_data=f"change_week_{data_parts[2]}")],
                    [InlineKeyboardButton(text="Назад в меню", callback_data="back_to_menu")],
                ]
            )
        )
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=f"{slot['start_time'].strftime('%H:%M')} ({slot['master_name']})",
                callback_data=f"slot_{slot['slot_id']}"
            )]
            for slot in available_slots
        ] + [
            [InlineKeyboardButton(text="Назад", callback_data=f"change_week_{data_parts[2]}")],
            [InlineKeyboardButton(text="Назад в меню", callback_data="back_to_menu")],
        ]
    )
    await state.set_state(BookingStates.selecting_time)
    await callback_query.message.edit_text("Выберите время:", reply_markup=keyboard)
