#*****************************
#database.py   ver 04--
#*****************************

import sqlite3, os

DB_PATH = os.path.join("data", "kumoclock.db")

def init_db():
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Students
    c.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            subject TEXT,
            level TEXT,
            book_loaned INTEGER,
            paper_ws INTEGER,
            email TEXT,
            phone TEXT,
            active INTEGER DEFAULT 1
        )
    """)

    # Staff
    c.execute("""
        CREATE TABLE IF NOT EXISTS staff (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            role TEXT,
            email TEXT,
            phone TEXT
        )
    """)

    # Books
    c.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            author TEXT,
            isbn TEXT,
            available INTEGER,
            reading_level TEXT
        )
    """)

    # Sessions (attendance)
    c.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            start_time TEXT,
            end_time TEXT,
            duration INTEGER,
            FOREIGN KEY(student_id) REFERENCES students(id)
        )
    """)

    # Assistant sessions (staff hours)
    c.execute("""
        CREATE TABLE IF NOT EXISTS assistant_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            assistant_id INTEGER,
            start_time TEXT,
            end_time TEXT,
            duration INTEGER,
            FOREIGN KEY(assistant_id) REFERENCES staff(id)
        )
    """)

    conn.commit()

    # Sample data
    if not c.execute("SELECT COUNT(*) FROM students").fetchone()[0]:
        demo = [
            ("Alice Johnson", "S1", "6A", 0, 1, "alice@demo.com", "111-222", 1),
            ("Bob Smith", "S2", "5A", 1, 0, "bob@demo.com", "222-333", 1)
        ]
        c.executemany("""INSERT INTO students
            (name, subject, level, book_loaned, paper_ws, email, phone, active)
            VALUES (?,?,?,?,?,?,?,?)""", demo)

    if not c.execute("SELECT COUNT(*) FROM staff").fetchone()[0]:
        c.execute("INSERT INTO staff (name,role,email,phone) VALUES (?,?,?,?)",
                  ("John Doe","Admin","admin@demo.com","777-888"))

    if not c.execute("SELECT COUNT(*) FROM books").fetchone()[0]:
        c.execute("INSERT INTO books (title,author,isbn,available,reading_level)"
                  " VALUES (?,?,?,?,?)",
                  ("Mathematics Basics","KumoPress","111222333",1,"5A"))

    conn.commit(); conn.close()

    # Ensure `photo` column exists on students table (migration for image filenames)
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(students)")
        cols = [r[1] for r in cur.fetchall()]
        if "photo" not in cols:
            cur.execute("ALTER TABLE students ADD COLUMN photo TEXT")
        conn.commit()

    def ensure_template():
        os.makedirs("templates", exist_ok=True)
        tpl_path = os.path.join("templates", "student_template.csv")
        if not os.path.exists(tpl_path):
            with open(tpl_path, "w", encoding="utf-8") as f:
                f.write("name,subject,level,email,phone\n")
                f.write("Example Student,S1,6A,example@example.com,123456789\n")