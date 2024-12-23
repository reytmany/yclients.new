import pytest
from unittest.mock import AsyncMock, patch
from aiogram import Bot
from datetime import datetime
from master_bot import delete_send_telegram_notification


@pytest.mark.asyncio
async def test_delete_send_telegram_notification_success():
    # Мокаем возвращаемые значения для get_telegram_id_by_master_id и get_username_by_telegram_id
    mock_master_telegram_id = 12345
    mock_username = "Test User"

    booking_data = {
        "slot_time": datetime(2024, 12, 22, 15, 0),  # Время, когда назначена запись
        "service_name": "Test Service"
    }

    # Мокаем функцию get_telegram_id_by_master_id
    with patch("master_bot.get_telegram_id_by_master_id", return_value=mock_master_telegram_id):
        # Мокаем функцию get_username_by_telegram_id
        with patch("master_bot.get_username_by_telegram_id", return_value=mock_username):
            # Мокаем бот и его метод send_message
            mock_bot = AsyncMock()
            with patch.object(Bot, 'send_message', mock_bot.send_message):
                # Вызываем функцию с нужными аргументами
                await delete_send_telegram_notification(
                    1, 123456789, booking_data["slot_time"], booking_data["service_name"]
                )

                # Проверяем, что метод send_message был вызван с ожидаемым сообщением
                mock_bot.send_message.assert_awaited_once_with(
                    chat_id=mock_master_telegram_id,
                    text=(
                        "У вас отмена записи на 22-12 15:00\n"
                        "Услуга: Test Service\n"
                        "Клиент: Test User"
                    )
                )


@pytest.mark.asyncio
async def test_delete_send_telegram_notification_master_not_found():
    # Мокаем, что get_telegram_id_by_master_id возвращает None
    with patch("master_bot.get_telegram_id_by_master_id", return_value=None):
        # Мокаем get_username_by_telegram_id
        with patch("master_bot.get_username_by_telegram_id", return_value="Test User"):
            # Мокаем бот
            mock_bot = AsyncMock()
            with patch.object(Bot, 'send_message', mock_bot.send_message):
                # Передаем словарь с валидным slot_time (объект datetime)
                booking_data = {
                    "slot_time": datetime(2024, 12, 22, 15, 30),  # Пример времени
                    "service_name": "Test Service"
                }
                # Вызываем функцию с правильными параметрами
                await delete_send_telegram_notification(
                    1, 123456789, booking_data["slot_time"], booking_data["service_name"]
                )

                # Проверяем, что send_message не был вызван
                mock_bot.send_message.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_send_telegram_notification_send_message_error():
    # Мокаем возвращаемые значения для get_telegram_id_by_master_id и get_username_by_telegram_id
    mock_master_telegram_id = 12345
    mock_username = "Test User"

    booking_data = {
        "slot_time": datetime(2024, 12, 22, 15, 0),  # Примерная дата и время записи
        "service_name": "Test Service"
    }

    # Мокаем функцию get_telegram_id_by_master_id
    with patch("master_bot.get_telegram_id_by_master_id", return_value=mock_master_telegram_id):
        # Мокаем функцию get_username_by_telegram_id
        with patch("master_bot.get_username_by_telegram_id", return_value=mock_username):
            # Мокаем бот и его метод send_message, чтобы он вызывал ошибку
            mock_bot = AsyncMock()
            mock_bot.send_message.side_effect = Exception("Telegram API error")
            with patch.object(Bot, 'send_message', mock_bot.send_message):
                # Передаем данные из booking_data по отдельности
                await delete_send_telegram_notification(
                    1,
                    12345,
                    booking_data["slot_time"],  # Передаем slot_time
                    booking_data["service_name"]  # Передаем service_name
                )

                # Проверяем, что send_message был вызван
                mock_bot.send_message.assert_awaited_once()


