import pytest
from unittest.mock import  AsyncMock, patch
from bot import user_booking_data, change_week_handler


@pytest.mark.asyncio
async def test_change_week_handler(callback_query):
    user_id = 12345
    week_offset = 2
    callback_query.data = f"change_week_{week_offset}"
    callback_query.from_user.id = user_id
    callback_query.message = AsyncMock()

    user_booking_data[user_id] = {"service_id": 1}  # Предварительно записываем данные пользователя

    # Мок для show_calendar
    with patch("bot.show_calendar", new=AsyncMock()) as mock_show_calendar:
        await change_week_handler(callback_query)

        # Проверяем, что week_offset сохранился в user_booking_data
        assert user_booking_data[user_id]["week_offset"] == week_offset

        # Проверяем, что show_calendar вызван с правильными параметрами
        mock_show_calendar.assert_awaited_once_with(callback_query.message, user_id, week_offset)
