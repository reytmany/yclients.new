import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from handlers import (
    start_handler,
    services_handler,
    master_handler,
    calendar_handler,
    booking_handler,
    general_handler,
)
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()

# Настройка логгера
logging.basicConfig(level=logging.INFO)

# Получение токена из переменных окружения
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("Telegram bot token is not found in environment variables")

# Создание объекта бота с использованием DefaultBotProperties
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

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


if __name__ == "__main__":
    asyncio.run(main())
