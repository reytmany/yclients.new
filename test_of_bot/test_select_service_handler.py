import pytest
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from bot import select_service_handler, user_booking_data

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
