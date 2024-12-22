from datetime import timedelta
from database import TimeSlotStatus

def find_available_slots(slots, service_duration):
    required_slots = service_duration // 15
    available_slots = []
    i = 0
    while i < len(slots):
        master_id = slots[i].master_id
        start_index = i
        end_index = i + required_slots
        consecutive_slots = slots[start_index:end_index]

        if len(consecutive_slots) < required_slots:
            i += 1
            continue

        is_consecutive = True
        for j in range(required_slots - 1):
            if (consecutive_slots[j + 1].start_time != consecutive_slots[j].start_time + timedelta(minutes=15) or
                    consecutive_slots[j + 1].status != TimeSlotStatus.free or
                    consecutive_slots[j + 1].master_id != master_id):
                is_consecutive = False
                break

        if is_consecutive:
            available_slots.append(consecutive_slots[0])
            i += required_slots  # Пропускаем проверенные слоты
        else:
            i += 1
    return available_slots
