import pytest
from unittest.mock import AsyncMock, patch
from aiogram.types import ChatMember, User
from master_bot import get_username_by_telegram_id  # Импортируем функцию для тестирования


@pytest.mark.asyncio
async def test_get_username_by_telegram_id_with_first_name():
    # Создаем мок для пользователя (User)
    mock_user = User(id=12345, is_bot=False, first_name="Fedya", username=None)

    # Создаем мок для chat_member
    mock_chat_member = ChatMember(user=mock_user, status="member")

    # Мокаем метод get_chat_member
    mock_get_chat_member = AsyncMock(return_value=mock_chat_member)

    # Используем patch для замены метода Bot.get_chat_member на мок
    with patch("aiogram.Bot.get_chat_member", mock_get_chat_member):
        username = await get_username_by_telegram_id(12345)  # Передаем только telegram_id
        assert username == "Fedya"

@pytest.mark.asyncio
async def test_get_username_by_telegram_id_with_username():
    # Создаем мок для пользователя (User)
    mock_user = User(id=12345, is_bot=False, first_name="", username="f.buzaev")

    # Создаем мок для chat_member
    mock_chat_member = ChatMember(user=mock_user, status="member")

    # Мокаем метод get_chat_member
    mock_get_chat_member = AsyncMock(return_value=mock_chat_member)

    # Используем patch для замены метода Bot.get_chat_member на мок
    with patch("aiogram.Bot.get_chat_member", mock_get_chat_member):
        username = await get_username_by_telegram_id(12345)
        assert username == "f.buzaev"

@pytest.mark.asyncio
async def test_get_username_by_telegram_id_with_no_name_or_username():
    # Создаем мок для пользователя (User)
    mock_user = User(id=12345, is_bot=False, first_name="", username="")

    # Создаем мок для chat_member
    mock_chat_member = ChatMember(user=mock_user, status="member")

    # Мокаем метод get_chat_member
    mock_get_chat_member = AsyncMock(return_value=mock_chat_member)

    # Используем patch для замены метода Bot.get_chat_member на мок
    with patch("aiogram.Bot.get_chat_member", mock_get_chat_member):
        username = await get_username_by_telegram_id(12345)
        assert username == "12345"