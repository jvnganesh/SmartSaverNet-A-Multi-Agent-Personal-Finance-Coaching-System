# data/seed_mock.py
from __future__ import annotations
from datetime import date, timedelta
import random


CATEGORIES = [
    ("Groceries", -200, -1200),
    ("Dining", -150, -900),
    ("Transport", -50, -400),
    ("Utilities", -600, -2000),
    ("Entertainment", -200, -1200),
    ("Shopping", -300, -2500),
]

SALARY_AMOUNTS = [45000, 60000, 75000]  # simulate variation


def seed_transactions(conn, user_id: str = "demo", days: int = 90) -> int:
    """
    Insert synthetic transactions covering the past `days` days.
    """
    cur = conn.cursor()
    today = date.today()
    inserted = 0

    for i in range(days):
        day = today - timedelta(days=i)

        # Salary hits on the 1st of each month
        if day.day == 1:
            cur.execute(
                "INSERT INTO transactions (user_id, date, description, amount, category) VALUES (?, ?, ?, ?, ?)",
                (user_id, day.isoformat(), "Salary Credit", random.choice(SALARY_AMOUNTS), "Income"),
            )
            inserted += 1
            continue

        # Rent on 3rd
        if day.day == 3:
            rent = -random.choice([8000, 12000, 15000])
            cur.execute(
                "INSERT INTO transactions (user_id, date, description, amount, category) VALUES (?, ?, ?, ?, ?)",
                (user_id, day.isoformat(), "Monthly Rent", rent, "Rent"),
            )
            inserted += 1
            continue

        # Random spend
        cat, lo, hi = random.choice(CATEGORIES)
        amount = round(random.uniform(lo, hi), 2)
        desc = f"{cat} Purchase"
        cur.execute(
            "INSERT INTO transactions (user_id, date, description, amount, category) VALUES (?, ?, ?, ?, ?)",
            (user_id, day.isoformat(), desc, amount, cat),
        )
        inserted += 1

    conn.commit()
    return inserted
