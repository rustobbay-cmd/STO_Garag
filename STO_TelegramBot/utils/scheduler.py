from datetime import datetime, timedelta

def get_free_slots(existing_apps, duration_hours):
    # Рабочий день 9:00 - 18:00
    day_start = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
    day_end = day_start.replace(hour=18)
    
    slots = []
    current_time = day_start
    step = timedelta(minutes=30) # Предлагаем время каждые 30 мин
    needed = timedelta(hours=duration_hours)

    while current_time + needed <= day_end:
        # Проверка: не занято ли это время?
        is_free = True
        for app in existing_apps:
            app_end = app.start_time + timedelta(hours=app.duration)
            # Пересечение интервалов
            if not (current_time + needed <= app.start_time or current_time >= app_end):
                is_free = False
                break
        
        if is_free and current_time > datetime.now():
            slots.append(current_time)
        current_time += step
        
    return slots
