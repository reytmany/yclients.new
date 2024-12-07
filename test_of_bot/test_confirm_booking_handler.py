import pytest
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from bot import user_booking_data, confirm_booking_handler
from datetime import datetime


@pytest.mark.asyncio
async def test_confirm_booking_handler_correct(callback_query, message, mock_db_session, timeslot):
    '''Тест для обработки корректной записи на время'''
    # Мокируем слот времени
    user_id = callback_query.from_user.id
    slot_id = 1
    service_duration = 30  # длительность услуги
    master_id = 1
    start_time = datetime(2024, 12, 4, 14, 0)  # Пример времени начала
    slot = timeslot(master_id, start_time)
    slot.id = slot_id  # Присваиваем слот ID
    slot.master.name = "Test Master"  # Устанавливаем имя мастера

    mock_db_session.query().options().filter().first.return_value = slot

    # Мокаем данные пользователя
    user_booking_data[user_id] = {
        'service_name': "Test Service",
        'service_duration': service_duration
    }

    # Создаем клавиатуру
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Подтверждаю", callback_data="confirm_booking")],
            [InlineKeyboardButton(text="Назад", callback_data=f"date_{start_time.date().isoformat()}_0")],
            [InlineKeyboardButton(text="Назад в меню", callback_data="back_to_menu")],
        ]
    )

    # Вызываем обработчик
    await confirm_booking_handler(callback_query)

    # Проверка, что был вызван метод edit_text с правильным текстом и клавиатурой
    new_text = (
        f"Вы хотите записаться на:\n"
        f"Дата и время: <b>{start_time.strftime('%Y-%m-%d %H:%M')}</b>\n"
        f"Услуга: <b>Test Service</b>\n"
        f"Мастер: <b>Test Master</b>\n"
        f"Все верно?"
    )

    callback_query.message.edit_text.assert_called_once_with(new_text, reply_markup=keyboard)


@pytest.mark.asyncio
async def test_confirm_booking_handler_user_data_update(callback_query, message, mock_db_session, timeslot):
    '''Тест для обработки изменения данных пользователя'''
    # Мокируем слот времени
    user_id = callback_query.from_user.id
    slot_id = 1
    service_duration = 30  # длительность услуги
    master_id = 1
    start_time = datetime(2024, 12, 4, 14, 0)  # Пример времени начала
    slot = timeslot(master_id, start_time)
    slot.id = slot_id  # Присваиваем слот ID
    slot.master.name = "Test Master"  # Устанавливаем имя мастера
    mock_db_session.query().options().filter().first.return_value = slot

    # Мокаем данные пользователя
    user_booking_data[user_id] = {
        'service_name': "Test Service",
        'service_duration': service_duration
    }

    # Вызываем обработчик
    await confirm_booking_handler(callback_query)

    # Проверяем, что данные в user_booking_data были обновлены
    assert user_booking_data[user_id]["slot_id"] == slot_id
    assert user_booking_data[user_id]["slot_time"] == start_time
    assert user_booking_data[user_id]["master_id"] == master_id

