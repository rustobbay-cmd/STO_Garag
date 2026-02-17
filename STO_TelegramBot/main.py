import asyncio
import sqlite3
import logging
import os
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)

# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect("sto.db")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS orders 
                      (id INTEGER PRIMARY KEY, user_id INTEGER, name TEXT, phone TEXT, 
                       car TEXT, issue TEXT, service TEXT, date TEXT, time TEXT, duration INTEGER)''')
    conn.commit(); conn.close()

def get_busy_slots(date_str):
    conn = sqlite3.connect("sto.db")
    cursor = conn.cursor()
    cursor.execute("SELECT time, duration FROM orders WHERE date = ?", (date_str,))
    rows = cursor.fetchall()
    conn.close()
    
    busy = []
    for t_str, dur in rows:
        try:
            # Извлекаем час (например, из "10:00" получаем 10)
            start_h = int(t_str.split(':')[0])
            # Помечаем все часы занятыми согласно длительности
            for i in range(dur):
                busy.append(f"{start_h + i}:00")
        except:
            continue
    return busy

def has_free_slots(date_str, duration):
    busy = get_busy_slots(date_str)
    now = datetime.now()
    curr_hour = now.hour
    is_today = (date_str == now.strftime("%d.%m"))
    
    for h in range(9, 18):
        if is_today and h <= curr_hour: continue
        can_fit = True
        for i in range(duration):
            if f"{h+i}:00" in busy or (h+i) >= 18:
                can_fit = False; break
        if can_fit: return True
    return False

# --- СОСТОЯНИЯ ---
class Booking(StatesGroup):
    choosing_service = State()
    asking_car = State()
    asking_issue = State()
    choosing_date = State()
    choosing_time = State()
    waiting_phone = State()

async def main():
    init_db()
    dp = Dispatcher()

    def main_kb(uid):
        btns = [[types.KeyboardButton(text="🚗 Записаться")], [types.KeyboardButton(text="📅 Мои записи")]]
        if uid == ADMIN_ID: btns.append([types.KeyboardButton(text="📋 План работ (Админ)")])
        return types.ReplyKeyboardMarkup(keyboard=btns, resize_keyboard=True)

    @dp.message(Command("start"))
    async def cmd_start(message: types.Message):
        await message.answer("СТО Гараж приветствует вас! 🛠\nВыберите действие:", reply_markup=main_kb(message.from_user.id))

    @dp.message(F.text == "🚗 Записаться")
    async def start_booking(message: types.Message, state: FSMContext):
        kb = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="Развал-схождение", callback_data="svc_Развал_1")],
            [types.InlineKeyboardButton(text="Ремонт ходовой", callback_data="svc_Ходовая_2")]
        ])
        await message.answer("Какая услуга вас интересует?", reply_markup=kb)
        await state.set_state(Booking.choosing_service)

    @dp.callback_query(F.data.startswith("svc_"))
    async def svc_chosen(callback: types.CallbackQuery, state: FSMContext):
        _, name, dur = callback.data.split("_")
        dur = int(dur)
        await state.update_data(service=name, duration=dur)
        
        if name == "Развал":
            await state.update_data(car="Любая", issue="Плановый развал")
            now = datetime.now()
            date_btns = []
            for i in range(7):
                d_str = (now + timedelta(days=i)).strftime("%d.%m")
                if has_free_slots(d_str, dur):
                    date_btns.append([types.InlineKeyboardButton(text=d_str, callback_data=f"date_{d_str}")])
            if not date_btns:
                await callback.message.edit_text("Извините, на ближайшую неделю мест нет.")
                await state.clear()
            else:
                await callback.message.edit_text("Выберите дату:", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=date_btns))
                await state.set_state(Booking.choosing_date)
        else:
            await callback.message.edit_text("Напишите марку и модель авто:")
            await state.set_state(Booking.asking_car)

    @dp.message(Booking.asking_car)
    async def car_received(message: types.Message, state: FSMContext):
        await state.update_data(car=message.text)
        await message.answer("Что именно беспокоит по ходовой?")
        await state.set_state(Booking.asking_issue)

    @dp.message(Booking.asking_issue)
    async def issue_received(message: types.Message, state: FSMContext):
        await state.update_data(issue=message.text)
        data = await state.get_data()
        now = datetime.now()
        date_btns = []
        for i in range(7):
            d_str = (now + timedelta(days=i)).strftime("%d.%m")
            if has_free_slots(d_str, data['duration']):
                date_btns.append([types.InlineKeyboardButton(text=d_str, callback_data=f"date_{d_str}")])
        if not date_btns:
            await message.answer("Извините, на ближайшую неделю мест нет.")
            await state.clear()
        else:
            await message.answer("На какой день вас записать?", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=date_btns))
            await state.set_state(Booking.choosing_date)

    @dp.callback_query(F.data.startswith("date_"))
    async def date_chosen(callback: types.CallbackQuery, state: FSMContext):
        d_str = callback.data.replace("date_", "")
        await state.update_data(date=d_str)
        data = await state.get_data()
        
        # Получаем актуальный список занятых часов
        busy = get_busy_slots(d_str)
        
        now = datetime.now(); curr_hour = now.hour; is_today = (d_str == now.strftime("%d.%m"))
        time_btns = []; row = []
        for h in range(9, 18):
            if is_today and h <= curr_hour: continue
            
            # Проверяем, свободен ли этот час и последующие (если услуга долгая)
            can_fit = True
            for i in range(data['duration']):
                check_t = f"{h+i}:00"
                if check_t in busy or (h+i) >= 18:
                    can_fit = False; break
            
            if can_fit:
                row.append(types.InlineKeyboardButton(text=f"{h}:00", callback_data=f"t_{h}:00"))
                if len(row) == 3: time_btns.append(row); row = []
        if row: time_btns.append(row)
        
        await callback.message.edit_text(f"Свободное время на {d_str}:", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=time_btns))
        await state.set_state(Booking.choosing_time)

    @dp.callback_query(F.data.startswith("t_"))
    async def time_chosen(callback: types.CallbackQuery, state: FSMContext):
        await state.update_data(time=callback.data.replace("t_", ""))
        kb = types.ReplyKeyboardMarkup(keyboard=[[types.KeyboardButton(text="📱 Отправить контакт", request_contact=True)]], resize_keyboard=True)
        await callback.message.answer("Оставьте контакт для подтверждения:", reply_markup=kb)
        await state.set_state(Booking.waiting_phone)

    @dp.message(Booking.waiting_phone, F.contact)
    async def finish(message: types.Message, state: FSMContext):
        data = await state.get_data()
        conn = sqlite3.connect("sto.db"); cur = conn.cursor()
        cur.execute("INSERT INTO orders (user_id, name, phone, car, issue, service, date, time, duration) VALUES (?,?,?,?,?,?,?,?,?)", 
                    (message.from_user.id, message.from_user.full_name, message.contact.phone_number, data['car'], data['issue'], data['service'], data['date'], data['time'], data['duration']))
        conn.commit(); conn.close()
        await message.answer("✅ Записано! Ждем вас в Гараже.", reply_markup=main_kb(message.from_user.id))
        await bot.send_message(ADMIN_ID, f"⚡️ ЗАПИСЬ: {data['service']} на {data['date']} в {data['time']}\n🚗 {data['car']}\n👤 {message.from_user.full_name}\n📞 {message.contact.phone_number}")
        await state.clear()

    @dp.message(F.text == "📋 План работ (Админ)")
    async def admin_panel(message: types.Message):
        if message.from_user.id != ADMIN_ID: return
        conn = sqlite3.connect("sto.db"); cur = conn.cursor()
        cur.execute("SELECT id, date, time, service, car, duration, phone, name FROM orders ORDER BY date, time")
        rows = cur.fetchall(); conn.close()
        if not rows: await message.answer("План пуст."); return
        for r in rows:
            if r[3] == "Ходовая":
                kb = types.InlineKeyboardMarkup(inline_keyboard=[[
                    types.InlineKeyboardButton(text="➕ Продлить", callback_data=f"edit_{r[0]}_1"),
                    types.InlineKeyboardButton(text="✅ Завершить", callback_data=f"done_{r[0]}")
                ]])
                await message.answer(f"🕒 {r[7]} {r[1]} — Ремонт ходовой ({r[2]})\n🚗 {r[4]} ({r[5]}ч)\n📞 {r[6]}", reply_markup=kb)
            else:
                await message.answer(f"🕒 {r[7]} {r[1]} — Развал-схождение ({r[2]})\n🚗 {r[4]}\n📞 {r[6]}")

    @dp.callback_query(F.data.startswith("edit_"))
    async def edit_duration(callback: types.CallbackQuery):
        _, oid, val = callback.data.split("_")
        conn = sqlite3.connect("sto.db"); cur = conn.cursor()
        cur.execute("UPDATE orders SET duration = duration + ? WHERE id = ?", (int(val), int(oid)))
        conn.commit(); conn.close()
        await callback.answer("Время продлено")
        await callback.message.edit_text(callback.message.text + "\n⚠️ ПРОДЛЕНО")

    @dp.callback_query(F.data.startswith("done_"))
    async def complete_order(callback: types.CallbackQuery):
        oid = callback.data.replace("done_", "")
        conn = sqlite3.connect("sto.db"); cur = conn.cursor()
        cur.execute("DELETE FROM orders WHERE id = ?", (int(oid),))
        conn.commit(); conn.close()
        await callback.message.edit_text("✅ Работа завершена.")

    @dp.message(F.text == "📅 Мои записи")
    async def my_orders(message: types.Message):
        conn = sqlite3.connect("sto.db"); cur = conn.cursor()
        cur.execute("SELECT id, date, time, service FROM orders WHERE user_id = ?", (message.from_user.id,))
        rows = cur.fetchall(); conn.close()
        if not rows: await message.answer("У вас нет активных записей."); return
        for r in rows:
            kb = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="❌ Отменить", callback_data=f"del_{r[0]}")]] )
            await message.answer(f"📅 {r[1]} в {r[2]} — {r[3]}", reply_markup=kb)

    @dp.callback_query(F.data.startswith("del_"))
    async def delete_order(callback: types.CallbackQuery):
        oid = callback.data.replace("del_", "")
        conn = sqlite3.connect("sto.db"); cur = conn.cursor()
        cur.execute("DELETE FROM orders WHERE id = ?", (int(oid),)); conn.commit(); conn.close()
        await callback.message.edit_text("❌ Запись отменена.")

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())














