from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from database import SessionLocal, Service



# Инициализация роутера
router = Router()

@router.message()
async def handle_unrecognized_message(message: Message, state: FSMContext):
    user_id = message.from_user.id
    booking_data = await state.get_data()  # Получаем данные из FSMContext

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
