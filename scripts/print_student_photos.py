import sqlite3
conn = sqlite3.connect('data/kumoclock.db')
cur = conn.cursor()
for row in cur.execute('SELECT id, name, photo FROM students ORDER BY id'):
    print(row)
conn.close()
