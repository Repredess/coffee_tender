import telebot
from telebot import types
import sqlite3
from datetime import datetime
import revenue
import CONFIG

coffee_bot = telebot.TeleBot(CONFIG.API_KEY)
money = 0
evening_cash = 0
non_cash = 0


@coffee_bot.message_handler(commands=["start"])
def welcome(message, closed=False):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton('Открыть смену')
    markup.row(btn1)
    if closed:
        coffee_bot.send_message(message.chat.id, f"Отличная смена, {message.from_user.first_name}!",
                                reply_markup=markup)
    else:
        coffee_bot.send_message(message.chat.id, f"Привет, {message.from_user.first_name}. Поработаем?",
                                reply_markup=markup)


@coffee_bot.message_handler(func=lambda message: message.text == "Открыть смену")
def new_shift(message, error=False):
    if not error:
        coffee_bot.send_message(message.chat.id, "Введите наличные на утро:")
        coffee_bot.register_next_step_handler(message, validate)
    else:
        coffee_bot.send_message(message.chat.id, "Введите наличные на утро (числовое значение):")
        coffee_bot.register_next_step_handler(message, validate)


def validate(message):
    if message.text.isdigit():
        global evening_cash
        get_rvn = revenue.Revenue()
        now = datetime.now()
        date = f'{now:%d-%m-%Y}'
        evening_cash = int(message.text)
        get_rvn.set_morning_cash(morning_cash=int(message.text), user_id=message.chat.id, date=date)
        on_shift(message)
    else:
        new_shift(message, error=True)


def on_shift(message, choice=False):
    global money, evening_cash, non_cash
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton('Закрыть смену')
    btn2 = types.KeyboardButton('Сводный чек')
    markup.row(btn1, btn2)
    if choice:
        money = int(f"{money.split(' ')[0].strip('+')}")
        coffee_bot.send_message(message.chat.id, f"+{money}р добавленно в кассу!\n\n"
                                                 f"Наличных в кассе: {evening_cash}р\n"
                                                 f"Безнал: {non_cash}р",
                                reply_markup=markup)
    else:
        coffee_bot.send_message(message.chat.id, f"Смена открыта!\n\n"
                                                 f"Наличных в кассе: {evening_cash}р\n",
                                reply_markup=markup)


@coffee_bot.message_handler(func=lambda message: message.text == "Сводный чек")
def get_check(message):
    db = sqlite3.connect('shifts.db')
    cursor = db.cursor()

    cursor.execute("""CREATE TABLE IF NOT EXISTS today_shift(
        user_id INTEGER,
        action TEXT,
        time TEXT);
        """)
    db.commit()

    cursor.execute("""SELECT rowid, * FROM today_shift;""")

    data = cursor.fetchall()
    if not data:
        coffee_bot.send_message(message.chat.id, "Еще не было заказов")
    else:
        clean_data = ""
        for piece in data:
            clean_data += f"{piece[0]}. {piece[2]} {piece[3].split(' ')[0]}\n"
        coffee_bot.send_message(message.chat.id, f"{clean_data}")


@coffee_bot.message_handler(func=lambda message: message.text.startswith('-') or message.text.startswith('+'))
def cash_register(message):
    if message.text.startswith('-'):
        global evening_cash
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        btn1 = types.KeyboardButton('Закрыть смену')
        btn2 = types.KeyboardButton('Сводный чек')
        markup.row(btn1, btn2)
        register_user_data(message, action=message.text)
        mm = int(f"{message.text.split(' ')[0].strip('-')}")
        evening_cash -= mm
        coffee_bot.send_message(message.chat.id, f"{message.text} добавлено в расход!\n\n"
                                                 f"В кассе: {evening_cash}р", reply_markup=markup)
    else:
        global money
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        btn1 = types.KeyboardButton("Наличные")
        btn2 = types.KeyboardButton("Безналичные")
        markup.row(btn1, btn2)
        coffee_bot.send_message(message.chat.id, "Тип оплаты:", reply_markup=markup)
        money = message.text
        coffee_bot.register_next_step_handler(message, add_data)


def add_data(message):
    global non_cash, evening_cash
    if message.text == "Наличные":
        mm = int(f"{money.split(' ')[0].strip('+')}")
        evening_cash += mm
    elif message.text == "Безналичные":
        mm = int(f"{money.split(' ')[0].strip('+')}")
        non_cash += mm
    registrated = f"{money} {message.text}"
    register_user_data(message, action=registrated)
    on_shift(message, choice=True)


def register_user_data(message, action):
    """Функция предназначена для добавления и обновления пользователей в базе данных."""
    db = sqlite3.connect('shifts.db')
    cursor = db.cursor()

    cursor.execute("""CREATE TABLE IF NOT EXISTS today_shift(
        user_id INTEGER,
        action TEXT,
        time TEXT);
        """)
    db.commit()

    user_id = message.chat.id
    action = action
    now = datetime.now()
    time = f'{now:%H:%M:%S %d-%m-%Y}'

    cursor.execute("""INSERT INTO today_shift VALUES(?,?,?);""", (user_id,
                                                                  action,
                                                                  time))

    db.commit()


@coffee_bot.message_handler(func=lambda message: message.text == "Закрыть смену")
def close_shift(message):
    now = datetime.now()
    date = f'{now:%d-%m-%Y}'

    get_rvn = revenue.Revenue()
    db = sqlite3.connect('shifts.db')
    cursor = db.cursor()

    cursor.execute("""SELECT action FROM today_shift;""")
    raw_data = cursor.fetchall()

    get_rvn.set_raw_check(raw=raw_data, date=date)
    msg = get_rvn.get_revenue(date=date)
    coffee_bot.send_message(message.chat.id, msg)
    clear_today_shifts_table()
    welcome(message, closed=True)


def clear_today_shifts_table():
    db = sqlite3.connect('shifts.db')
    cursor = db.cursor()
    cursor.execute("DELETE FROM today_shift;")
    db.commit()
    db.close()


coffee_bot.infinity_polling()
