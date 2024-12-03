import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from aiogram import types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from aiogram.exceptions import TelegramBadRequest
from bot import first_interaction, start_handler, send_main_menu, back_to_menu_handler, select_service_handler, user_booking_data, select_master_handler, show_calendar_for_master, show_calendar_no_master, show_calendar, change_week_handler, date_selected_handler
from database import Service, Master
from datetime import datetime, timedelta

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
def master():
    """Фикстура для создания мок-объекта Master"""
    mock_master = MagicMock(spec=Master)
    mock_master.id = 1
    mock_master.name = "Test Master"
    mock_master.rating = 4.8
    return mock_master

@pytest.fixture
def callback_query(message):
    """Фикстура для создания мок-объекта callback_query"""
    mock_callback_query = MagicMock(spec=CallbackQuery)
    mock_callback_query.data = "service_1"  # Убедитесь, что данные правильные
    mock_callback_query.message = message(text="Some text")
    mock_callback_query.from_user = MagicMock(id=12345)
    return mock_callback_query


@pytest.fixture
def service(master):
    """Фикстура для создания мок-объекта Service с мастерами"""
    mock_service = MagicMock(spec=Service)
    mock_service.id = 1
    mock_service.name = "Test Service"
    mock_service.duration = 30  # Пример продолжительности услуги
    mock_service.masters = [master]
    return mock_service



@pytest.fixture
def mock_db_session(service):
    """Фикстура для мокирования сессии базы данных"""
    with patch('bot.SessionLocal') as mock_session_local:
        mock_session = MagicMock()
        mock_session_local.return_value.__enter__.return_value = mock_session

        # Настраиваем query().filter().first() на возврат mock_service
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value.first.return_value = service
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

@pytest.mark.asyncio
async def test_select_master_handler_with_masters(callback_query, service, master, mock_db_session):
    """Тестируем обработчик с мастерами"""
    user_booking_data[callback_query.from_user.id] = {
        "service_id": service.id,
    }

    # Вызываем обработчик
    await select_master_handler(callback_query)

    # Проверяем, что edit_text был вызван с правильными параметрами
    callback_query.message.edit_text.assert_called_once_with(
        "Выберите мастера:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(
                    text=f"{master.name} (Рейтинг: {master.rating})",
                    callback_data=f"master_{master.id}"
                )],
                [InlineKeyboardButton(text="Назад", callback_data=f"service_{service.id}")],
                [InlineKeyboardButton(text="Назад в меню", callback_data="back_to_menu")]
            ]
        )
    )


@pytest.mark.asyncio
async def test_select_master_handler_without_masters(callback_query, service, mock_db_session):
    """Тестируем обработчик без мастеров (пустой список мастеров)"""

    # Убираем мастеров из услуги
    service.masters = []

    user_booking_data[callback_query.from_user.id] = {
        "service_id": service.id,  # Записываем идентификатор услуги в словарь
    }

    # Вызываем обработчик
    await select_master_handler(callback_query)

    # Проверяем, что edit_text был вызван с правильными параметрами
    callback_query.message.edit_text.assert_called_once_with(
        "Выберите мастера:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Назад", callback_data=f"service_{service.id}")],
                [InlineKeyboardButton(text="Назад в меню", callback_data="back_to_menu")]
            ]
        )
    )




@pytest.mark.asyncio
async def test_select_master_handler_telegram_error(callback_query, service, master, mock_db_session):
    """Тестируем обработчик, когда возникает ошибка TelegramBadRequest при редактировании сообщения"""

    user_booking_data[callback_query.from_user.id] = {
        "service_id": service.id,
    }

    # Мокаем ошибку при редактировании сообщения
    callback_query.message.edit_text.side_effect = TelegramBadRequest("Telegram server says",
                                                                      "Detailed error description")

    try:
        # Вызываем обработчик
        await select_master_handler(callback_query)
    except TelegramBadRequest as e:
        # Проверяем оба аргумента, переданные в исключение
        assert e.args == ("Telegram server says", "Detailed error description")

        # Проверка, что метод edit_text был вызван с правильными параметрами
        callback_query.message.edit_text.assert_called_once_with(
            "Выберите мастера:",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text=f"{master.name} (Рейтинг: {master.rating})",
                                          callback_data=f"master_{master.id}")],
                    [InlineKeyboardButton(text="Назад", callback_data=f"service_{service.id}")],
                    [InlineKeyboardButton(text="Назад в меню", callback_data="back_to_menu")]
                ]
            )
        )


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

    # Ensure today is a known fixed date for testing, e.g., Dec 3, 2024
    today = datetime(2024, 12, 3).date()

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

    # Проверка
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
    # Настройка
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

    # Проверка
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
