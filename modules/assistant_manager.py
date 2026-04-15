#*****************************
# assistant_manager.py - Assistant management
# Version: 2.2.0
#*****************************
"""
CRUD operations for staff assistants in Stdytime.
"""

import sqlite3
from modules.database import DB_PATH


def get_all_assistants(owner_user_id: int = 1):
    """Fetch all assistants from database."""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute(
            "SELECT id, name, role, email, phone FROM staff WHERE owner_user_id = ? ORDER BY name",
            (owner_user_id,),
        )
        return c.fetchall()


def get_assistant(assistant_id, owner_user_id: int = 1):
    """Fetch a specific assistant by ID."""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        row = c.execute(
            "SELECT id, name, role, email, phone FROM staff WHERE id = ? AND owner_user_id = ?",
            (assistant_id, owner_user_id),
        ).fetchone()
        return row


def add_assistant(name, role="", email="", phone="", owner_user_id: int = 1):
    """Add a new assistant to the database and automatically generate QR code."""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO staff (name, role, email, phone, owner_user_id) VALUES (?,?,?,?,?)",
            (name, role, email, phone, owner_user_id),
        )
        assistant_id = c.lastrowid
        conn.commit()
    
    # Automatically generate QR code for the new assistant
    try:
        from modules import qr_generator
        qr_data = f"ASST:{assistant_id}\nName:{name}"
        qr_generator.generate_qr(qr_data, f"assistant_{assistant_id}")
    except Exception as e:
        print(f"Warning: Failed to generate QR code for assistant {assistant_id}: {e}")
    
    return assistant_id


def update_assistant(assistant_id, name, role="", email="", phone="", owner_user_id: int = 1):
    """Update an existing assistant."""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute(
            "UPDATE staff SET name = ?, role = ?, email = ?, phone = ? WHERE id = ? AND owner_user_id = ?",
            (name, role, email, phone, assistant_id, owner_user_id),
        )
        conn.commit()


def delete_assistant(assistant_id, owner_user_id: int = 1):
    """Delete an assistant from the database."""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM staff WHERE id = ? AND owner_user_id = ?", (assistant_id, owner_user_id))
        conn.commit()


def cleanup_old_payroll_data(months=18, owner_user_id=None):
    """
    Delete assistant_sessions (payroll data) older than specified months.
    Default: 18 months data retention policy.
    Returns: Number of records deleted.
    """
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        # Count records to be deleted
        if owner_user_id is None:
            c.execute(
                """
                SELECT COUNT(*) FROM assistant_sessions
                WHERE start_time < DATE('now', '-' || ? || ' months')
                """,
                (months,),
            )
        else:
            c.execute(
                """
                SELECT COUNT(*) FROM assistant_sessions
                WHERE start_time < DATE('now', '-' || ? || ' months')
                  AND owner_user_id = ?
                """,
                (months, owner_user_id),
            )
        count = c.fetchone()[0]
        
        # Delete old records
        if count > 0:
            if owner_user_id is None:
                c.execute(
                    """
                    DELETE FROM assistant_sessions
                    WHERE start_time < DATE('now', '-' || ? || ' months')
                    """,
                    (months,),
                )
            else:
                c.execute(
                    """
                    DELETE FROM assistant_sessions
                    WHERE start_time < DATE('now', '-' || ? || ' months')
                      AND owner_user_id = ?
                    """,
                    (months, owner_user_id),
                )
            conn.commit()
            print(f"[Payroll Cleanup] Deleted {count} assistant_sessions records older than {months} months")
        
        return count
