from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram import Router, F
from database import SessionLocal, Service



router = Router()
from states import BookingStates

@router.callback_query(F.data == "select_master")
async def select_master_handler(callback_query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    service_id = data["service_id"]

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
        ] + [[InlineKeyboardButton(text="Назад", callback_data="back_to_menu")]]
    )

    await callback_query.message.edit_text("Выберите мастера:", reply_markup=keyboard)
