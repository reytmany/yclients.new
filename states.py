# states.py

from aiogram.fsm.state import State, StatesGroup

class BookingStates(StatesGroup):
    selecting_service = State()
    selecting_master = State()
    selecting_date = State()
    selecting_time = State()
    confirming = State()
