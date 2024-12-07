import pytest
from unittest.mock import AsyncMock
from aiogram import types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from bot import first_interaction

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
