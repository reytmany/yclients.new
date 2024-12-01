from aiogram import Router, types, html
from aiogram.filters import CommandStart

router = Router()  # Создаем роутер для обработчиков стартовой команды

@router.message(CommandStart())
async def command_start_handler(message: types.Message) -> None:
    """
    Handler for the `/start` command
    """
    await message.answer(
        f"Здравствуйте, {html.bold(message.from_user.full_name)}!\n"
        "Я бот для записи к мастерам.\n"
        "Напишите /services, чтобы узнать услуги.\n"
        "Напишите /book, чтобы забронировать.\n"
    )
