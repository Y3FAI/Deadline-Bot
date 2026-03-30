import sqlite3
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

DB_NAME = "deadlines.db"
RIYADH_TZ = ZoneInfo("Asia/Riyadh")


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS deadlines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            class TEXT NOT NULL,
            start TIMESTAMP NOT NULL,
            due TIMESTAMP NOT NULL,
            link TEXT,
            recurring TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS holidays (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            start_date DATE NOT NULL,
            end_date DATE
        )
    """)
    conn.commit()
    conn.close()


def add_deadline(name, class_name, start, due, link=None, recurring=None):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO deadlines (name, class, start, due, link, recurring) VALUES (?, ?, ?, ?, ?, ?)",
        (name, class_name, start, due, link, recurring),
    )
    conn.commit()
    conn.close()


def get_all_deadlines():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name, class, start, due, link, recurring FROM deadlines ORDER BY due"
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_soon_deadlines(days=7):
    """Get non-recurring deadlines due within `days` + all recurring deadlines."""
    cutoff = datetime.now(RIYADH_TZ).replace(tzinfo=None) + timedelta(days=days)
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, name, class, start, due, link, recurring FROM deadlines
        WHERE recurring IS NOT NULL
           OR due <= ?
        ORDER BY due
        """,
        (cutoff,),
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def delete_deadline(id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM deadlines WHERE id = ?", (id,))
    conn.commit()
    conn.close()


def get_all_holidays():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, start_date, end_date FROM holidays ORDER BY start_date")
    rows = cursor.fetchall()
    conn.close()
    return rows
