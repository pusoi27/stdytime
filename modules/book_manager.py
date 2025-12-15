#*****************************
#book_manager.py   ver 04--
#*****************************
import sqlite3
from modules.database import DB_PATH

def get_books():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT id,title,author,available FROM books ORDER BY title;")
        return c.fetchall()