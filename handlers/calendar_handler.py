from aiogram.types import CallbackQuery
from datetime import datetime, timedelta
from utils.calendar import show_calendar
from aiogram import Router, F
from utils.data_storage import user_booking_data


router = Router()

@router.callback_query(F.data.startswith("change_week_"))
async def change_week_handler(callback_query: CallbackQuery):
    week_offset = int(callback_query.data.split("_")[2])
    user_id = callback_query.from_user.id
    await show_calendar(callback_query.message, user_id, week_offset)
