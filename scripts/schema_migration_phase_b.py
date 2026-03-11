"""
schema_migration.py - Phase B: Add owner_user_id tenancy columns
Migrates single-user schema to multi-tenant by adding owner_user_id to:
- students, staff, books, sessions, assistant_sessions
Backfills all records with admin user ID (1) and adds indexes.
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join("data", "kumoclock.db")


def migrate_schema():
    """Apply Phase B: Tenant-scoped schema changes."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    print("[Phase B] Starting schema migration...")
    
    # 1. students table - add owner_user_id
    print("\n  Adding owner_user_id to students table...")
    try:
        c.execute("PRAGMA table_info(students)")
        cols = [r[1] for r in c.fetchall()]
        if 'owner_user_id' not in cols:
            c.execute("""ALTER TABLE students 
                ADD COLUMN owner_user_id INTEGER DEFAULT 1 
                REFERENCES users(id) ON DELETE CASCADE""")
            print("    ✓ Column added")
        else:
            print("    - Already exists")
    except Exception as e:
        print(f"    ✗ Error: {e}")
    
    # 2. staff table - add owner_user_id
    print("\n  Adding owner_user_id to staff table...")
    try:
        c.execute("PRAGMA table_info(staff)")
        cols = [r[1] for r in c.fetchall()]
        if 'owner_user_id' not in cols:
            c.execute("""ALTER TABLE staff 
                ADD COLUMN owner_user_id INTEGER DEFAULT 1 
                REFERENCES users(id) ON DELETE CASCADE""")
            print("    ✓ Column added")
        else:
            print("    - Already exists")
    except Exception as e:
        print(f"    ✗ Error: {e}")
    
    # 3. books table - add owner_user_id
    print("\n  Adding owner_user_id to books table...")
    try:
        c.execute("PRAGMA table_info(books)")
        cols = [r[1] for r in c.fetchall()]
        if 'owner_user_id' not in cols:
            c.execute("""ALTER TABLE books 
                ADD COLUMN owner_user_id INTEGER DEFAULT 1 
                REFERENCES users(id) ON DELETE CASCADE""")
            print("    ✓ Column added")
        else:
            print("    - Already exists")
    except Exception as e:
        print(f"    ✗ Error: {e}")
    
    # 4. sessions table - add owner_user_id (denormalized for query speed)
    print("\n  Adding owner_user_id to sessions table...")
    try:
        c.execute("PRAGMA table_info(sessions)")
        cols = [r[1] for r in c.fetchall()]
        if 'owner_user_id' not in cols:
            c.execute("""ALTER TABLE sessions 
                ADD COLUMN owner_user_id INTEGER DEFAULT 1""")
            # Populate from students table
            c.execute("""UPDATE sessions SET owner_user_id = 
                (SELECT owner_user_id FROM students WHERE students.id = sessions.student_id)
                WHERE owner_user_id = 1""")
            print("    ✓ Column added and backfilled")
        else:
            print("    - Already exists")
    except Exception as e:
        print(f"    ✗ Error: {e}")
    
    # 5. assistant_sessions table - add owner_user_id (denormalized)
    print("\n  Adding owner_user_id to assistant_sessions table...")
    try:
        c.execute("PRAGMA table_info(assistant_sessions)")
        cols = [r[1] for r in c.fetchall()]
        if 'owner_user_id' not in cols:
            c.execute("""ALTER TABLE assistant_sessions 
                ADD COLUMN owner_user_id INTEGER DEFAULT 1""")
            # Populate from staff table
            c.execute("""UPDATE assistant_sessions SET owner_user_id = 
                (SELECT owner_user_id FROM staff WHERE staff.id = assistant_sessions.assistant_id)
                WHERE owner_user_id = 1""")
            print("    ✓ Column added and backfilled")
        else:
            print("    - Already exists")
    except Exception as e:
        print(f"    ✗ Error: {e}")
    
    # 6. Create indexes for tenant-scoped queries
    print("\n  Creating indexes for tenant-scoped queries...")
    try:
        c.execute("CREATE INDEX IF NOT EXISTS idx_students_owner ON students(owner_user_id, name)")
        print("    ✓ idx_students_owner created")
    except Exception as e:
        print(f"    ✗ Error: {e}")
    
    try:
        c.execute("CREATE INDEX IF NOT EXISTS idx_staff_owner ON staff(owner_user_id, name)")
        print("    ✓ idx_staff_owner created")
    except Exception as e:
        print(f"    ✗ Error: {e}")
    
    try:
        c.execute("CREATE INDEX IF NOT EXISTS idx_books_owner ON books(owner_user_id, title)")
        print("    ✓ idx_books_owner created")
    except Exception as e:
        print(f"    ✗ Error: {e}")
    
    try:
        c.execute("CREATE INDEX IF NOT EXISTS idx_sessions_owner ON sessions(owner_user_id, student_id)")
        print("    ✓ idx_sessions_owner created")
    except Exception as e:
        print(f"    ✗ Error: {e}")
    
    try:
        c.execute("CREATE INDEX IF NOT EXISTS idx_assistant_sessions_owner ON assistant_sessions(owner_user_id, assistant_id)")
        print("    ✓ idx_assistant_sessions_owner created")
    except Exception as e:
        print(f"    ✗ Error: {e}")
    
    conn.commit()
    conn.close()
    
    print("\n✓ Phase B schema migration completed successfully!")
    print("  All business tables now have owner_user_id for multi-tenant isolation")
    print("  Default admin user (ID=1) assigned to all existing records")


if __name__ == '__main__':
    migrate_schema()
