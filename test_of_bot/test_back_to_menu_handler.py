import pytest
from unittest.mock import AsyncMock, patch
from bot import  back_to_menu_handler

@pytest.mark.asyncio
async def test_back_to_menu_handler_calls_send_main_menu(message, callback_query):
    """Тестируем, что back_to_menu_handler вызывает send_main_menu с правильным сообщением"""

    # Убедимся, что данные callback_query правильные (button back_to_menu)
    callback_query.data = "back_to_menu"

    # Патчим send_main_menu, чтобы проверить его вызов
    with patch('bot.send_main_menu', new_callable=AsyncMock) as mock_send_main_menu:
        # Вызываем обработчик
        await back_to_menu_handler(callback_query)

        # Проверяем, что send_main_menu была вызвана с правильным сообщением
        mock_send_main_menu.assert_called_once_with(callback_query.message)

