import sqlite3


class Revenue:

    def __init__(self):
        db = sqlite3.connect('shifts.db')
        cursor = db.cursor()

        cursor.execute("""CREATE TABLE IF NOT EXISTS shifts(
                date TEXT,
                user_id INTEGER,
                morning_cash INTEGER,
                cash_orders INTEGER,
                card_orders INTEGER,
                expenses INTEGER,
                raw_check TEXT,
                evening_cash INTEGER,
                revenue INTEGER
                );
                """)
        db.commit()

    def set_morning_cash(self, morning_cash, user_id, date):
        db = sqlite3.connect('shifts.db')
        cursor = db.cursor()

        date = date
        user_id = user_id
        morning_cash = morning_cash
        cash_orders = 0
        card_orders = 0
        expenses = 0
        raw_check = "-"
        evening_cash = morning_cash
        revenue = 0

        cursor.execute("""INSERT INTO shifts VALUES(?,?,?,?,?,?,?,?,?);""", (date,
                                                                             user_id,
                                                                             morning_cash,
                                                                             cash_orders,
                                                                             card_orders,
                                                                             expenses,
                                                                             raw_check,
                                                                             evening_cash,
                                                                             revenue))
        db.commit()

    def set_raw_check(self, raw, date):
        db = sqlite3.connect('shifts.db')
        cursor = db.cursor()

        cash_orders = 0
        card_orders = 0
        expenses = 0
        date = date

        for piece in raw:
            if piece[0].startswith("-"):
                body = piece[0].split(' ')
                expenses += int(body[0].strip('-'))
            elif piece[0].startswith("+"):
                body = piece[0].split(' ')
                if body[-1] == "Наличные":
                    cash_orders += int(body[0].strip('+'))
                elif body[-1] == "Безналичные":
                    card_orders += int(body[0].strip('+'))

        raw_check = ""
        counter = 0
        for piece in raw:
            counter += 1
            raw_check += f"{counter}. {' '.join(piece)}\n"

        cursor.execute(
            """UPDATE shifts SET cash_orders = ?, card_orders = ?, expenses = ?, raw_check = ? WHERE date = ?;""",
            (cash_orders,
             card_orders,
             expenses,
             raw_check,
             date))

        db.commit()

    def set_evening_cash(self, date):
        db = sqlite3.connect('shifts.db')
        cursor = db.cursor()
        date = str(date)
        cursor.execute("""SELECT morning_cash, cash_orders, expenses FROM shifts WHERE date = ?;""",
                       (date,))  # добавлена запятая после date

        data = cursor.fetchone()
        evening_cash = data[0] + data[1] - data[2]

        cursor.execute(
            """UPDATE shifts SET evening_cash = ? WHERE date = ?;""", (evening_cash,
                                                                       date))

        db.commit()

    def get_revenue(self, date):
        db = sqlite3.connect('shifts.db')
        cursor = db.cursor()
        date = date
        cursor.execute(
            """SELECT morning_cash, cash_orders, card_orders, expenses, evening_cash FROM shifts WHERE date = ?;""",
            (date,))  # добавлена запятая после date

        data = cursor.fetchone()

        revenue = data[4] + data[3] + data[2] - data[0]
        message = f"Смена {date}:\n\n" \
                  f"Наличные на утро: {data[0]}р\n" \
                  f"Получено наличными: {data[1]}р\n" \
                  f"Безнал: {data[2]}р\n" \
                  f"Расходы: {data[3]}р\n" \
                  f"Наличные на вечер: {data[4]}р\n" \
                  f"Выручка: {revenue}р\n"

        cursor.execute(
            """UPDATE shifts SET revenue = ? WHERE date = ?;""", (revenue,
                                                                  date))

        db.commit()

        return message