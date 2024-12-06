import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import CallbackQuery


from config import API_TOKEN
from handlers import start_handler, services_handler, master_handler, calendar_handler, booking_handler, general_handler

# Настройка логгера
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

# Создание объекта бота
bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# Регистрация обработчиков
dp.include_router(start_handler.router)
dp.include_router(services_handler.router)
dp.include_router(master_handler.router)
dp.include_router(calendar_handler.router)
dp.include_router(booking_handler.router)
dp.include_router(general_handler.router)


# Основная функция
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

    logging.info(callback_query.from_user.id)



if __name__ == "__main__":
    asyncio.run(main())
