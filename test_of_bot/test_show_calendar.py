import pytest
from unittest.mock import AsyncMock, patch
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from bot import user_booking_data, show_calendar_for_master, show_calendar_no_master, show_calendar

from datetime import datetime, timedelta

@pytest.mark.asyncio
async def test_show_calendar_for_master(callback_query):
    """Тестируем установку master_id для пользователя"""

    # Устанавливаем данные в callback_query
    master_id = 1
    callback_query.data = f"master_{master_id}"

    # Инициализируем user_booking_data для пользователя
    user_booking_data[callback_query.from_user.id] = {}

    # Мокаем функцию show_calendar
    with patch("bot.show_calendar", new=AsyncMock()) as mock_show_calendar:
        # Вызываем тестируемую функцию
        await show_calendar_for_master(callback_query)

        # Проверяем, что master_id обновлён
        assert user_booking_data[callback_query.from_user.id]["master_id"] == master_id

        # Проверяем, что show_calendar вызвана с корректными параметрами
        mock_show_calendar.assert_called_once_with(
            callback_query.message, callback_query.from_user.id, week_offset=0
        )

@pytest.mark.asyncio
async def test_show_calendar_no_master_reset_master(callback_query):
    """Тестируем сброс master_id для существующего пользователя"""

    # Добавляем данные пользователя в user_booking_data
    user_booking_data[callback_query.from_user.id] = {"master_id": 1}

    # Настраиваем callback_query
    callback_query.data = "select_time_no_master"

    # Мокаем функцию show_calendar
    with patch("bot.show_calendar", new=AsyncMock()) as mock_show_calendar:
        # Вызываем тестируемую функцию
        await show_calendar_no_master(callback_query)

        # Проверяем, что master_id сброшен
        assert user_booking_data[callback_query.from_user.id]["master_id"] is None

        # Проверяем, что show_calendar вызвана с корректными параметрами
        mock_show_calendar.assert_called_once_with(
            callback_query.message, callback_query.from_user.id, week_offset=0
        )

@pytest.mark.asyncio
async def test_show_calendar_no_master_new_user(callback_query):
    user_id = 12345

    # Убедимся, что данных для пользователя нет
    if user_id in user_booking_data:
        del user_booking_data[user_id]

    # Создаём пустую запись для пользователя в user_booking_data
    user_booking_data[user_id] = {}

    # Настраиваем callback_query
    callback_query.data = "select_time_no_master"

    # Мок функции show_calendar
    with patch("bot.show_calendar", new=AsyncMock()) as mock_show_calendar:
        # Вызов тестируемой функции
        await show_calendar_no_master(callback_query)

        # Проверка, что данные для пользователя обновлены
        assert user_booking_data[user_id]["master_id"] is None

        # Проверка, что show_calendar вызвана
        mock_show_calendar.assert_called_once_with(
            callback_query.message, user_id, week_offset=0
        )


@pytest.mark.asyncio
async def test_show_calendar_with_slots(message, mock_db_session):
    # Настроим данные
    user_id = 12345
    week_offset = 0

    # Получаем сегодняшнюю дату
    today = datetime.today().date()

    user_booking_data[user_id] = {
        "service_id": 1,
        "service_duration": 30,
        "master_id": None
    }

    # Настроим возвращаемые слоты (пусть их не будет)
    mock_db_session.query.return_value.filter.return_value.all.return_value = []

    # Мокируем сообщение как AsyncMock
    message = AsyncMock()

    # Вызываем функцию
    await show_calendar(message, user_id, week_offset)

    # Для правильного подсчета даты начала недели (если понедельник является началом недели)
    start_date = today - timedelta(days=today.weekday())
    end_date = start_date + timedelta(days=6)

    # Ожидаемое сообщение без года
    expected_message = f"На неделю с {start_date.strftime('%d.%m')} по {end_date.strftime('%d.%m')} свободных окошек нет."

    # Ожидаемая клавиатура
    expected_reply_markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="След. неделя ➡️", callback_data="change_week_1")],
        [InlineKeyboardButton(text="Назад", callback_data="service_1")],
        [InlineKeyboardButton(text="Назад в меню", callback_data="back_to_menu")]
    ])

    # Убедимся, что edit_text был вызван один раз с ожидаемыми параметрами
    message.edit_text.assert_called_once_with(expected_message, reply_markup=expected_reply_markup)
