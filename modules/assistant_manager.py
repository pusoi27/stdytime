#*****************************
# assistant_manager.py - Assistant management
# Version: 2.2.0
#*****************************
"""
CRUD operations for staff assistants in KumoClock.
"""

import sqlite3
from modules.database import DB_PATH


def get_all_assistants():
    """Fetch all assistants from database."""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT id, name, role, email, phone FROM staff ORDER BY name")
        return c.fetchall()


def get_assistant(assistant_id):
    """Fetch a specific assistant by ID."""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        row = c.execute("SELECT id, name, role, email, phone FROM staff WHERE id=?", (assistant_id,)).fetchone()
        return row


def add_assistant(name, role="", email="", phone=""):
    """Add a new assistant to the database."""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT INTO staff (name, role, email, phone) VALUES (?,?,?,?)",
                  (name, role, email, phone))
        conn.commit()
        return c.lastrowid


def update_assistant(assistant_id, name, role="", email="", phone=""):
    """Update an existing assistant."""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("UPDATE staff SET name=?, role=?, email=?, phone=? WHERE id=?",
                  (name, role, email, phone, assistant_id))
        conn.commit()


def delete_assistant(assistant_id):
    """Delete an assistant from the database."""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM staff WHERE id=?", (assistant_id,))
        conn.commit()
