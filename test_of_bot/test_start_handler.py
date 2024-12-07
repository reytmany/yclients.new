import pytest
from unittest.mock import AsyncMock, patch
from aiogram.types import CallbackQuery
from bot import start_handler

@pytest.mark.asyncio
async def test_start_handler(callback_query: CallbackQuery):
    """Тестируем, что start_handler вызывает send_main_menu с правильными параметрами"""

    # Патчим send_main_menu в правильном месте
    with patch('bot.send_main_menu', new_callable=AsyncMock) as mock_send_main_menu:
        # Вызываем start_handler
        await start_handler(callback_query)

        # Проверяем, что send_main_menu была вызвана с правильным сообщением
        mock_send_main_menu.assert_called_once_with(callback_query.message)
