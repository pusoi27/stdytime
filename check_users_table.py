import sqlite3

conn = sqlite3.connect('data/kumoclock.db')
c = conn.cursor()

# Check if users table exists
c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
table_exists = c.fetchone()

if table_exists:
    print('[OK] Users table exists')
    c.execute('SELECT email, role, is_active FROM users LIMIT 5')
    rows = c.fetchall()
    for row in rows:
        print(f'  - Email: {row[0]}, Role: {row[1]}, Active: {row[2]}')
else:
    print('[ERROR] Users table NOT found')

conn.close()
