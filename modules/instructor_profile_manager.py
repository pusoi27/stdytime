#*****************************
#instructor_profile_manager.py
#*****************************

import sqlite3
from datetime import datetime
from modules.database import DB_PATH


def _ensure_owner_column():
    """Ensure instructor_profile supports required profile columns."""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("PRAGMA table_info(instructor_profile)")
        cols = [r[1] for r in c.fetchall()]
        if "owner_user_id" not in cols:
            c.execute("ALTER TABLE instructor_profile ADD COLUMN owner_user_id INTEGER DEFAULT 1")
            c.execute("UPDATE instructor_profile SET owner_user_id = 1 WHERE owner_user_id IS NULL")
            c.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_instructor_profile_owner ON instructor_profile(owner_user_id)"
            )
        if "center_time_zone" not in cols:
            c.execute("ALTER TABLE instructor_profile ADD COLUMN center_time_zone TEXT")
            conn.commit()


def get_instructor_profile(owner_user_id=1):
    """Get the instructor profile for a specific user."""
    _ensure_owner_column()
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""
            SELECT id, name, email, phone, center_location, center_address, center_time_zone, center_hours,
                   monday_start, monday_end, tuesday_start, tuesday_end, 
                   wednesday_start, wednesday_end, thursday_start, thursday_end,
                   friday_start, friday_end, saturday_start, saturday_end,
                   sunday_start, sunday_end, created_at, updated_at
            FROM instructor_profile
            WHERE owner_user_id = ?
            LIMIT 1
        """, (owner_user_id,))
        row = c.fetchone()
        if row:
            return {
                'id': row[0],
                'name': row[1],
                'email': row[2],
                'phone': row[3],
                'center_location': row[4],
                'center_address': row[5],
                'center_time_zone': row[6],
                'center_hours': row[7],
                'monday_start': row[8],
                'monday_end': row[9],
                'tuesday_start': row[10],
                'tuesday_end': row[11],
                'wednesday_start': row[12],
                'wednesday_end': row[13],
                'thursday_start': row[14],
                'thursday_end': row[15],
                'friday_start': row[16],
                'friday_end': row[17],
                'saturday_start': row[18],
                'saturday_end': row[19],
                'sunday_start': row[20],
                'sunday_end': row[21],
                'created_at': row[22],
                'updated_at': row[23]
            }
    return None


def create_instructor_profile(name, email, phone, center_location, center_address, center_time_zone, center_hours, weekly_hours, owner_user_id=1):
    """Create a new instructor profile for the given user."""
    _ensure_owner_column()
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        now = datetime.now().isoformat()
        days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        
        values = [name, email, phone, center_location, center_address, center_time_zone, center_hours, now, now, owner_user_id]
        for day in days:
            values.append(weekly_hours.get(f'{day}_start', ''))
            values.append(weekly_hours.get(f'{day}_end', ''))
        
        placeholders = ','.join(['?' for _ in range(len(values))])
        columns = 'name, email, phone, center_location, center_address, center_time_zone, center_hours, created_at, updated_at, owner_user_id'
        for day in days:
            columns += f', {day}_start, {day}_end'
        
        c.execute(f"""
            INSERT INTO instructor_profile ({columns})
            VALUES ({placeholders})
        """, values)
        conn.commit()
        return c.lastrowid


def update_instructor_profile(profile_id, name, email, phone, center_location, center_address, center_time_zone, center_hours, weekly_hours, owner_user_id=1):
    """Update an existing instructor profile owned by the current user."""
    _ensure_owner_column()
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        now = datetime.now().isoformat()
        days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        
        set_clause = 'name = ?, email = ?, phone = ?, center_location = ?, center_address = ?, center_time_zone = ?, center_hours = ?, updated_at = ?'
        values = [name, email, phone, center_location, center_address, center_time_zone, center_hours, now]
        
        for day in days:
            set_clause += f', {day}_start = ?, {day}_end = ?'
            values.append(weekly_hours.get(f'{day}_start', ''))
            values.append(weekly_hours.get(f'{day}_end', ''))
        
        values.append(profile_id)
        values.append(owner_user_id)
        
        c.execute(f"""
            UPDATE instructor_profile
            SET {set_clause}
            WHERE id = ? AND owner_user_id = ?
        """, values)
        conn.commit()


def delete_instructor_profile(profile_id, owner_user_id=1):
    """Delete an instructor profile owned by the current user."""
    _ensure_owner_column()
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM instructor_profile WHERE id = ? AND owner_user_id = ?", (profile_id, owner_user_id))
        conn.commit()
