from bot import find_available_slots
from datetime import datetime

def test_find_available_slots_sufficient_consecutive_slots(timeslot):
    """Тест на достаточное количество последовательных слотов."""
    master_id = 1
    slots = [
        timeslot(master_id, datetime(2024, 12, 4, 10, 0)),
        timeslot(master_id, datetime(2024, 12, 4, 10, 15)),
        timeslot(master_id, datetime(2024, 12, 4, 10, 30)),
    ]
    service_duration = 30  # Требуется 2 слота
    result = find_available_slots(slots, service_duration)
    assert len(result) == 1
    assert result[0].start_time == datetime(2024, 12, 4, 10, 0)


def test_find_available_slots_insufficient_slots(timeslot):
    """Тест на недостаточное количество слотов."""
    master_id = 1
    slots = [
        timeslot(master_id, datetime(2024, 12, 4, 10, 0)),
        timeslot(master_id, datetime(2024, 12, 4, 10, 15)),
    ]
    service_duration = 45  # Требуется 3 слота
    result = find_available_slots(slots, service_duration)
    assert len(result) == 0


def test_find_available_slots_mixed_masters(timeslot):
    """Тест на наличие разных мастеров в слоте."""
    slots = [
        timeslot(1, datetime(2024, 12, 4, 10, 0)),
        timeslot(2, datetime(2024, 12, 4, 10, 15)),  # Другой мастер
        timeslot(1, datetime(2024, 12, 4, 10, 30)),
    ]
    service_duration = 30  # Требуется 2 слота
    result = find_available_slots(slots, service_duration)
    assert len(result) == 0