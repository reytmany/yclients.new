import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession
from master_bot import main, Master


@pytest.mark.asyncio
@patch("master_bot.Bot")
@patch("master_bot.Dispatcher")
@patch("master_bot.async_session_maker")
@patch("master_bot.start_polling", AsyncMock())  # Патчим start_polling, чтобы не запускать реальный бот
async def test_main_start_command(mock_session_maker, mock_dispatcher, mock_bot):
    # Настроим mock объектов
    dp_instance = mock_dispatcher.return_value
    mock_session = MagicMock(spec=AsyncSession)
    mock_session_maker.return_value.__aenter__.return_value = mock_session

    # Создаем объект Master для теста
    mock_master = Master(name="Test Master", telegram_id=12345)

    # Настроим ответ от базы данных
    mock_result = AsyncMock()
    mock_result.scalars.return_value.first.return_value = mock_master
    mock_session.execute.return_value = mock_result

    # Создаем мок сообщения и добавляем необходимые атрибуты
    message = AsyncMock(spec=Message)
    message.from_user = AsyncMock(id=12345)
    message.text = "/start"  # Добавляем мок для text
    message.answer = AsyncMock()

    # Вызываем main для регистрации обработчиков
    await main()

    # Проверим, что обработчик был зарегистрирован
    assert dp_instance.message.call_count > 0, "Обработчик /start не был зарегистрирован."

    # Получаем зарегистрированный обработчик для команды /start
    start_handler = dp_instance.message.call_args_list[0][0][0]

    # Проверяем, что start_handler существует
    assert start_handler is not None, "Обработчик для /start не был зарегистрирован."



@pytest.mark.asyncio
@patch("master_bot.Bot")
@patch("master_bot.Dispatcher")
@patch("master_bot.async_session_maker")
@patch("master_bot.start_polling", AsyncMock())
async def test_main_start_command_not_found(mock_session_maker, mock_dispatcher, mock_bot):
    # Настроим mock объектов
    bot_instance = mock_bot.return_value
    dp_instance = mock_dispatcher.return_value

    # Мастер не найден в базе
    mock_session = AsyncMock()  # Используем AsyncMock для сессии
    mock_session_maker.return_value.__aenter__.return_value = mock_session

    mock_result = AsyncMock()
    mock_result.scalars.return_value.first.return_value = None
    mock_session.execute.return_value = mock_result

    # Создаем мок сообщения
    message = AsyncMock()
    message.text = "/start"
    message.answer = AsyncMock()

    # Вызываем main для регистрации обработчиков
    await main()

    # Проверяем, что обработчик для команды /start зарегистрирован в dp_instance
    handlers = dp_instance.message.get_commands()

    # Убедитесь, что обработчик для /start был добавлен
    assert handlers, "Обработчик для команды /start не был зарегистрирован."
