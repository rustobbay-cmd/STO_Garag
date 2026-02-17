def init_db():
    conn = sqlite3.connect("sto.db")
    cursor = conn.cursor()
    # ПРИНУДИТЕЛЬНО УДАЛЯЕМ СТАРУЮ ТАБЛИЦУ
    cursor.execute("DROP TABLE IF EXISTS orders") 
    # СОЗДАЕМ НОВУЮ С ПРАВИЛЬНЫМИ КОЛОНКАМИ
    cursor.execute('''CREATE TABLE orders 
                      (id INTEGER PRIMARY KEY, 
                       name TEXT, 
                       phone TEXT, 
                       service TEXT, 
                       date TEXT, 
                       time TEXT)''')
    conn.commit()
    conn.close()
    print("--- БАЗА ДАННЫХ ОБНОВЛЕНА И ПЕРЕСОЗДАНА ---")
