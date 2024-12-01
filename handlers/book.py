from aiogram import Router, types
from aiogram.filters import Command
from database import SessionLocal, Master

router = Router()  # Роутер для записи к мастерам

@router.message(Command("book"))
async def cmd_book(message: types.Message):
    session = SessionLocal()
    masters = session.query(Master).all()
    if not masters:
        await message.reply("Мастера не найдены.")
    else:
        masters_list = "\n".join([f"{master.id}. {master.name} - {master.specialization}" for master in masters])
        await message.reply(f"Наши мастера:\n{masters_list}\nВыберите мастера.")
    session.close()
