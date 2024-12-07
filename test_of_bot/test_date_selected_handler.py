import pytest
from unittest.mock import MagicMock, patch
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from bot import user_booking_data, date_selected_handler
from datetime import datetime

@pytest.mark.asyncio
async def test_date_selected_handler_no_booking_data(callback_query, message):
    """Тест на обработку отсутствия данных в user_booking_data."""
    callback_query.data = "date_2024-12-03_0"
    callback_query.message = message()
    user_id = callback_query.from_user.id

    # Убедимся, что данных для пользователя нет
    if user_id in user_booking_data:
        del user_booking_data[user_id]

    # Выполнение
    await date_selected_handler(callback_query)

    # Проверка
    callback_query.message.edit_text.assert_awaited_once_with("Ошибка: данные записи не найдены.")


@pytest.mark.asyncio
async def test_date_selected_handler_no_available_slots(callback_query, message, mock_db_session):
    """Тест на отсутствие доступных слотов."""
    callback_query.data = "date_2024-12-03_0"
    callback_query.message = message()
    user_id = callback_query.from_user.id
    user_booking_data[user_id] = {
        "service_id": 1,
        "service_duration": 30,
        "master_id": None
    }

    mock_db_session.query.return_value.filter.return_value.all.return_value = []  # Нет слотов

    # Выполнение
    await date_selected_handler(callback_query)
    expected_text = "Нет доступных слотов на эту дату."
    expected_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Назад", callback_data="change_week_0")],
            [InlineKeyboardButton(text="Назад в меню", callback_data="back_to_menu")],
        ]
    )
    callback_query.message.edit_text.assert_awaited_once_with(expected_text, reply_markup=expected_keyboard)


@pytest.mark.asyncio
async def test_date_selected_handler_with_available_slots(callback_query, message, mock_db_session, master):
    """Тест на наличие доступных слотов."""
    callback_query.data = "date_2024-12-03_0"
    callback_query.message = message()
    user_id = callback_query.from_user.id
    user_booking_data[user_id] = {
        "service_id": 1,
        "service_duration": 30,
        "master_id": None
    }

    # Мокируем TimeSlot с мастером
    mock_slot = MagicMock()
    mock_slot.id = 1
    mock_slot.start_time = datetime(2024, 12, 3, 14, 0)
    mock_slot.master = master

    mock_db_session.query.return_value.filter.return_value.all.return_value = [mock_slot]  # Один слот

    # Выполнение
    with patch('bot.find_available_slots', return_value=[mock_slot]):
        await date_selected_handler(callback_query)


    expected_text = "Выберите время:"
    expected_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="14:00 (Test Master)", callback_data="slot_1"
            )],
            [InlineKeyboardButton(text="Назад", callback_data="change_week_0")],
            [InlineKeyboardButton(text="Назад в меню", callback_data="back_to_menu")],
        ]
    )
    callback_query.message.edit_text.assert_awaited_once_with(expected_text, reply_markup=expected_keyboard)

