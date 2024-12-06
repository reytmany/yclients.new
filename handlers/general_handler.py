from aiogram.types import Message, CallbackQuery
from aiogram import Router
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.data_storage import user_booking_data


# Инициализация роутера
router = Router()

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
