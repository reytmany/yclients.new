import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from aiogram import types
from aiogram.types import CallbackQuery
from database import Service, Master, TimeSlotStatus

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

@pytest.fixture
def timeslot():
    """Фикстура для создания мок-объекта TimeSlot."""
    def _timeslot(master_id, start_time, status=TimeSlotStatus.free):
        mock_slot = MagicMock()
        mock_slot.master_id = master_id
        mock_slot.start_time = start_time
        mock_slot.status = status
        return mock_slot
    return _timeslot
