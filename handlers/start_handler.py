from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram import Router, F
from utils.main_menu import send_main_menu
from utils.data_storage import user_booking_data


router = Router()

@router.message(F.text == "/start")
async def first_interaction(message: Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Старт", callback_data="start")],
        ]
    )
    await message.answer("Добро пожаловать! Нажмите 'Старт', чтобы начать.", reply_markup=keyboard)


@router.callback_query(F.data == "start")
async def start_handler(callback_query: CallbackQuery):
    await send_main_menu(callback_query.message)


# Обработчик кнопки "Назад в меню"
@router.callback_query(F.data == "back_to_menu")
async def back_to_menu_handler(callback_query: CallbackQuery):
    await send_main_menu(callback_query.message)
