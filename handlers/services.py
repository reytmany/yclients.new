# handlers/services.py

from aiogram import Router, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.orm import joinedload

from database import SessionLocal, Service, Master


# Инициализация хранилища состояний
router = Router()

# Создание состояний
class ServiceSelectionState(StatesGroup):
    waiting_for_service = State()
    waiting_for_master = State()


# Команда для показа услуг
@router.message(Command("services"))
async def show_services(message: types.Message, state: FSMContext):
    session = SessionLocal()
    services = session.query(Service).all()
    session.close()

    if not services:
        await message.reply("На данный момент нет доступных услуг.")
        return

    # Создание клавиатуры с кнопками для услуг
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=f"{service.service_name}",
                callback_data=f"choose_service:{service.id}"
            )
        ] for service in services
    ])

    await message.reply("Выберите услугу:", reply_markup=keyboard)
    # Устанавливаем состояние для пользователя
    await state.set_state(ServiceSelectionState.waiting_for_service)


@router.callback_query(lambda callback_query: callback_query.data.startswith("choose_service:"))
async def handle_choose_service(callback_query: CallbackQuery, state: FSMContext):
    service_id = int(callback_query.data.split(":")[1])

    session = SessionLocal()

    # Используем joinedload для явной загрузки связанных мастеров
    service = session.query(Service).options(joinedload(Service.masters)).filter(Service.id == service_id).first()

    if not service:
        session.close()
        await callback_query.message.edit_text("К сожалению, услуга не найдена.")
        return

    masters = service.masters

    # Закрываем сессию, так как данные уже загружены
    session.close()

    if not masters:
        await callback_query.message.edit_text("У этой услуги нет мастеров.")
        return

    # Кнопка "Назад", которая возвращает к выбору услуги
    back_button = InlineKeyboardButton(text="Назад", callback_data="back_to_services")

    # Клавиатура с мастерами
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=f"{master.name}",
                callback_data=f"choose_master:{master.id}"
            )
        ] for master in masters
    ] + [[back_button]])  # Добавляем кнопку назад

    # Отправляем сообщение с выбранной услугой и клавиатурой для мастеров
    await callback_query.message.edit_text(
        f"Вы выбрали услугу: {service.service_name}.\nСтоимость: {service.cost} руб.\n\nВыберите мастера:",
        reply_markup=keyboard
    )

    # Сохраняем выбор услуги и устанавливаем новое состояние
    await state.update_data(service_id=service.id)
    await state.set_state(ServiceSelectionState.waiting_for_master)


# Обработка кнопки "Назад"
@router.callback_query(lambda callback_query: callback_query.data == "back_to_services")
async def back_to_services(callback_query: CallbackQuery, state: FSMContext):
    session = SessionLocal()
    services = session.query(Service).all()
    session.close()

    if not services:
        await callback_query.message.edit_text("На данный момент нет доступных услуг.")
        return

    # Создаем клавиатуру для выбора услуги
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=f"{service.service_name}",
                callback_data=f"choose_service:{service.id}"
            )
        ] for service in services
    ])

    # Отправляем сообщение с выбором услуги
    await callback_query.message.edit_text("Выберите услугу:", reply_markup=keyboard)

    # Возвращаем пользователя в состояние выбора услуги
    await state.set_state(ServiceSelectionState.waiting_for_service)


# Обработка выбора мастера
@router.callback_query(lambda callback_query: callback_query.data.startswith("choose_master:"))
async def handle_choose_master(callback_query: CallbackQuery, state: FSMContext):
    master_id = int(callback_query.data.split(":")[1])

    session = SessionLocal()
    master = session.query(Master).filter(Master.id == master_id).first()
    session.close()

    if not master:
        await callback_query.message.edit_text("К сожалению, мастер не найден.")
        return

    # Отправляем сообщение с выбранным мастером
    await callback_query.message.edit_text(
        f"Вы выбрали мастера: {master.name}. Он выполнит вашу услугу."
    )
