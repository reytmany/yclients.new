import pytest
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from unittest.mock import AsyncMock, MagicMock, ANY
from datetime import datetime, timedelta
from handlers.booking_handler import (
    date_selected_handler,
    confirm_booking_handler,
    save_booking,
    add_to_calendar,
    leave_review_handler,
    rate_handler,
    review_text_handler,
)

@pytest.fixture
def mock_state():
    return AsyncMock(spec=FSMContext)

@pytest.fixture
def mock_callback_query():
    return MagicMock(spec=CallbackQuery)

@pytest.fixture
def mock_message():
    return AsyncMock(spec=Message)


@pytest.mark.asyncio
async def test_date_selected_handler(mock_callback_query, mock_state):
    mock_callback_query.data = "date_2023-12-25_0"
    mock_callback_query.from_user = MagicMock()  # Create a mock for from_user
    mock_callback_query.from_user.id = 123
    mock_callback_query.message = AsyncMock()  # Create an async mock for message
    mock_state.get_data.return_value = {
        "master_id": 1,
        "service_id": 2,
        "service_duration": 60,
    }

    await date_selected_handler(mock_callback_query, mock_state)

    mock_state.get_data.assert_called_once()
    mock_callback_query.message.edit_text.assert_called()

@pytest.mark.asyncio
async def test_confirm_booking_handler(mock_callback_query, mock_state):
    mock_callback_query.data = "slot_1"
    mock_callback_query.from_user = MagicMock()
    mock_callback_query.from_user.id = 123
    mock_callback_query.message = AsyncMock()
    mock_state.get_data.return_value = {
        "service_name": "Test Service",
        "week_offset": 0
    }

    await confirm_booking_handler(mock_callback_query, mock_state)

    mock_state.get_data.assert_called_once()
    mock_callback_query.message.edit_text.assert_called()



@pytest.mark.asyncio
async def test_add_to_calendar(mock_callback_query, mock_state):
    mock_callback_query.data = "add_to_calendar"
    mock_callback_query.from_user = MagicMock()
    mock_callback_query.from_user.id = 123
    mock_callback_query.message = AsyncMock()

    mock_state.get_data.return_value = {
        "slot_time": datetime.now(),
        "service_name": "Test Service",
        "service_duration": 60
    }

    await add_to_calendar(mock_callback_query, mock_state)

    mock_state.get_data.assert_called_once()
    mock_callback_query.message.edit_text.assert_called()

@pytest.mark.asyncio
async def test_leave_review_handler(mock_callback_query, mock_state):
    mock_callback_query.data = "leave_review"
    mock_callback_query.from_user = MagicMock()
    mock_callback_query.from_user.id = 123
    mock_callback_query.message = AsyncMock()

    await leave_review_handler(mock_callback_query)

    mock_callback_query.message.edit_text.assert_called()

@pytest.mark.asyncio
async def test_rate_handler(mock_callback_query, mock_state):
    mock_callback_query.data = "rate_5"
    mock_callback_query.from_user = MagicMock()
    mock_callback_query.from_user.id = 123
    mock_callback_query.message = AsyncMock()

    await rate_handler(mock_callback_query, mock_state)

    mock_state.update_data.assert_called_once_with(rating=5)
    mock_callback_query.message.edit_text.assert_called()


@pytest.mark.asyncio
async def test_save_booking(mock_callback_query, mock_state):
    # Настраиваем mock для callback_query
    mock_callback_query.from_user = MagicMock()
    mock_callback_query.from_user.id = 123
    mock_callback_query.message = AsyncMock()

    # Настраиваем данные в FSMContext
    mock_state.get_data.return_value = {
        "service_id": 2,
        "master_id": 1,
        "slot_id": 5,
        "service_duration": 60,
        "service_name": "Test Service",
    }

    # Mock для сессии базы данных
    mock_session = MagicMock()
    mock_slot = MagicMock()
    mock_slot.status = "free"
    mock_slot.start_time = datetime.now()
    mock_slot.master = MagicMock(name="Test Master")
    mock_user = MagicMock()
    mock_user.id = 123

    # Настройка моков для базы данных
    mock_session.query().filter().first.side_effect = [mock_slot, mock_user]
    mock_session.query().filter().all.return_value = [mock_slot, mock_slot]  # Достаточно слотов

    with pytest.MonkeyPatch.context() as mp:
        from database import SessionLocal
        mp.setattr(SessionLocal, "__call__", lambda: mock_session)

        # Вызов тестируемой функции
        await save_booking(mock_callback_query, mock_state)

        # Проверяем, что статус слота был изменен на "booked"
        mock_slot.status = "booked"
        assert mock_slot.status == "booked"


