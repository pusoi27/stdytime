#*****************************
#instructor_profile_manager.py
#*****************************

import sqlite3
from datetime import datetime
from modules.database import DB_PATH


def get_instructor_profile():
    """Get the instructor profile (assumes single profile)"""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""
            SELECT id, name, email, phone, center_location, created_at, updated_at
            FROM instructor_profile
            LIMIT 1
        """)
        row = c.fetchone()
        if row:
            return {
                'id': row[0],
                'name': row[1],
                'email': row[2],
                'phone': row[3],
                'center_location': row[4],
                'created_at': row[5],
                'updated_at': row[6]
            }
    return None


def create_instructor_profile(name, email, phone, center_location):
    """Create a new instructor profile"""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        now = datetime.now().isoformat()
        c.execute("""
            INSERT INTO instructor_profile (name, email, phone, center_location, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (name, email, phone, center_location, now, now))
        conn.commit()
        return c.lastrowid


def update_instructor_profile(profile_id, name, email, phone, center_location):
    """Update an existing instructor profile"""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        now = datetime.now().isoformat()
        c.execute("""
            UPDATE instructor_profile
            SET name = ?, email = ?, phone = ?, center_location = ?, updated_at = ?
            WHERE id = ?
        """, (name, email, phone, center_location, now, profile_id))
        conn.commit()


def delete_instructor_profile(profile_id):
    """Delete an instructor profile"""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM instructor_profile WHERE id = ?", (profile_id,))
        conn.commit()
