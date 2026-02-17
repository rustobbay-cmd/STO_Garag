from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# Главное меню
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🚗 Записаться на ремонт")],
        [KeyboardButton(text="📅 Мои записи"), KeyboardButton(text="📞 Контакты")]
    ],
    resize_keyboard=True
)

# Выбор услуги
services_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Развал-схождение (1 ч)", callback_data="svc_razval")],
        [InlineKeyboardButton(text="Ремонт ходовой (расчет по факту)", callback_data="svc_hodo_fast")],
        [InlineKeyboardButton(text="Комплексная диагностика (0.5 ч)", callback_data="svc_diag")]
    ]
)

# Функция для генерации слотов времени
def get_time_slots_kb(slots):
    buttons = []
    for slot in slots:
        # Форматируем время для кнопки
        time_str = slot.strftime("%H:%M")
        buttons.append([InlineKeyboardButton(text=time_str, callback_data=f"time_{time_str}")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)
