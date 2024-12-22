from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

async def send_main_menu(message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Посмотреть услуги", callback_data="services")],
            [InlineKeyboardButton(text="Мои записи", callback_data="my_bookings")],
            [InlineKeyboardButton(text="Оставить отзыв", callback_data="leave_review")],
        ]
    )
    await message.edit_text("Выберите действие:", reply_markup=keyboard)

