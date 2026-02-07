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
                SELECT s.id, s.name, s.subject, s.level, s.email, s.phone, s.whatsapp, s.photo, s.active, s.book_loaned, s.paper_ws,
                       s.math_goal, s.math_ws_per_week, s.reading_goal, s.reading_ws_per_week,
                       s.el, s.pi, s.v, s.day1, s.day1_time, s.day2, s.day2_time,
                       (SELECT COUNT(*) FROM books WHERE borrower_id = s.id AND available = 0) as has_active_loan
                FROM students s
                ORDER BY s.name
            """)
            return c.fetchall()
        else:
            # Fallback if photo column is missing (migration not yet applied)
            c.execute("""
                SELECT s.id, s.name, s.subject, s.level, s.email, s.phone, s.active, s.book_loaned, s.paper_ws,
                       (SELECT COUNT(*) FROM books WHERE borrower_id = s.id AND available = 0) as has_active_loan
                FROM students s
                ORDER BY s.name
            """)
            rows = c.fetchall()
            # Return a consistent tuple shape where index 6 is `photo` (None if missing)
            return [(r[0], r[1], r[2], r[3], r[4], r[5], None, r[6], r[7], r[8], None, 0, None, 0, r[9]) for r in rows]


def get_student(student_id):
    has_photo = _table_has_column("students", "photo")
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        if has_photo:
            row = c.execute("SELECT id,name,subject,email,phone,whatsapp,photo,active,book_loaned,paper_ws,math_goal,math_ws_per_week,reading_goal,reading_ws_per_week,el,pi,v,day1,day2,day1_time,day2_time FROM students WHERE id=?", (student_id,)).fetchone()
            return row
        else:
            row = c.execute("SELECT id,name,subject,email,phone,whatsapp,active,book_loaned,paper_ws FROM students WHERE id=?", (student_id,)).fetchone()
            if not row:
                return None
            # Insert None for photo and default new columns to keep tuple shape
            return (row[0], row[1], row[2], row[3], row[4], row[5], None, row[6], row[7], row[8], None, 0, None, 0)


def add_student(name, subject, email, phone, whatsapp="", photo=None, book_loaned=0, paper_ws=0, math_goal="", math_worksheets_per_week=0, reading_goal="", reading_worksheets_per_week=0, el=0, pi=0, v=0, day1="", day2="", day1_time="", day2_time=""):
    has_photo = _table_has_column("students", "photo")
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        if has_photo:
            c.execute("""INSERT INTO students
                (name,subject,email,phone,whatsapp,photo,active,book_loaned,paper_ws,math_goal,math_ws_per_week,reading_goal,reading_ws_per_week,el,pi,v,day1,day2,day1_time,day2_time)
                VALUES (?,?,?,?,?,?,1,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (name, subject, email, phone, whatsapp, photo, int(bool(book_loaned)), int(bool(paper_ws)), math_goal, safe_int(math_worksheets_per_week), reading_goal, safe_int(reading_worksheets_per_week), int(bool(el)), int(bool(pi)), int(bool(v)), day1, day2, day1_time, day2_time))
        else:
            c.execute("""INSERT INTO students
                (name,subject,email,phone,whatsapp,active,book_loaned,paper_ws,math_goal,math_ws_per_week,reading_goal,reading_ws_per_week)
                VALUES (?,?,?,?,?,1,?,?,?,?,?,?)""",
                (name, subject, email, phone, whatsapp, int(bool(book_loaned)), int(bool(paper_ws)), math_goal, safe_int(math_worksheets_per_week), reading_goal, safe_int(reading_worksheets_per_week)))
        conn.commit()


def update_student(sid, name, email, phone, whatsapp="", subject="", book_loaned=0, paper_ws=0, math_goal="", math_worksheets_per_week=0, reading_goal="", reading_worksheets_per_week=0, photo=None, el=0, pi=0, v=0, day1="", day2="", day1_time="", day2_time=""):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        if photo:
            # If photo is provided, include it in the update
            c.execute("""UPDATE students SET name=?,subject=?,email=?,phone=?,whatsapp=?,book_loaned=?,paper_ws=?,math_goal=?,math_ws_per_week=?,reading_goal=?,reading_ws_per_week=?,photo=?,el=?,pi=?,v=?,day1=?,day2=?,day1_time=?,day2_time=? WHERE id=?""",
                      (name,subject,email,phone,whatsapp,int(bool(book_loaned)),int(bool(paper_ws)),math_goal,safe_int(math_worksheets_per_week),reading_goal,safe_int(reading_worksheets_per_week),photo,int(bool(el)),int(bool(pi)),int(bool(v)),day1,day2,day1_time,day2_time,sid))
        else:
            # If no photo, update all other fields
            c.execute("""UPDATE students SET name=?,subject=?,email=?,phone=?,whatsapp=?,book_loaned=?,paper_ws=?,math_goal=?,math_ws_per_week=?,reading_goal=?,reading_ws_per_week=?,el=?,pi=?,v=?,day1=?,day2=?,day1_time=?,day2_time=? WHERE id=?""",
                      (name,subject,email,phone,whatsapp,int(bool(book_loaned)),int(bool(paper_ws)),math_goal,safe_int(math_worksheets_per_week),reading_goal,safe_int(reading_worksheets_per_week),int(bool(el)),int(bool(pi)),int(bool(v)),day1,day2,day1_time,day2_time,sid))
        conn.commit()


def delete_student(sid):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM students WHERE id=?", (sid,))
        conn.commit()


