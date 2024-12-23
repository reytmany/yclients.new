import pytest
from unittest.mock import AsyncMock, patch
from master_bot import get_telegram_id_by_master_id


@pytest.mark.asyncio
async def test_get_telegram_id_by_master_id_not_found():
    # Мокаем результат, когда мастер не найден
    mock_session = AsyncMock()

    # Мокаем execute, чтобы он возвращал пустой результат
    mock_result = AsyncMock()
    mock_result.scalars.return_value.first.return_value = None
    mock_session.execute.return_value = mock_result

    # Мокаем async_session_maker, чтобы вернуть мок сессии
    with patch("master_bot.async_session_maker", return_value=mock_session):
        # Вызываем функцию
        telegram_id = await get_telegram_id_by_master_id(1)
        assert telegram_id is None


@pytest.mark.asyncio
async def test_get_telegram_id_by_master_id_with_error():
    # Мокаем сессию, которая вызывает ошибку
    mock_session = AsyncMock()

    # Мокаем execute, чтобы он вызывал исключение
    mock_session.execute.side_effect = Exception("Database error")

    # Мокаем async_session_maker, чтобы вернуть мок сессии
    with patch("master_bot.async_session_maker", return_value=mock_session):
        # Вызываем функцию
        telegram_id = await get_telegram_id_by_master_id(1)

        # Проверяем, что в случае ошибки возвращается None
        assert telegram_id is None
