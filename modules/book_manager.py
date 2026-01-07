#*****************************
#book_manager.py   ver 04--
#*****************************
import sqlite3
from modules.database import DB_PATH
from datetime import datetime

def get_books():
    """Get all books with all columns."""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""
            SELECT id, title, author, available, reading_level, isbn, isbn13, publisher, copies, borrower_id 
            FROM books 
            ORDER BY title
        """)
        return c.fetchall()


def get_book(book_id):
    """Get a single book by ID."""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""
            SELECT id, title, author, available, reading_level, isbn, isbn13, publisher, copies, borrower_id 
            FROM books 
            WHERE id = ?
        """, (book_id,))
        return c.fetchone()


def add_book(title, author, publisher, isbn=None, isbn13=None, available=1, reading_level=None, copies=1):
    """Add a new book to the database."""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""
            INSERT INTO books (title, author, publisher, isbn, isbn13, available, reading_level, copies)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (title, author, publisher, isbn, isbn13, available, reading_level, copies))
        conn.commit()
        return c.lastrowid


def update_book(book_id, title=None, author=None, publisher=None, isbn=None, isbn13=None, available=None, reading_level=None, copies=None, borrower_id=None):
    """Update a book."""
    updates = []
    params = []
    
    if title is not None:
        updates.append("title = ?")
        params.append(title)
    if author is not None:
        updates.append("author = ?")
        params.append(author)
    if publisher is not None:
        updates.append("publisher = ?")
        params.append(publisher)
    if isbn is not None:
        updates.append("isbn = ?")
        params.append(isbn)
    if isbn13 is not None:
        updates.append("isbn13 = ?")
        params.append(isbn13)
    if available is not None:
        updates.append("available = ?")
        params.append(available)
    if reading_level is not None:
        updates.append("reading_level = ?")
        params.append(reading_level)
    if copies is not None:
        updates.append("copies = ?")
        params.append(copies)
    if borrower_id is not None:
        updates.append("borrower_id = ?")
        params.append(borrower_id)
    
    if not updates:
        return False
    
    params.append(book_id)
    query = f"UPDATE books SET {', '.join(updates)} WHERE id = ?"
    
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute(query, params)
        conn.commit()
        return c.rowcount > 0


def delete_book(book_id):
    """Delete a book."""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM books WHERE id = ?", (book_id,))
        conn.commit()
        return c.rowcount > 0


def enforce_isbn_availability_rule():
    """Set available=0 for any book that has neither ISBN-10 nor ISBN-13.
    This keeps DB state consistent so any view using raw `available` won't
    erroneously show books without identifiers as available.
    Also, if a book has an ISBN and no borrower and is marked unavailable,
    flip it back to available=1 so it can be loaned.
    """
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute(
            """
            UPDATE books
               SET available = 0
             WHERE (isbn IS NULL OR TRIM(isbn) = '')
               AND (isbn13 IS NULL OR TRIM(isbn13) = '')
            """
        )
        c.execute(
            """
            UPDATE books
               SET available = 1
             WHERE (available IS NULL OR available = 0)
               AND ( (isbn IS NOT NULL AND TRIM(isbn) != '')
                     OR (isbn13 IS NOT NULL AND TRIM(isbn13) != '') )
               AND (borrower_id IS NULL)
            """
        )
        conn.commit()


def ensure_book_loans_table():
    """Create book_loans table if it does not exist."""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS book_loans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id INTEGER NOT NULL,
                student_id INTEGER NOT NULL,
                checkout_date TEXT NOT NULL,
                return_date TEXT,
                FOREIGN KEY(book_id) REFERENCES books(id),
                FOREIGN KEY(student_id) REFERENCES students(id)
            )
            """
        )
        conn.commit()


def loan_book(book_id: int, student_id: int):
    """Mark a book as loaned to a student and record the checkout date."""
    ensure_book_loans_table()
    checkout_date = datetime.utcnow().isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        # update book availability
        c.execute(
            "UPDATE books SET available = 0, borrower_id = ? WHERE id = ?",
            (student_id, book_id)
        )
        # insert loan record
        c.execute(
            """
            INSERT INTO book_loans (book_id, student_id, checkout_date)
            VALUES (?, ?, ?)
            """,
            (book_id, student_id, checkout_date)
        )
        conn.commit()
        return checkout_date


def return_book(book_id: int):
    """Mark a book as returned and set return_date for the open loan."""
    ensure_book_loans_table()
    return_date = datetime.utcnow().isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute(
            "UPDATE books SET available = 1, borrower_id = NULL WHERE id = ?",
            (book_id,)
        )
        # close latest open loan
        c.execute(
            """
            UPDATE book_loans
            SET return_date = ?
            WHERE id = (
                SELECT id FROM book_loans
                WHERE book_id = ? AND return_date IS NULL
                ORDER BY checkout_date DESC
                LIMIT 1
            )
            """,
            (return_date, book_id)
        )
        conn.commit()
        return return_date


def search_books(query=None, level=None, available_only=False):
    """Search books by various criteria."""
    sql = "SELECT id, title, author, available, reading_level, isbn, isbn13, publisher, copies, borrower_id FROM books WHERE 1=1"
    params = []
    
    if query:
        sql += " AND (title LIKE ? OR author LIKE ? OR publisher LIKE ?)"
        search_term = f"%{query}%"
        params.extend([search_term, search_term, search_term])
    
    if level:
        sql += " AND reading_level = ?"
        params.append(level)
    
    if available_only:
        sql += " AND available = 1"
    
    sql += " ORDER BY title"
    
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute(sql, params)
        return c.fetchall()


def find_book_by_title(title: str):
    """Find a single book by exact title (case-insensitive)."""
    if not title:
        return None
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute(
            "SELECT id, title, author, available, reading_level, isbn, isbn13, publisher, copies, borrower_id "
            "FROM books WHERE lower(title) = lower(?) LIMIT 1",
            (title.strip(),)
        )
        return c.fetchone()


def find_book_by_isbn(isbn: str):
    """Find a single book by ISBN (checks both ISBN-10 and ISBN-13)."""
    if not isbn:
        return None
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute(
            "SELECT id, title, author, available, reading_level, isbn, isbn13, publisher, copies, borrower_id "
            "FROM books WHERE isbn = ? OR isbn13 = ? LIMIT 1",
            (isbn.strip(), isbn.strip())
        )
        return c.fetchone()