#*****************************
#student_manager.py   ver 04--------------
#*****************************

import sqlite3, csv, os
from modules.database import DB_PATH


def _table_has_column(table, column):
    """Return True if `column` exists in `table` (sqlite PRAGMA)."""
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute(f"PRAGMA table_info({table})")
        cols = [r[1] for r in cur.fetchall()]
    return column in cols


def calculate_subject(math_goal, reading_goal):
    """Calculate subject based on goals: S1 if both goals, S2 if one goal, empty if neither.
    Goals can be text strings or None. Both must have non-empty text to be considered 'populated'.
    """
    # Check if math_goal has actual text content (handles None, empty string, whitespace)
    math_filled = bool(math_goal and str(math_goal).strip())
    # Check if reading_goal has actual text content (handles None, empty string, whitespace)
    reading_filled = bool(reading_goal and str(reading_goal).strip())
    
    # If both goals are populated, assign S1
    if math_filled and reading_filled:
        return "S1"
    # If only one goal is populated, assign S2
    elif math_filled or reading_filled:
        return "S2"
    # If neither goal is populated, return empty
    else:
        return ""


def safe_int(value, default=0):
    """Safely convert value to int, returning default if empty or invalid."""
    try:
        val = str(value).strip()
        if not val:
            return default
        return int(val)
    except (ValueError, TypeError):
        return default


def get_all_students():
    has_photo = _table_has_column("students", "photo")
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        if has_photo:
            # Include flags for loaned book and paper worksheet, plus active book loan count
            c.execute("""
                SELECT s.id, s.name, s.subject, s.email, s.phone, s.photo, s.active, s.book_loaned, s.paper_ws,
                       s.math_goal, s.math_worksheets_per_week, s.reading_goal, s.reading_worksheets_per_week,
                       (SELECT COUNT(*) FROM books WHERE borrower_id = s.id AND available = 0) as has_active_loan
                FROM students s
                ORDER BY s.name
            """)
            return c.fetchall()
        else:
            # Fallback if photo column is missing (migration not yet applied)
            c.execute("""
                SELECT s.id, s.name, s.subject, s.email, s.phone, s.active, s.book_loaned, s.paper_ws,
                       (SELECT COUNT(*) FROM books WHERE borrower_id = s.id AND available = 0) as has_active_loan
                FROM students s
                ORDER BY s.name
            """)
            rows = c.fetchall()
            # Return a consistent tuple shape where index 5 is `photo` (None if missing)
            return [(r[0], r[1], r[2], r[3], r[4], None, r[5], r[6], r[7], None, 0, None, 0, r[8]) for r in rows]


def get_student(student_id):
    has_photo = _table_has_column("students", "photo")
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        if has_photo:
            row = c.execute("SELECT id,name,subject,email,phone,photo,active,book_loaned,paper_ws,math_goal,math_worksheets_per_week,reading_goal,reading_worksheets_per_week FROM students WHERE id=?", (student_id,)).fetchone()
            return row
        else:
            row = c.execute("SELECT id,name,subject,email,phone,active,book_loaned,paper_ws FROM students WHERE id=?", (student_id,)).fetchone()
            if not row:
                return None
            # Insert None for photo and default new columns to keep tuple shape
            return (row[0], row[1], row[2], row[3], row[4], None, row[5], row[6], row[7], None, 0, None, 0)


def add_student(name, email, phone, photo=None, book_loaned=0, paper_ws=0, math_goal="", math_worksheets_per_week=0, reading_goal="", reading_worksheets_per_week=0):
    has_photo = _table_has_column("students", "photo")
    subject = calculate_subject(math_goal, reading_goal)
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        if has_photo:
            c.execute("""INSERT INTO students
                (name,subject,email,phone,photo,active,book_loaned,paper_ws,math_goal,math_worksheets_per_week,reading_goal,reading_worksheets_per_week)
                VALUES (?,?,?,?,?,1,?,?,?,?,?,?)""",
                (name, subject, email, phone, photo, int(bool(book_loaned)), int(bool(paper_ws)), math_goal, safe_int(math_worksheets_per_week), reading_goal, safe_int(reading_worksheets_per_week)))
        else:
            c.execute("""INSERT INTO students
                (name,subject,email,phone,active,book_loaned,paper_ws,math_goal,math_worksheets_per_week,reading_goal,reading_worksheets_per_week)
                VALUES (?,?,?,?,1,?,?,?,?,?,?)""",
                (name, subject, email, phone, int(bool(book_loaned)), int(bool(paper_ws)), math_goal, safe_int(math_worksheets_per_week), reading_goal, safe_int(reading_worksheets_per_week)))
        conn.commit()


