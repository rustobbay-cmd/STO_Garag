from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.db_manager import add_appointment, get_today_appointments
from utils.scheduler import get_free_slots

router = Router()

class Form(StatesGroup):
    choosing_service = State()
    choosing_time = State()
    waiting_phone = State()

@router.message(F.text == "/start")
async def start(message: Message):
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Записаться")]], resize_keyboard=True)
    await message.answer("СТО приветствует вас! Нажмите кнопку ниже:", reply_markup=kb)

@router.message(F.text == "Записаться")
async def choose_svc(message: Message, state: FSMContext):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Развал (1ч)", callback_data="svc_Развал_1")],
        [InlineKeyboardButton(text="Ходовая (2ч+)", callback_data="svc_Ходовая_2.5")]
    ])
    await message.answer("Что будем чинить?", reply_markup=kb)
    await state.set_state(Form.choosing_service)

@router.callback_query(Form.choosing_service)
async def svc_callback(callback: CallbackQuery, state: FSMContext):
    _, name, dur = callback.data.split("_")
    await state.update_data(svc=name, duration=float(dur))
    
    # Получаем свободные слоты
    apps = await get_today_appointments()
    slots = get_free_slots(apps, float(dur))
    
    buttons = [[InlineKeyboardButton(text=s.strftime("%H:%M"), callback_data=f"t_{s.strftime('%H:%M')}")] for s in slots]
    await callback.message.edit_text("Выберите время:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await state.set_state(Form.choosing_time)

@router.callback_query(Form.choosing_time)
async def time_callback(callback: CallbackQuery, state: FSMContext):
    time_val = callback.data.replace("t_", "")
    await state.update_data(time=time_val)
    
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📱 Отправить контакт", request_contact=True)]], resize_keyboard=True)
    await callback.message.answer("Оставьте номер телефона для подтверждения:", reply_markup=kb)
    await state.set_state(Form.waiting_phone)

@router.message(Form.waiting_phone, F.contact)
async def finish(message: Message, state: FSMContext):
    data = await state.get_data()
    # Собираем дату
    dt_str = f"{datetime.datetime.now().strftime('%Y-%m-%d')} {data['time']}"
    start_dt = datetime.datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
    
    await add_appointment(message.from_user.full_name, message.contact.phone_number, data['svc'], start_dt, data['duration'])
    
    await message.answer(f"✅ Записали! {data['svc']} на {data['time']}.", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Записаться")]], resize_keyboard=True))
    await state.clear()

