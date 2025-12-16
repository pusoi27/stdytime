# modules/timer_manager.py
import sqlite3
from modules.database import DB_PATH
from modules.utils import time_now, duration_seconds

active_sessions = {}


def clear_active_sessions():
    """Clear in-memory active session cache without touching the DB."""
    active_sessions.clear()


def stop_all_active():
    """Stop and persist all currently active sessions."""
    stopped = []
    for sid in list(active_sessions.keys()):
        stop_session(sid)
        stopped.append(sid)
    return stopped


def enforce_max_duration(max_seconds: int = 7200):
    """Stop any active session exceeding max_seconds. Returns list of ended ids."""
    ended = []
    now = time_now()
    for sid, start in list(active_sessions.items()):
        try:
            elapsed = duration_seconds(start, now)
        except Exception:
            # If parsing fails, skip enforcement for this record
            continue
        if elapsed >= max_seconds:
            stop_session(sid)
            ended.append(sid)
    return ended

def close_all_open_db_sessions():
    """Close ALL DB sessions with end_time IS NULL.
    This is stronger than stop_session(sid) because it closes multiple
    open rows per student if any exist. Returns count of rows updated.
    """
    end = time_now()
    updated = 0
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        rows = c.execute(
            "SELECT id, start_time FROM sessions WHERE end_time IS NULL"
        ).fetchall()
        for sid, start in rows:
            try:
                dur = duration_seconds(start, end)
            except Exception:
                # if parsing fails, set 0 duration
                dur = 0
            c.execute(
                "UPDATE sessions SET end_time=?, duration=? WHERE id=?",
                (end, dur, sid),
            )
            updated += 1
        conn.commit()
    # Clear in-memory cache as well
    clear_active_sessions()
    return updated

def delete_all_open_db_sessions():
    """Hard delete all sessions with end_time IS NULL.
    Use when a clean slate is required (e.g., app restart/reset).
    Returns number of rows deleted.
    """
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM sessions WHERE end_time IS NULL")
        deleted = c.rowcount
        conn.commit()
    clear_active_sessions()
    return deleted

def delete_all_sessions():
    """Delete ALL session records (open or closed) and clear caches.
    Use when a full reset of the active class/state is required.
    Returns number of rows deleted.
    """
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM sessions")
        deleted = c.rowcount
        conn.commit()
    clear_active_sessions()
    return deleted

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