def update_student(sid, name, email, phone, subject="", book_loaned=0, paper_ws=0, math_goal="", math_worksheets_per_week=0, reading_goal="", reading_worksheets_per_week=0):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""UPDATE students SET name=?,subject=?,email=?,phone=?,book_loaned=?,paper_ws=?,math_goal=?,math_worksheets_per_week=?,reading_goal=?,reading_worksheets_per_week=? WHERE id=?""",
                  (name,subject,email,phone,int(bool(book_loaned)),int(bool(paper_ws)),math_goal,safe_int(math_worksheets_per_week),reading_goal,safe_int(reading_worksheets_per_week),sid))
        conn.commit()


def recalculate_all_subjects():
    """Recalculate and update subject for all students based on their Math and Reading goals.
    Subject assignment:
    - S2 if both Math AND Reading goals are populated
    - S1 if only one goal is populated
    - Empty string if both goals are blank
    """
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        # Get all students with their goals
        c.execute("SELECT id, math_goal, reading_goal FROM students")
        students = c.fetchall()
        
        updated_count = 0
        for student_id, math_goal, reading_goal in students:
            new_subject = calculate_subject(math_goal, reading_goal)
            c.execute("UPDATE students SET subject=? WHERE id=?", (new_subject, student_id))
            updated_count += 1
        
        conn.commit()
    
    return updated_count


def delete_student(sid):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM students WHERE id=?", (sid,))
        conn.commit()


def import_csv(file_path):
    if not os.path.exists(file_path):
        return 0
    added=0
    with sqlite3.connect(DB_PATH) as conn, open(file_path,newline="",encoding="utf-8-sig") as f:
        reader=csv.DictReader(f)
        for row in reader:
            name=row.get("name") or ""
            if not name.strip(): continue
            email=row.get("email") or ""
            phone=row.get("phone") or ""
            whatsapp=row.get("WhatsApp") or ""
            subject=row.get("subject") or ""
            math_goal=row.get("math_goal") or ""
            math_ws=safe_int(row.get("Math/WS") or "0", default=0)
            reading_goal=row.get("reading_goal") or ""
            reading_ws=safe_int(row.get("Reading/WS") or "0", default=0)
            
            # If subject not provided, calculate from goals
            if not subject.strip():
                subject=calculate_subject(math_goal, reading_goal)
            
            exists=conn.execute("SELECT id FROM students WHERE LOWER(name)=LOWER(?)",(name,)).fetchone()
            if exists: continue
            
            # Check if new columns exist before using them
            has_whatsapp = _table_has_column("students", "whatsapp")
            has_math_ws = _table_has_column("students", "math_ws_per_week")
            has_reading_ws = _table_has_column("students", "reading_ws_per_week")
            
            if has_whatsapp and has_math_ws and has_reading_ws:
                conn.execute("""INSERT INTO students(name,subject,email,phone,whatsapp,active,math_goal,math_ws_per_week,reading_goal,reading_ws_per_week)
                                VALUES(?,?,?,?,?,1,?,?,?,?)""",(name,subject,email,phone,whatsapp,math_goal,math_ws,reading_goal,reading_ws))
            elif has_whatsapp and has_math_ws:
                conn.execute("""INSERT INTO students(name,subject,email,phone,whatsapp,active,math_goal,math_ws_per_week,reading_goal)
                                VALUES(?,?,?,?,?,1,?,?,?)""",(name,subject,email,phone,whatsapp,math_goal,math_ws,reading_goal))
            elif has_whatsapp and has_reading_ws:
                conn.execute("""INSERT INTO students(name,subject,email,phone,whatsapp,active,math_goal,reading_goal,reading_ws_per_week)
                                VALUES(?,?,?,?,?,1,?,?,?)""",(name,subject,email,phone,whatsapp,math_goal,reading_goal,reading_ws))
            elif has_whatsapp:
                conn.execute("""INSERT INTO students(name,subject,email,phone,whatsapp,active,math_goal,reading_goal)
                                VALUES(?,?,?,?,?,1,?,?)""",(name,subject,email,phone,whatsapp,math_goal,reading_goal))
            else:
                conn.execute("""INSERT INTO students(name,subject,email,phone,active,math_goal,reading_goal)
                                VALUES(?,?,?,?,1,?,?)""",(name,subject,email,phone,math_goal,reading_goal))
            added+=1
        conn.commit()
    return added

def export_csv(path):
    data=get_all_students()
    headers=["ID","Name","Subject","Email","Phone","Photo","Active","BookLoaned","PaperWS","MathGoal","MathWSPerWeek","ReadingGoal","ReadingWSPerWeek"]
    with open(path,"w",newline="",encoding="utf-8") as f:
        writer=csv.writer(f)
        writer.writerow(headers)
        writer.writerows(data)