#*****************************
# schedule_manager.py - Assistant scheduling by day
# Version: 1.0.0
#*****************************
"""
CRUD operations for assistant scheduling (assigns assistants to specific calendar dates).
"""

import sqlite3
from datetime import datetime, timedelta
from modules.database import DB_PATH


def schedule_assistant(assistant_id, scheduled_date, owner_user_id: int = 1):
    """
    Schedule an assistant for a specific date (YYYY-MM-DD format).
    Returns True if inserted, False if already scheduled.
    """
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        try:
            c.execute(
                """INSERT INTO assistant_schedule (assistant_id, scheduled_date, owner_user_id)
                   VALUES (?, ?, ?)""",
                (assistant_id, scheduled_date, owner_user_id),
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            # Already scheduled or other constraint violation
            return False


def unschedule_assistant(assistant_id, scheduled_date, owner_user_id: int = 1):
    """
    Remove an assistant from a scheduled date.
    Returns number of rows deleted.
    """
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute(
            """DELETE FROM assistant_schedule 
               WHERE assistant_id = ? AND scheduled_date = ? AND owner_user_id = ?""",
            (assistant_id, scheduled_date, owner_user_id),
        )
        conn.commit()
        return c.rowcount


def get_scheduled_assistants_for_date(scheduled_date, owner_user_id: int = 1):
    """
    Fetch all assistants scheduled for a specific date.
    Returns list of (assistant_id, name, role, email, phone).
    """
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute(
            """SELECT s.id, s.name, s.role, s.email, s.phone
               FROM staff s
               INNER JOIN assistant_schedule a
                 ON s.id = a.assistant_id
               WHERE a.scheduled_date = ? AND a.owner_user_id = ?
               ORDER BY s.name""",
            (scheduled_date, owner_user_id),
        )
        return c.fetchall()


def get_unscheduled_assistants(owner_user_id: int = 1):
    """
    Fetch all assistants not currently in the schedule.
    Returns list of (assistant_id, name, role, email, phone).
    """
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute(
            """SELECT id, name, role, email, phone
               FROM staff
               WHERE owner_user_id = ?
               ORDER BY name""",
            (owner_user_id,),
        )
        return c.fetchall()


def get_assistants_schedule_for_month(year, month, owner_user_id: int = 1):
    """
    Fetch all scheduled assistants for a given month.
    Returns dict: {YYYY-MM-DD: [(assistant_id, name, role, email, phone), ...]}.
    """
    # Get first and last day of month
    first_day = datetime(year, month, 1).date()
    if month == 12:
        last_day = datetime(year + 1, 1, 1).date() - timedelta(days=1)
    else:
        last_day = datetime(year, month + 1, 1).date() - timedelta(days=1)
    
    start_str = first_day.isoformat()
    end_str = last_day.isoformat()
    
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute(
            """SELECT a.scheduled_date, s.id, s.name, s.role, s.email, s.phone
               FROM assistant_schedule a
               INNER JOIN staff s ON s.id = a.assistant_id
               WHERE a.scheduled_date BETWEEN ? AND ? AND a.owner_user_id = ?
               ORDER BY a.scheduled_date, s.name""",
            (start_str, end_str, owner_user_id),
        )
        
        result = {}
        for row in c.fetchall():
            date_str = row[0]
            assistant = row[1:]
            if date_str not in result:
                result[date_str] = []
            result[date_str].append(assistant)
        
        return result
