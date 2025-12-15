# modules/timer_manager.py
import sqlite3
from modules.database import DB_PATH
from modules.utils import time_now, duration_seconds

active_sessions = {}

def start_session(student_id):
    """Record start time in DB and cache it."""
    start = time_now()
    active_sessions[student_id] = start
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        # Insert a new session stub (end_time NULL)
        c.execute(
            """INSERT INTO sessions (student_id,start_time) VALUES (?,?)""",
            (student_id, start)
        )
        conn.commit()

def stop_session(student_id):
    """Complete the active session and write duration."""
    if student_id not in active_sessions:
        # try to find last NULL end_time
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute("""SELECT id,start_time FROM sessions
                         WHERE student_id=? AND end_time IS NULL
                         ORDER BY id DESC LIMIT 1""", (student_id,))
            row = c.fetchone()
            if not row:
                return None
            sid, start = row
            end = time_now()
            duration = duration_seconds(start, end)
            c.execute("""UPDATE sessions
                         SET end_time=?, duration=?
                         WHERE id=?""", (end, duration, sid))
            conn.commit()
        return dict(start=start, end=end, duration=duration)

    # If start time cached
    start = active_sessions.pop(student_id)
    end = time_now()
    duration = duration_seconds(start, end)
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        # update the latest open session or append if none open
        c.execute("""SELECT id FROM sessions
                     WHERE student_id=? AND end_time IS NULL
                     ORDER BY id DESC LIMIT 1""", (student_id,))
        row = c.fetchone()
        if row:
            sid = row[0]
            c.execute(
                "UPDATE sessions SET end_time=?, duration=? WHERE id=?",
                (end, duration, sid),
            )
        else:
            c.execute(
                """INSERT INTO sessions
                   (student_id, start_time, end_time, duration)
                   VALUES (?,?,?,?)""",
                (student_id, start, end, duration),
            )
        conn.commit()
    return dict(start=start, end=end, duration=duration)