import asyncio
import os

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardRemove
)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker
from database import Master
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN2")
if not API_TOKEN:
    raise ValueError("Telegram bot token is not found in environment variables")

# Создаем асинхронный движок базы данных и сессию
engine = create_async_engine('sqlite+aiosqlite:///database.db', echo=True)
async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Функция для получения имени пользователя по Telegram ID
async def get_username_by_telegram_id(telegram_id):
    async with Bot(token=API_TOKEN) as master_bot:
        try:
            chat = await master_bot.get_chat_member(telegram_id, telegram_id)
            return chat.user.first_name if chat.user.first_name else chat.user.username if chat.user.username else str(telegram_id)
        except Exception as e:
            return str(telegram_id)

async def get_telegram_id_by_master_id(master_id):
    async with async_session_maker() as session:
        try:
            result = await session.execute(
                select(Master).filter(Master.id == master_id)
            )
            master = result.scalars().first()  # Получаем первую (и единственную) запись

            if master:
                return master.telegram_id
            else:
                return None
        except Exception as e:
            return None

async def insertion_send_telegram_notification(master_id, user_telegram_id, booking_data):
    async with Bot(token=API_TOKEN) as master_bot:
        master_telegram_id = await get_telegram_id_by_master_id(master_id)
        name = await get_username_by_telegram_id(user_telegram_id)
        message = (
            f"У вас новая запись на {booking_data['slot_time'].strftime('%d-%m %H:%M')}\n"  
            f"Услуга: {booking_data['service_name']}\n"
            f"Клиент: {name}"
        )
        try:
            await master_bot.send_message(chat_id=master_telegram_id, text=message)
        except Exception as e:
            pass

async def delete_send_telegram_notification(master_telegram_id, user_id, booking_data):
    async with Bot(token=API_TOKEN) as master_bot:
        name = await get_username_by_telegram_id(user_id)
        message = (
            f"У вас отмена записи на {booking_data['slot_time'].strftime('%d-%m %H:%M')}\n" 
            f"Услуга: {booking_data['service_name']}\n"
            f"Клиент: {name}"
        )
        try:
            await master_bot.send_message(chat_id=master_telegram_id, text=message)
        except Exception as e:
            pass

async def start_polling(dp, master_bot):
    try:
        await dp.start_polling(master_bot)
    finally:
        await master_bot.close()
        await master_bot.session.close()

async def main():
    async with Bot(token=API_TOKEN) as master_bot:
        dp = Dispatcher()

        @dp.message(Command("start"))
        async def cmd_start(message: Message):
            async with async_session_maker() as session:
                try:
                    result = await session.execute(
                        select(Master).filter(Master.telegram_id == message.from_user.id)
                    )
                    master = result.scalars().first()
                    if master:
                        keyboard = ReplyKeyboardMarkup(
                            keyboard=[[KeyboardButton(text="Подключиться к записям")]],
                            resize_keyboard=True
                        )
                        await message.answer(
                            f"Здравствуйте, {master.name}! Я бот для уведомлений мастеров. "
                            "Подключите меня к своим записям для получения уведомлений! 💋",
                            reply_markup=keyboard
                        )
                    else:
                        await message.answer(
                            "Кажется, Вы не являетесь нашим мастером, "
                            "обратитесь к администратору."
                            "Если вы хотите записаться в салон, напишите @HseKrasotaBot ❤️"
                        )
                except Exception as e:
                    await message.answer("Произошла ошибка на сервере.")

        @dp.message(F.text == "Подключиться к записям")
        async def connect_to_records(message: Message):
            async with async_session_maker() as session:
                try:
                    result = await session.execute(
                        select(Master).filter(Master.telegram_id == message.from_user.id)
                    )
                    master = result.scalars().first()
                    if master:
                        master.notifications_enabled = True
                        await session.commit()
                        await message.answer(
                            "Вы успешно подключены к уведомлениям о записях!",
                            reply_markup=ReplyKeyboardRemove()
                        )
                    else:
                        await message.answer("Мастер не найден в базе данных!")
                except Exception as e:
                    await message.answer("Произошла ошибка при подключении к записям.")

        @dp.message()
        async def handle_unknown_message(message: Message):
            await message.answer(
                "Простите, но я еще не научился понимать Ваши сообщения, зато я могу уведомлять Вас о записях!"
            )

        # Запуск бота
        await start_polling(dp, master_bot)

if __name__ == '__main__':
    asyncio.run(main())
