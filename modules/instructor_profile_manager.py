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
            SELECT id, name, email, phone, center_location, center_address, center_hours, 
                   monday_start, monday_end, tuesday_start, tuesday_end, 
                   wednesday_start, wednesday_end, thursday_start, thursday_end,
                   friday_start, friday_end, saturday_start, saturday_end,
                   sunday_start, sunday_end, created_at, updated_at
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
                'center_address': row[5],
                'center_hours': row[6],
                'monday_start': row[7],
                'monday_end': row[8],
                'tuesday_start': row[9],
                'tuesday_end': row[10],
                'wednesday_start': row[11],
                'wednesday_end': row[12],
                'thursday_start': row[13],
                'thursday_end': row[14],
                'friday_start': row[15],
                'friday_end': row[16],
                'saturday_start': row[17],
                'saturday_end': row[18],
                'sunday_start': row[19],
                'sunday_end': row[20],
                'created_at': row[21],
                'updated_at': row[22]
            }
    return None


def create_instructor_profile(name, email, phone, center_location, center_address, center_hours, weekly_hours):
    """Create a new instructor profile"""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        now = datetime.now().isoformat()
        days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        
        values = [name, email, phone, center_location, center_address, center_hours, now, now]
        for day in days:
            values.append(weekly_hours.get(f'{day}_start', ''))
            values.append(weekly_hours.get(f'{day}_end', ''))
        
        placeholders = ','.join(['?' for _ in range(len(values))])
        columns = 'name, email, phone, center_location, center_address, center_hours, created_at, updated_at'
        for day in days:
            columns += f', {day}_start, {day}_end'
        
        c.execute(f"""
            INSERT INTO instructor_profile ({columns})
            VALUES ({placeholders})
        """, values)
        conn.commit()
        return c.lastrowid


def update_instructor_profile(profile_id, name, email, phone, center_location, center_address, center_hours, weekly_hours):
    """Update an existing instructor profile"""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        now = datetime.now().isoformat()
        days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        
        set_clause = 'name = ?, email = ?, phone = ?, center_location = ?, center_address = ?, center_hours = ?, updated_at = ?'
        values = [name, email, phone, center_location, center_address, center_hours, now]
        
        for day in days:
            set_clause += f', {day}_start = ?, {day}_end = ?'
            values.append(weekly_hours.get(f'{day}_start', ''))
            values.append(weekly_hours.get(f'{day}_end', ''))
        
        values.append(profile_id)
        
        c.execute(f"""
            UPDATE instructor_profile
            SET {set_clause}
            WHERE id = ?
        """, values)
        conn.commit()


def delete_instructor_profile(profile_id):
    """Delete an instructor profile"""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM instructor_profile WHERE id = ?", (profile_id,))
        conn.commit()
