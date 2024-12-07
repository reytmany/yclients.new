import pytest
from unittest.mock import AsyncMock
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from bot import send_main_menu
from aiogram.exceptions import TelegramBadRequest

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