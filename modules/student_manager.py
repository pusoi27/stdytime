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


def get_all_students():
    has_photo = _table_has_column("students", "photo")
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        if has_photo:
            c.execute("SELECT id, name, subject, level, email, phone, photo, active FROM students ORDER BY name")
            return c.fetchall()
        else:
            c.execute("SELECT id, name, subject, level, email, phone, active FROM students ORDER BY name")
            rows = c.fetchall()
            # Return a consistent tuple shape where index 6 is `photo` (None if missing)
            return [(r[0], r[1], r[2], r[3], r[4], r[5], None) for r in rows]


def get_student(student_id):
    has_photo = _table_has_column("students", "photo")
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        if has_photo:
            row = c.execute("SELECT id,name,subject,level,email,phone,photo,active FROM students WHERE id=?", (student_id,)).fetchone()
            return row
        else:
            row = c.execute("SELECT id,name,subject,level,email,phone,active FROM students WHERE id=?", (student_id,)).fetchone()
            if not row:
                return None
            return (row[0], row[1], row[2], row[3], row[4], row[5], None)


def add_student(name, subject, level, email, phone, photo=None):
    has_photo = _table_has_column("students", "photo")
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        if has_photo:
            c.execute("""INSERT INTO students
                (name,subject,level,email,phone,photo,active)
                VALUES (?,?,?,?,?,?,1)""",
                (name, subject, level, email, phone, photo))
        else:
            c.execute("""INSERT INTO students
                (name,subject,level,email,phone,active)
                VALUES (?,?,?,?,?,1)""",
                (name, subject, level, email, phone))
        conn.commit()


def update_student(sid, name, subject, level, email, phone):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""UPDATE students SET name=?,subject=?,level=?,email=?,phone=? WHERE id=?""",
                  (name,subject,level,email,phone,sid))
        conn.commit()


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
            subject=row.get("subject") or ""
            level=row.get("level") or ""
            email=row.get("email") or ""
            phone=row.get("phone") or ""
            exists=conn.execute("SELECT id FROM students WHERE LOWER(name)=LOWER(?)",(name,)).fetchone()
            if exists: continue
            conn.execute("""INSERT INTO students(name,subject,level,email,phone,active)
                            VALUES(?,?,?,?,?,1)""",(name,subject,level,email,phone))
            added+=1
        conn.commit()
    return added

def export_csv(path):
    data=get_all_students()
    headers=["ID","Name","Subject","Level","Email","Phone","Active"]
    with open(path,"w",newline="",encoding="utf-8") as f:
        writer=csv.writer(f)
        writer.writerow(headers)
        writer.writerows(data)