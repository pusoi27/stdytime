# routes/books.py
"""Books management routes."""

from flask import render_template, request, jsonify, redirect, url_for, flash
from modules.book_manager import (
    get_books,
    find_book_by_title,
    find_book_by_isbn,
    add_book,
    update_book,
    get_book,
    delete_book,
    loan_book,
    return_book,
    enforce_isbn_availability_rule,
)
from modules.student_manager import get_student
import sqlite3
from modules.database import DB_PATH
import requests
import re


def register_book_routes(app):
    """Register book management routes."""
    
    # ----------------------------------------
    # Add Book page
    # ----------------------------------------
    @app.route("/books/add")
    def books_add():
        return render_template("book_add.html", edit_book_id=None)

    @app.route("/books/edit/<int:book_id>")
    def books_edit(book_id: int):
        book = get_book(book_id)
        if not book:
            flash("Book not found", "danger")
            return redirect(url_for("books_list"))
        return render_template("book_add.html", edit_book_id=book_id)
    
    @app.route("/books")
    def books_list():
        """Display all books in the library."""
        try:
            # Normalize DB: any book without ISBN should be unavailable
            enforce_isbn_availability_rule()
            books = get_books()
            
            # Convert to list of dicts for easier template rendering
            books_list = []
            for book in books:
                borrower_id = book[9] if len(book) > 9 else None
                borrower_name = None
                if borrower_id:
                    student = get_student(borrower_id)
                    if student:
                        borrower_name = student[1]
                
                # Book is available only if it has ISBN AND no borrower
                has_isbn = (book[5] if len(book) > 5 else None) or (book[6] if len(book) > 6 else None)
                is_available = 1 if (has_isbn and not borrower_id) else 0
                
                books_list.append({
                    'id': book[0],
                    'title': book[1],
                    'author': book[2],
                    'available': is_available,
                    'reading_level': book[4] if len(book) > 4 else None,
                    'isbn': book[5] if len(book) > 5 else None,
                    'isbn13': book[6] if len(book) > 6 else None,
                    'publisher': book[7] if len(book) > 7 else None,
                    'copies': book[8] if len(book) > 8 else 1,
                    'borrower_id': borrower_id,
                    'borrower_name': borrower_name,
                })
            
            return render_template(
                "books_list.html",
                books=books_list,
                total_books=len(books_list)
            )
        except Exception as e:
            flash(f"Error loading books: {str(e)}", "danger")
            return render_template("books_list.html", books=[], total_books=0)
    
    @app.route("/api/books/search")
    def api_books_search():
        """API endpoint to search/filter books."""
        query = request.args.get('q', '').strip().lower()
        level = request.args.get('level', '').strip()
        
        try:
            # Normalize DB before search
            enforce_isbn_availability_rule()
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            
            # Build dynamic query
            sql = "SELECT id, title, author, available, reading_level, isbn, isbn13, publisher, copies, borrower_id FROM books WHERE 1=1"
            params = []
            
            if query:
                sql += " AND (title LIKE ? OR author LIKE ? OR publisher LIKE ?)"
                search_term = f"%{query}%"
                params.extend([search_term, search_term, search_term])
            
            if level:
                sql += " AND reading_level = ?"
                params.append(level)
            
            sql += " ORDER BY title"
            
            c.execute(sql, params)
            books = c.fetchall()
            conn.close()
            
            books_list = []
            for book in books:
                # Use helper to include borrower_name and derived fields
                data = _book_row_to_dict(book)
                books_list.append(data)
            
            return jsonify({'books': books_list, 'count': len(books_list)})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route("/api/books/levels")
    def api_books_levels():
        """Get all unique reading levels."""
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT DISTINCT reading_level FROM books ORDER BY reading_level")
            levels = [row[0] for row in c.fetchall()]
            conn.close()
            return jsonify({'levels': levels})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route("/books/loan")
    def books_loan_page():
        return render_template("book_loan.html")

    @app.route("/api/students/suggest")
    def api_students_suggest():
        """Return student name suggestions for autocomplete."""
        q = (request.args.get('q') or '').strip()
        if not q or len(q) < 3:
            return jsonify({'suggestions': []})
        
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            rows = c.execute(
                "SELECT id, name FROM students WHERE lower(name) LIKE lower(?) ORDER BY name LIMIT 10",
                (f"{q}%",)
            ).fetchall()
            suggestions = [{'id': row[0], 'name': row[1]} for row in rows]
            return jsonify({'suggestions': suggestions})

    @app.route("/api/students/lookup")
    def api_students_lookup():
        """Lookup a student by id (numeric) or exact name (case-insensitive)."""
        q = (request.args.get('q') or '').strip()
        if not q:
            return jsonify({'error': 'Student query is required.'}), 400
        student = None
        
        # Parse QR code format: "ID:4Name:Aahan A." or "ID:4\nName:Aahan A."
        import re
        qr_match = re.match(r'^ID:(\d+)', q)
        if qr_match:
            student_id = int(qr_match.group(1))
            student = get_student(student_id)
            if student:
                return jsonify({'student': {'id': student[0], 'name': student[1]}})
        
        if q.isdigit():
            student = get_student(int(q))
            if student:
                return jsonify({'student': {'id': student[0], 'name': student[1]}})
        # name lookup
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            row = c.execute(
                "SELECT id, name FROM students WHERE lower(name) = lower(?) LIMIT 1",
                (q,)
            ).fetchone()
            if row:
                return jsonify({'student': {'id': row[0], 'name': row[1]}})
        return jsonify({'error': 'Student not found.'}), 404

    # ----------------------------------------
    # ISBN lookup (fetch details from Library of Congress JSON)
    # ----------------------------------------
    @app.route("/api/books/isbn_lookup")
    def api_books_isbn_lookup():
        isbn_raw = (request.args.get('isbn') or '').strip()
        isbn = _sanitize_isbn(isbn_raw)

        if not isbn or len(isbn) not in (10, 13):
            return jsonify({'error': 'Please scan or enter a valid ISBN-10 or ISBN-13.'}), 400

        try:
            data = _lookup_isbn_online(isbn)
        except Exception as e:
            return jsonify({'error': f"Lookup failed: {e}"}), 502

        # Check for existing book by ISBN
        existing_by_isbn = find_book_by_isbn(isbn)
        isbn_existing_id = existing_by_isbn[0] if existing_by_isbn else None
        isbn_existing_book = None
        if isbn_existing_id:
            isbn_existing_book = get_book(isbn_existing_id)

        # Check for existing book by title
        existing = find_book_by_title(data.get('title')) if data.get('title') else None
        existing_id = existing[0] if existing else None
        existing_book = None
        if existing_id:
            existing_book = get_book(existing_id)

        return jsonify({
            'book': data,
            'existing_id': existing_id,
            'existing_book': _book_row_to_dict(existing_book) if existing_book else None,
            'isbn_existing_id': isbn_existing_id,
            'isbn_existing_book': _book_row_to_dict(isbn_existing_book) if isbn_existing_book else None,
            'message': "Book found" if data else "No data found",
        })

    # ----------------------------------------
    # Save / upsert book
    # ----------------------------------------
    @app.route("/api/books/save", methods=["POST"])
    def api_books_save():
        payload = request.get_json(silent=True) or {}

        title = (payload.get('title') or '').strip()
        author = (payload.get('author') or '').strip()
        publisher = (payload.get('publisher') or '').strip()
        isbn = _sanitize_isbn(payload.get('isbn')) if payload.get('isbn') else None
        isbn13 = _sanitize_isbn(payload.get('isbn13')) if payload.get('isbn13') else None
        level = (payload.get('reading_level') or '').strip()
        copies = int(payload.get('copies') or 1)
        existing_id = payload.get('id')

        # If existing_id not provided, try to find by title to prevent duplicates
        if not existing_id and title:
            existing = find_book_by_title(title)
            if existing:
                existing_id = existing[0]

        # Existing book: update provided fields
        if existing_id:
            try:
                update_book(
                    existing_id,
                    title=title or None,
                    author=author or None,
                    publisher=publisher or None,
                    isbn=isbn,
                    isbn13=isbn13,
                    reading_level=level or None,
                    copies=copies,
                    # Force availability to No if no ISBN present
                    available=1 if (isbn or isbn13) else 0,
                    borrower_id=payload.get('borrower_id') if payload.get('borrower_id') is not None else None,
                )
                return jsonify({'status': 'updated', 'id': existing_id})
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        # New book: require title and level
        if not title:
            return jsonify({'error': 'Title is required.'}), 400
        if not level:
            return jsonify({'error': 'Reading level is required for new books.'}), 400

        try:
            new_id = add_book(
                title=title,
                author=author,
                publisher=publisher,
                isbn=isbn,
                isbn13=isbn13,
                # New books without ISBN should be marked unavailable
                available=1 if (isbn or isbn13) else 0,
                reading_level=level,
                copies=copies,
            )
            return jsonify({'status': 'created', 'id': new_id})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # ----------------------------------------
    # Increase book copies
    # ----------------------------------------
    @app.route("/api/books/increase_copies", methods=["POST"])
    def api_books_increase_copies():
        """Increase the number of copies for an existing book."""
        payload = request.get_json(silent=True) or {}
        book_id = payload.get('id')
        additional_copies = int(payload.get('additional_copies') or 1)

        if not book_id:
            return jsonify({'error': 'Book ID is required.'}), 400

        try:
            # Get current book
            book = get_book(book_id)
            if not book:
                return jsonify({'error': 'Book not found.'}), 404

            current_copies = book[8] if len(book) > 8 else 1
            new_copies = current_copies + additional_copies

            # Update copies count
            update_book(book_id, copies=new_copies)
            return jsonify({'status': 'updated', 'id': book_id, 'new_copies': new_copies})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # ----------------------------------------
    # Loan / Return endpoints
    # ----------------------------------------
    @app.route("/api/books/loan", methods=["POST"])
    def api_books_loan():
        payload = request.get_json(silent=True) or {}
        book_id = payload.get('book_id')
        student_input = (payload.get('student_input') or '').strip()
        student_id = payload.get('student_id')

        if not book_id:
            return jsonify({'error': 'Book ID is required.'}), 400
        if not (student_input or student_id):
            return jsonify({'error': 'Student name or ID is required.'}), 400

        try:
            book = get_book(book_id)
            if not book:
                return jsonify({'error': 'Book not found.'}), 404
            # Disallow loaning books without any ISBN
            if not (book[5] or book[6]):
                return jsonify({'error': 'Book cannot be loaned without an ISBN.'}), 400
            if not book[3]:
                return jsonify({'error': 'Book is already loaned.'}), 400

            # Resolve student by explicit id, by numeric QR, or by name
            student_row = None
            if student_id:
                student_row = get_student(int(student_id))
            if not student_row and student_input:
                if student_input.isdigit():
                    student_row = get_student(int(student_input))
                if not student_row:
                    with sqlite3.connect(DB_PATH) as conn:
                        c = conn.cursor()
                        row = c.execute(
                            "SELECT id, name FROM students WHERE lower(name)=lower(?) LIMIT 1",
                            (student_input,)
                        ).fetchone()
                        if row:
                            student_row = (row[0], row[1])
            if not student_row:
                return jsonify({'error': 'Student not found.'}), 404

            student_id = student_row[0]
            checkout_date = loan_book(book_id, student_id)
            return jsonify({
                'status': 'loaned',
                'book_id': book_id,
                'student_id': student_id,
                'student_name': student_row[1] if len(student_row) > 1 else None,
                'checkout_date': checkout_date,
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route("/api/books/return", methods=["POST"])
    def api_books_return():
        payload = request.get_json(silent=True) or {}
        book_id = payload.get('book_id')
        if not book_id:
            return jsonify({'error': 'Book ID is required.'}), 400
        try:
            book = get_book(book_id)
            if not book:
                return jsonify({'error': 'Book not found.'}), 404
            if book[3]:
                return jsonify({'error': 'Book is already available.'}), 400
            return_date = return_book(book_id)
            return jsonify({'status': 'returned', 'book_id': book_id, 'return_date': return_date})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # ----------------------------------------
    # Get single book details (for editing)
    # ----------------------------------------
    @app.route("/api/books/<int:book_id>")
    def api_books_get(book_id: int):
        try:
            book = get_book(book_id)
            if not book:
                return jsonify({'error': 'Book not found'}), 404
            data = _book_row_to_dict(book)
            if data.get('borrower_id'):
                student = get_student(data['borrower_id'])
                if student:
                    data['borrower_name'] = student[1]
            return jsonify({'book': data})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # ----------------------------------------
    # Delete book
    # ----------------------------------------
    @app.route("/books/delete/<int:book_id>")
    def books_delete(book_id: int):
        try:
            success = delete_book(book_id)
            if success:
                flash("Book deleted", "success")
            else:
                flash("Book not found", "warning")
        except Exception as e:
            flash(f"Delete failed: {e}", "danger")
        return redirect(url_for("books_list"))


# ================================================
# Helper functions
# ================================================
def _sanitize_isbn(value: str):
    if not value:
        return None
    digits = re.sub(r"[^0-9Xx]", "", value)
    return digits.upper()


def _lookup_isbn_online(isbn: str):
    """Fetch book details from Google Books API using ISBN."""
    url = "https://www.googleapis.com/books/v1/volumes"
    params = {
        "q": f"isbn:{isbn}",
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; KumoClock/1.0)",
    }
    resp = requests.get(url, params=params, headers=headers, timeout=10)
    if resp.status_code != 200:
        raise RuntimeError(f"Google Books API returned {resp.status_code}")

    try:
        payload = resp.json()
    except Exception as exc:
        raise RuntimeError("Invalid JSON response from Google Books API") from exc

    items = payload.get("items") or []
    if not items:
        raise RuntimeError("No results found on Google Books for this ISBN")

    first_book = items[0] or {}
    volume_info = first_book.get("volumeInfo") or {}

    # Extract fields with safe fallbacks
    title = volume_info.get("title") or ""
    
    # Author may be a list; take first one
    authors = volume_info.get("authors") or []
    author = authors[0] if authors else ""
    
    # Publisher
    publisher = volume_info.get("publisher") or ""
    
    # ISBN info
    isbn_data = volume_info.get("industryIdentifiers") or []
    isbn10 = None
    isbn13 = None
    for id_entry in isbn_data:
        if id_entry.get("type") == "ISBN_10":
            isbn10 = id_entry.get("identifier")
        elif id_entry.get("type") == "ISBN_13":
            isbn13 = id_entry.get("identifier")
    
    # Fallback: use input ISBN if not found in response
    if not isbn10 and not isbn13:
        if len(isbn) == 10:
            isbn10 = isbn
        elif len(isbn) == 13:
            isbn13 = isbn

    if not title:
        raise RuntimeError("No book title found in Google Books response")

    return {
        'title': title.strip(),
        'author': author.strip(),
        'publisher': publisher.strip(),
        'isbn': isbn10,
        'isbn13': isbn13,
    }


def _first_text(items):
    return items[0].strip() if items else None


def _book_row_to_dict(row):
    if not row:
        return None
    borrower_id = row[9]
    borrower_name = None
    if borrower_id:
        student = get_student(borrower_id)
        if student:
            borrower_name = student[1]
    
    # Book is available only if it has ISBN AND no borrower
    has_isbn = row[5] or row[6]
    is_available = 1 if (has_isbn and not borrower_id) else 0
    
    return {
        'id': row[0],
        'title': row[1],
        'author': row[2],
        'available': is_available,
        'reading_level': row[4],
        'isbn': row[5],
        'isbn13': row[6],
        'publisher': row[7],
        'copies': row[8],
        'borrower_id': borrower_id,
        'borrower_name': borrower_name,
    }