def import_csv(file_path):
    if not os.path.exists(file_path):
        return {"added": 0, "updated": 0, "deleted": 0}
    added=0
    updated=0
    deleted=0
    csv_names=set()  # Track names from CSV
    
    with sqlite3.connect(DB_PATH) as conn, open(file_path,newline="",encoding="utf-8-sig") as f:
        reader=csv.DictReader(f)
        
        # Debug: Log column headers
        first_row = True
        for row in reader:
            if first_row:
                print(f"CSV Columns: {list(row.keys())}")
                first_row = False
            
            name=row.get("name") or ""
            if not name.strip(): continue
            csv_names.add(name.lower().strip())  # Store lowercase name for matching
            
            email=row.get("email") or ""
            phone=row.get("phone") or ""
            whatsapp=row.get("WhatsApp") or row.get("whatsapp") or ""
            subject=row.get("subject") or ""
            math_goal=row.get("math_goal") or ""
            # Map CSV column Math/WS to database column math_ws_per_week
            math_ws=safe_int(row.get("Math/WS") or row.get("math/ws") or "0", default=0)
            reading_goal=row.get("reading_goal") or ""
            # Map CSV column Reading/WS to database column reading_ws_per_week
            reading_ws=safe_int(row.get("Reading/WS") or row.get("reading/ws") or "0", default=0)
            print(f"Student: {name}, Math/WS: {math_ws}, Reading/WS: {reading_ws}")
            
            if subject.strip() not in {"S1", "S2"}:
                return {"error": "CSV import failed: subject must be S1 or S2 for every student."}
            
            # Check if student exists
            student_record=conn.execute("SELECT id FROM students WHERE LOWER(TRIM(name))=LOWER(?)",(name.strip(),)).fetchone()
            
            # Check if new columns exist before using them
            has_whatsapp = _table_has_column("students", "whatsapp")
            has_math_ws = _table_has_column("students", "math_ws_per_week")
            has_reading_ws = _table_has_column("students", "reading_ws_per_week")
            
            print(f"Columns exist - WhatsApp: {has_whatsapp}, Math WS: {has_math_ws}, Reading WS: {has_reading_ws}")
            
            if student_record:
                # UPDATE existing student - set all fields from CSV
                student_id = student_record[0]
                print(f"UPDATING student ID {student_id}: {name}")
                if has_whatsapp and has_math_ws and has_reading_ws:
                    print(f"  Setting math_ws_per_week={math_ws}, reading_ws_per_week={reading_ws}")
                    conn.execute("""UPDATE students SET name=?, subject=?, email=?, phone=?, whatsapp=?, math_goal=?, math_ws_per_week=?, reading_goal=?, reading_ws_per_week=?, active=1 WHERE id=?"""
                                 ,(name,subject,email,phone,whatsapp,math_goal,math_ws,reading_goal,reading_ws,student_id))
                elif has_whatsapp and has_math_ws:
                    print(f"  Setting math_ws_per_week={math_ws} (no reading_ws_per_week column)")
                    conn.execute("""UPDATE students SET name=?, subject=?, email=?, phone=?, whatsapp=?, math_goal=?, math_ws_per_week=?, reading_goal=?, active=1 WHERE id=?"""
                                 ,(name,subject,email,phone,whatsapp,math_goal,math_ws,reading_goal,student_id))
                elif has_whatsapp and has_reading_ws:
                    print(f"  Setting reading_ws_per_week={reading_ws} (no math_ws_per_week column)")
                    conn.execute("""UPDATE students SET name=?, subject=?, email=?, phone=?, whatsapp=?, math_goal=?, reading_goal=?, reading_ws_per_week=?, active=1 WHERE id=?"""
                                 ,(name,subject,email,phone,whatsapp,math_goal,reading_goal,reading_ws,student_id))
                elif has_whatsapp:
                    print(f"  No WS columns to update")
                    conn.execute("""UPDATE students SET name=?, subject=?, email=?, phone=?, whatsapp=?, math_goal=?, reading_goal=?, active=1 WHERE id=?"""
                                 ,(name,subject,email,phone,whatsapp,math_goal,reading_goal,student_id))
                else:
                    print(f"  No whatsapp or WS columns to update")
                    conn.execute("""UPDATE students SET name=?, subject=?, email=?, phone=?, math_goal=?, reading_goal=?, active=1 WHERE id=?"""
                                 ,(name,subject,email,phone,math_goal,reading_goal,student_id))
                updated+=1
            else:
                # INSERT new student
                print(f"INSERTING new student: {name}")
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
        
        # PERMANENTLY delete students not in CSV
        cursor=conn.cursor()
        cursor.execute("SELECT id, name FROM students")
        db_students=cursor.fetchall()
        print(f"CSV names: {csv_names}")
        for student_id, student_name in db_students:
            student_name_lower = student_name.lower().strip()
            if student_name_lower not in csv_names:
                conn.execute("DELETE FROM students WHERE id=?", (student_id,))
                deleted+=1
                print(f"Permanently deleting: {student_name}")
        
        conn.commit()
    return {"added": added, "updated": updated, "deleted": deleted}

def export_csv(path):
    data=get_all_students()
    headers=["ID","Name","Subject","Email","Phone","Photo","Active","BookLoaned","PaperWS","MathGoal","MathWSPerWeek","ReadingGoal","ReadingWSPerWeek"]
    with open(path,"w",newline="",encoding="utf-8") as f:
        writer=csv.writer(f)
        writer.writerow(headers)
        writer.writerows(data)