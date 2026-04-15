import sqlite3

DB_PATH = r"c:/Users/octav/AppData/Local/Programs/Python/Python312/stdytime/data/Stdytime.db"

with sqlite3.connect(DB_PATH) as conn:
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS students_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            subject TEXT,
            level TEXT,
            book_loaned INTEGER DEFAULT 0,
            paper_ws INTEGER DEFAULT 0,
            email TEXT,
            phone TEXT,
            active INTEGER DEFAULT 1,
            el INTEGER DEFAULT 0,
            pi INTEGER DEFAULT 0,
            v INTEGER DEFAULT 0,
            day1 TEXT DEFAULT '',
            day1_time TEXT DEFAULT '',
            day2 TEXT DEFAULT '',
            day2_time TEXT DEFAULT '',
            owner_user_id INTEGER NOT NULL DEFAULT 1
        )
    """)
    c.execute("""
        INSERT INTO students_new (id, name, subject, level, book_loaned, paper_ws, email, phone, active, el, pi, v, day1, day1_time, day2, day2_time, owner_user_id)
        SELECT id, name, subject, level, book_loaned, paper_ws, email, phone, active, el, pi, v, day1, day1_time, day2, day2_time, owner_user_id FROM students
    """)
    c.execute("DROP TABLE students")
    c.execute("ALTER TABLE students_new RENAME TO students")
    conn.commit()
print("Student table migrated: math/reading goals and ws/week fields removed.")