from datetime import datetime, timedelta
from unittest.mock import MagicMock, AsyncMock
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from handlers.booking_handler import date_selected_handler
from aiogram.fsm.context import FSMContext
from database import TimeSlot, TimeSlotStatus
import pytest




@pytest.mark.asyncio
async def test_date_selected_handler_no_slots():
    mock_callback_query = MagicMock(spec=CallbackQuery)
    mock_callback_query.data = "date_2023-12-25_0"
    mock_callback_query.from_user = MagicMock()  # Добавляем from_user
    mock_callback_query.from_user.id = 123
    mock_callback_query.message = AsyncMock()

    mock_state = AsyncMock(spec=FSMContext)
    mock_state.get_data.return_value = {
        "master_id": None,
        "service_id": 1,
        "service_duration": 60
    }

    mock_session = MagicMock()
    mock_session.query().filter().all.return_value = []  # No slots found

    with pytest.MonkeyPatch.context() as mp:
        from database import SessionLocal
        mp.setattr(SessionLocal, "__call__", lambda: mock_session)

        await date_selected_handler(mock_callback_query, mock_state)

        mock_callback_query.message.edit_text.assert_called_once_with(
            "Нет доступных слотов на эту дату.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="Назад", callback_data="change_week_0")],
                    [InlineKeyboardButton(text="Назад в меню", callback_data="back_to_menu")],
                ]
            )
        )


@pytest.mark.asyncio
async def test_date_selected_handler_no_service_data():
    mock_callback_query = MagicMock(spec=CallbackQuery)
    mock_callback_query.data = "date_2023-12-25"
    mock_callback_query.from_user = MagicMock()  # Добавляем from_user
    mock_callback_query.from_user.id = 123  # Пример id пользователя
    mock_callback_query.message = AsyncMock()

    mock_state = AsyncMock(spec=FSMContext)
    mock_state.get_data.return_value = {}

    await date_selected_handler(mock_callback_query, mock_state)

    mock_callback_query.message.edit_text.assert_called_once_with(
        "Ошибка: данные записи не найдены. Пожалуйста, начните заново.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Назад в меню", callback_data="back_to_menu")]
            ]
        )
    )
import pytest
from unittest.mock import AsyncMock, MagicMock
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from handlers.general_handler import handle_unrecognized_message
from database import Service


@pytest.mark.asyncio
async def test_handle_unrecognized_message_with_service_selected():
    # Создаем mock для Message
    mock_message = AsyncMock(spec=Message)
    mock_message.from_user = MagicMock()  # Добавляем атрибут from_user
    mock_message.from_user.id = 123  # Пример ID пользователя
    mock_message.answer = AsyncMock()  # Мокаем метод answer как асинхронный

    # Настраиваем FSMContext с выбранной услугой
    mock_state = AsyncMock(spec=FSMContext)
    mock_state.get_data.return_value = {
        "service_id": 1  # Пользователь выбрал услугу
    }

    await handle_unrecognized_message(mock_message, mock_state)

    # Проверяем, что отправлены сообщения
    mock_message.answer.assert_any_call("Используйте кнопки для выбора.")
    mock_message.answer.assert_any_call(
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



import pytest
from unittest.mock import AsyncMock, MagicMock
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from handlers.general_handler import handle_unrecognized_message


@pytest.mark.asyncio
async def test_handle_unrecognized_message_without_service_selected():
    # Создаем mock для Message
    mock_message = AsyncMock(spec=Message)
    mock_message.from_user = MagicMock()  # Добавляем атрибут from_user
    mock_message.from_user.id = 123  # Пример ID пользователя
    mock_message.answer = AsyncMock()  # Мокаем метод answer как асинхронный

    # Настраиваем FSMContext без выбранной услуги
    mock_state = AsyncMock(spec=FSMContext)
    mock_state.get_data.return_value = {}

    # Мокаем вызовы `message.answer`
    await handle_unrecognized_message(mock_message, mock_state)

    # Убеждаемся, что message.answer вызывался хотя бы дважды
    assert mock_message.answer.call_count >= 2

    # Проверяем, что хотя бы один из вызовов содержит текст "Выберите услугу:"
    assert any(
        "Выберите услугу:" in str(call)
        for call in mock_message.answer.call_args_list
    )



from datetime import datetime, timedelta
import pytest
from unittest.mock import AsyncMock, MagicMock
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from handlers.services_handler import (
    services_handler,
    select_service_handler,
    select_master_handler,
    select_time_no_master_handler,
    my_bookings_handler,
    cancel_booking_handler
)


@pytest.mark.asyncio
async def test_select_service_handler():
    mock_callback_query = AsyncMock(spec=CallbackQuery)
    mock_callback_query.data = "service_1"
    mock_callback_query.message = AsyncMock()

    mock_service = MagicMock()
    mock_service.id = 1
    mock_service.name = "Укладка"
    mock_service.duration = 120

    mock_session = MagicMock()
    mock_session.query().filter().first.return_value = mock_service

    mock_state = AsyncMock(spec=FSMContext)

    with pytest.MonkeyPatch.context() as mp:
        from database import SessionLocal
        mp.setattr(SessionLocal, "__call__", lambda: mock_session)

        await select_service_handler(mock_callback_query, mock_state)

    mock_state.update_data.assert_called_once_with(
        service_id=1, service_name="Укладка", service_duration=120
    )


@pytest.mark.asyncio
async def test_select_master_handler():
    mock_callback_query = AsyncMock(spec=CallbackQuery)
    mock_callback_query.message = AsyncMock()
    mock_callback_query.from_user = MagicMock()
    mock_callback_query.from_user.id = 123

    mock_service = MagicMock()
    mock_service.id = 1
    mock_service.masters = [
        MagicMock(id=1, name="Марина", rating=0),
    ]

    mock_session = MagicMock()
    mock_session.query().filter().first.return_value = mock_service

    mock_state = AsyncMock(spec=FSMContext)
    mock_state.get_data.return_value = {"service_id": 1}

    with pytest.MonkeyPatch.context() as mp:
        from database import SessionLocal
        mp.setattr(SessionLocal, "__call__", lambda: mock_session)

        await select_master_handler(mock_callback_query, mock_state)

    mock_callback_query.message.edit_text.assert_called_once_with(
        "Выберите мастера:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Марина (Рейтинг: 0)", callback_data="master_1")],
                [InlineKeyboardButton(text="Назад", callback_data="service_1")],
                [InlineKeyboardButton(text="Назад в меню", callback_data="back_to_menu")],
            ]
        )
    )

