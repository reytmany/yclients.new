import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from aiogram import types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from aiogram.exceptions import TelegramBadRequest
from bot import first_interaction, start_handler, send_main_menu, back_to_menu_handler, select_service_handler, user_booking_data
from database import Appointment, Service


@pytest.fixture
def message():
    """Фикстура для создания мок-сообщений"""

    def _message(text='/start', user_id=12345, is_bot=False, first_name="Test"):
        mock_message = MagicMock(spec=types.Message)
        mock_message.text = text
        mock_message.from_user = types.User(id=user_id, is_bot=is_bot, first_name=first_name)
        mock_message.edit_text = AsyncMock()
        return mock_message

    return _message


@pytest.fixture
def callback_query(message):
    """Фикстура для создания мок-объекта callback_query"""
    mock_callback_query = MagicMock(spec=CallbackQuery)
    mock_callback_query.data = "service_1"  # Убедитесь, что данные правильные
    mock_callback_query.message = message(text="Some text")
    mock_callback_query.from_user = MagicMock(id=12345)
    return mock_callback_query


@pytest.fixture
def service():
    """Фикстура для создания мок-объекта Service"""
    mock_service = MagicMock(spec=Service)
    mock_service.id = 1
    mock_service.name = "Test Service"
    mock_service.duration = 30  # Пример продолжительности услуги
    return mock_service


@pytest.fixture
def mock_db_session():
    """Фикстура для мокирования сессии базы данных"""
    with patch('bot.SessionLocal') as mock_session_local:
        mock_session = MagicMock()
        mock_session_local.return_value.__enter__.return_value = mock_session

        # Мокаем метод query().filter().first() в mock_session
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value.first.return_value = None  # Заглушка для первого запроса
        yield mock_session



@pytest.mark.asyncio
async def test_answer_called(message: types.Message):
    """Тестируем, что метод answer был вызван"""
    mock_message = message(text='/start')

    # Мокаем метод answer
    mock_message.answer = AsyncMock()

    # Вызываем обработчик
    await first_interaction(mock_message)

    # Проверяем, что answer был вызван один раз
    mock_message.answer.assert_called_once()


@pytest.mark.asyncio
async def test_keyboard_structure(message: types.Message):
    """Тестируем структуру клавиатуры"""
    mock_message = message(text='/start')

    # Мокаем метод answer
    mock_message.answer = AsyncMock()

    # Вызываем обработчик
    await first_interaction(mock_message)

    # Проверяем, что reply_markup (клавиатура) передана
    args, kwargs = mock_message.answer.call_args
    keyboard = kwargs.get('reply_markup')

    assert isinstance(keyboard, InlineKeyboardMarkup)  # Убедитесь, что это InlineKeyboardMarkup
    assert len(keyboard.inline_keyboard) == 1  # Клавиатура должна содержать 1 ряд кнопок
    assert len(keyboard.inline_keyboard[0]) == 1  # Один элемент в ряду


@pytest.mark.asyncio
async def test_button_text(message: types.Message):
    """Тестируем текст кнопки 'Старт'"""
    mock_message = message(text='/start')

    # Мокаем метод answer
    mock_message.answer = AsyncMock()

    # Вызываем обработчик
    await first_interaction(mock_message)

    # Получаем переданные аргументы для ответа
    args, kwargs = mock_message.answer.call_args
    keyboard = kwargs.get('reply_markup')

    # Проверяем, что текст кнопки 'Старт'
    start_button = keyboard.inline_keyboard[0][0]
    assert isinstance(start_button, InlineKeyboardButton)
    assert start_button.text == "Старт"


@pytest.mark.asyncio
async def test_start_handler(callback_query: CallbackQuery):
    """Тестируем, что start_handler вызывает send_main_menu с правильными параметрами"""

    # Патчим send_main_menu в правильном месте
    with patch('bot.send_main_menu', new_callable=AsyncMock) as mock_send_main_menu:
        # Вызываем start_handler
        await start_handler(callback_query)

        # Проверяем, что send_main_menu была вызвана с правильным сообщением
        mock_send_main_menu.assert_called_once_with(callback_query.message)


@pytest.mark.asyncio
async def test_send_main_menu(message):
    """Тестируем, что send_main_menu правильно редактирует сообщение с клавиатурой"""

    # Используем фикстуру message для создания объекта с нужными аттрибутами
    mock_message = message(text="Старое сообщение")  # Текст сообщения
    mock_message.reply_markup = None  # Изначально не должно быть клавиатуры

    # Мокаем метод edit_text для проверки
    mock_message.edit_text = AsyncMock()

    # Вызываем send_main_menu
    await send_main_menu(mock_message)

    # Проверяем, что edit_text был вызван с нужными параметрами
    mock_message.edit_text.assert_called_once_with(
        "Выберите действие:", reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Посмотреть услуги", callback_data="services")],
                [InlineKeyboardButton(text="Мои записи", callback_data="my_bookings")]
            ]
        )
    )


@pytest.mark.asyncio
async def test_send_main_menu_message_not_modified(message):
    """Тестируем, что ошибка 'message is not modified' корректно обрабатывается"""

    # Используем фикстуру message для создания объекта с нужными аттрибутами
    mock_message = message(text="Some other text")
    mock_message.reply_markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Посмотреть услуги", callback_data="services")],
            [InlineKeyboardButton(text="Мои записи", callback_data="my_bookings")]
        ]
    )

    # Мокаем метод edit_text, чтобы он выбрасывал ошибку "message is not modified"
    mock_message.edit_text = AsyncMock(side_effect=TelegramBadRequest("message is not modified", "error"))

    # Проверяем, что при вызове функции будет выброшено исключение TelegramBadRequest с нужным сообщением
    with pytest.raises(TelegramBadRequest, match="Telegram server says - error"):
        # Вызываем send_main_menu и ожидаем, что будет выброшено исключение
        await send_main_menu(mock_message)

    # Проверяем, что edit_text был вызван только один раз
    mock_message.edit_text.assert_called_once()


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


@pytest.mark.asyncio
async def test_select_service_handler(callback_query, service, mock_db_session):
    # Мокируем запрос к базе данных
    mock_db_session.query().filter().first.return_value = service

    # Вызываем обработчик
    await select_service_handler(callback_query)

    # Проверяем, что данные о записи пользователя были сохранены
    assert user_booking_data[callback_query.from_user.id] == {
        "service_id": 1,
        "service_name": "Test Service",
        "service_duration": 30  # Проверяем, что продолжительность была сохранена
    }

    # Проверяем, что метод edit_text был вызван с нужными параметрами
    callback_query.message.edit_text.assert_called_once_with(
        "Как вы хотите продолжить?",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Выбрать мастера", callback_data="select_master")],
                [InlineKeyboardButton(text="Выбрать время (мастер не важен)", callback_data="select_time_no_master")],
                [InlineKeyboardButton(text="Назад", callback_data="services")],
                [InlineKeyboardButton(text="Назад в меню", callback_data="back_to_menu")],
            ]
        )
    )



@pytest.mark.asyncio
async def test_select_service_handler_db_query_called(callback_query, service, mock_db_session):
    """Проверка, что запрос к базе данных действительно был выполнен"""
    mock_db_session.query().filter().first.return_value = service

    # Вызываем обработчик
    await select_service_handler(callback_query)

    # Проверяем, что был сделан запрос к базе данных
    mock_db_session.query().filter().first.assert_called_once_with()