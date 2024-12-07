import pytest
from unittest.mock import MagicMock, AsyncMock
from aiogram import types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from bot import  user_booking_data, handle_unrecognized_message
from database import Service

@pytest.mark.asyncio
async def test_user_has_chosen_service():
    """Тест на случай, когда пользователь уже выбрал услугу."""

    # Создаем мок-объект для сообщения
    mock_message = MagicMock(spec=types.Message)

    # Мокаем from_user
    mock_from_user = MagicMock(spec=types.User)
    mock_from_user.id = 12345  # Устанавливаем ID пользователя
    mock_from_user.first_name = "Test User"  # Устанавливаем имя пользователя
    mock_message.from_user = mock_from_user  # Присваиваем mock_from_user в from_user

    mock_message.text = "Some unrecognized message"  # Мокаем текст сообщения
    mock_message.answer = AsyncMock()  # Мокаем метод answer

    # Мокаем данные о выборе услуги
    user_booking_data[12345] = {'service_id': 1}

    # Мокаем наличие услуги в базе данных
    service = MagicMock(spec=Service)
    service.id = 1
    service.name = "Test Service"
    service.cost = 100

    # Вызовем обработчик
    await handle_unrecognized_message(mock_message)

    # Ожидаем, что будет отправлено сообщение с нужными кнопками
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Выбрать мастера", callback_data="select_master")],
            [InlineKeyboardButton(text="Выбрать время (мастер не важен)", callback_data="select_time_no_master")],
            [InlineKeyboardButton(text="Назад", callback_data="services")],
            [InlineKeyboardButton(text="Назад в меню", callback_data="back_to_menu")]
        ]
    )
    new_text = "Как вы хотите продолжить?"

    # Проверяем, что метод answer был вызван с правильным текстом и клавиатурой
    mock_message.answer.assert_any_call("Используйте кнопки для выбора.")
    mock_message.answer.assert_any_call(new_text, reply_markup=keyboard)