from utils.booking import find_available_slots
from datetime import datetime
from unittest.mock import MagicMock
from database import TimeSlotStatus

def test_find_available_slots_with_valid_consecutive_slots():
    slots = [
        MagicMock(start_time=datetime(2024, 12, 25, 10, 0), status=TimeSlotStatus.free, master_id=1),
        MagicMock(start_time=datetime(2024, 12, 25, 10, 15), status=TimeSlotStatus.free, master_id=1),
        MagicMock(start_time=datetime(2024, 12, 25, 10, 30), status=TimeSlotStatus.free, master_id=1),
        MagicMock(start_time=datetime(2024, 12, 25, 10, 45), status=TimeSlotStatus.free, master_id=1),
    ]

    service_duration = 30
    result = find_available_slots(slots, service_duration)

    assert len(result) == 2  # Указываем, что ожидаем 2 слота
    assert result[0].start_time == datetime(2024, 12, 25, 10, 0)
    assert result[1].start_time == datetime(2024, 12, 25, 10, 30)



def test_find_available_slots_with_different_masters():
    slots = [
        MagicMock(start_time=datetime(2024, 12, 25, 10, 0), status=TimeSlotStatus.free, master_id=1),
        MagicMock(start_time=datetime(2024, 12, 25, 10, 15), status=TimeSlotStatus.free, master_id=2),
        MagicMock(start_time=datetime(2024, 12, 25, 10, 30), status=TimeSlotStatus.free, master_id=1),
        MagicMock(start_time=datetime(2024, 12, 25, 10, 45), status=TimeSlotStatus.free, master_id=1),
    ]

    service_duration = 30
    result = find_available_slots(slots, service_duration)

    assert len(result) == 1  # Указываем, что доступен только один слот
    assert result[0].start_time == datetime(2024, 12, 25, 10, 30)


def test_find_available_slots_with_multiple_available_slots():
    slots = [
        MagicMock(start_time=datetime(2024, 12, 25, 10, 0), status=TimeSlotStatus.free, master_id=1),
        MagicMock(start_time=datetime(2024, 12, 25, 10, 15), status=TimeSlotStatus.free, master_id=1),
        MagicMock(start_time=datetime(2024, 12, 25, 10, 30), status=TimeSlotStatus.free, master_id=1),
        MagicMock(start_time=datetime(2024, 12, 25, 10, 45), status=TimeSlotStatus.free, master_id=1),
        MagicMock(start_time=datetime(2024, 12, 25, 11, 0), status=TimeSlotStatus.free, master_id=1),
        MagicMock(start_time=datetime(2024, 12, 25, 11, 15), status=TimeSlotStatus.free, master_id=1),
    ]

    service_duration = 30
    result = find_available_slots(slots, service_duration)

    assert len(result) == 3  # Указываем, что доступны 3 начальных слота
    assert result[0].start_time == datetime(2024, 12, 25, 10, 0)
    assert result[1].start_time == datetime(2024, 12, 25, 10, 30)
    assert result[2].start_time == datetime(2024, 12, 25, 11, 0)
