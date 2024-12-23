import pytest
from unittest.mock import AsyncMock
from master_bot import start_polling


@pytest.mark.asyncio
async def test_start_polling_success():
    # Мокаем диспетчер и бота
    mock_dp = AsyncMock()
    mock_bot = AsyncMock()

    # Вызываем тестируемую функцию
    await start_polling(mock_dp, mock_bot)

    # Проверяем, что start_polling был вызван
    mock_dp.start_polling.assert_awaited_once_with(mock_bot)

    # Проверяем, что bot.close и bot.session.close были вызваны
    mock_bot.close.assert_awaited_once()
    mock_bot.session.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_start_polling_with_exception():
    # Мокаем диспетчер и бота
    mock_dp = AsyncMock()
    mock_bot = AsyncMock()

    # Эмулируем исключение в start_polling
    mock_dp.start_polling.side_effect = Exception("Polling error")

    # Вызываем тестируемую функцию
    with pytest.raises(Exception, match="Polling error"):
        await start_polling(mock_dp, mock_bot)

    # Проверяем, что start_polling был вызван
    mock_dp.start_polling.assert_awaited_once_with(mock_bot)

    # Проверяем, что bot.close и bot.session.close были вызваны даже при исключении
    mock_bot.close.assert_awaited_once()
    mock_bot.session.close.assert_awaited_once()