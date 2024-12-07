import pytest
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.exceptions import TelegramBadRequest
from bot import user_booking_data, select_master_handler

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