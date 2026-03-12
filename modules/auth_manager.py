"""
auth_manager.py - User authentication and password management.
Handles user registration, login verification, and password hashing.
"""

import sqlite3
import os
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask import session

DB_PATH = os.path.join("data", "kumoclock.db")

ROLE_ADMIN = "admin"
ROLE_INSTRUCTOR = "instructor"
ROLE_ASSISTANT = "assistant"
VALID_ROLES = [ROLE_ADMIN, ROLE_INSTRUCTOR, ROLE_ASSISTANT]


def get_current_user_id():
    """Get current user ID from Flask session. Returns 1 (admin) if no user logged in."""
    return session.get('user_id', 1)


class User:
    """User model representing an authenticated user."""
    
    def __init__(self, user_id, email, role, is_active=True, must_change_password=False):
        self.id = user_id
        self.email = email
        self.role = role
        self.is_active = is_active
        self.must_change_password = bool(must_change_password)
    
    def __repr__(self):
        return f"<User {self.email} ({self.role})>"
    
    def is_authenticated(self):
        return self.is_active
    
    def is_admin(self):
        return self.role == ROLE_ADMIN
    
    def is_instructor(self):
        return self.role == ROLE_INSTRUCTOR
    
    def is_assistant(self):
        return self.role == ROLE_ASSISTANT


def get_user_by_id(user_id):
    """Fetch user by ID from database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT id, email, role, is_active FROM users WHERE id = ?", (user_id,))
        row = c.fetchone()
        conn.close()
        if row:
            return User(row[0], row[1], row[2], bool(row[3]))
        return None
    except Exception as e:
        print(f"[auth] Error fetching user by ID: {e}")
        return None


def get_user_by_email(email):
    """Fetch user by email from database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT id, email, role, is_active FROM users WHERE email = ?", (email,))
        row = c.fetchone()
        conn.close()
        if row:
            return User(row[0], row[1], row[2], bool(row[3]))
        return None
    except Exception as e:
        print(f"[auth] Error fetching user by email: {e}")
        return None


def authenticate_user(email, password):
    """Verify email and password. Returns User object if valid, None otherwise."""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "SELECT id, email, role, is_active, password_hash, must_change_password FROM users WHERE email = ?",
            (email,)
        )
        row = c.fetchone()
        conn.close()
        
        if not row:
            return None
        
        user_id, user_email, role, is_active, password_hash, must_change_password = row
        
        # Check if user is active
        if not is_active:
            return None
        
        # Verify password hash
        if not check_password_hash(password_hash, password):
            return None
        
        return User(user_id, user_email, role, is_active, must_change_password)
    
    except Exception as e:
        print(f"[auth] Error authenticating user: {e}")
        return None


def register_user(email, password, role=ROLE_INSTRUCTOR, is_active=True):
    """Create new user with hashed password. Returns (success: bool, user_id: int or error_msg: str)."""
    try:
        # Validate email not already registered
        existing = get_user_by_email(email)
        if existing:
            return (False, "Email already registered")
        
        # Validate role
        if role not in VALID_ROLES:
            return (False, f"Invalid role. Must be one of: {', '.join(VALID_ROLES)}")
        
        # Validate password strength (minimum 8 chars)
        if len(password) < 8:
            return (False, "Password must be at least 8 characters")
        
        # Hash password
        password_hash = generate_password_hash(password, method='pbkdf2:sha256')
        
        # Insert user
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        now = datetime.now().isoformat()
        
        c.execute("""
            INSERT INTO users (email, password_hash, role, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (email, password_hash, role, int(is_active), now, now))
        
        user_id = c.lastrowid
        conn.commit()
        conn.close()
        
        return (True, user_id)
    
    except Exception as e:
        print(f"[auth] Error registering user: {e}")
        return (False, f"Registration failed: {str(e)}")


def initialize_new_user_data(user_id: int):
    """Seed a newly registered user with starter records.

    Creates:
    - 2 fictitious students
    - 2 fictitious assistants
    - A copy of existing book titles with available=0 and copies=0

    Existing data for the user is left untouched (idempotent behavior).
    Returns (success: bool, message: str).
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        # Seed two fictitious students if user has no students yet
        student_count = c.execute(
            "SELECT COUNT(*) FROM students WHERE owner_user_id = ?",
            (user_id,),
        ).fetchone()[0]

        if student_count == 0:
            fictitious_students = [
                ("Ava Thompson", "S1", "ava.thompson@example.com", "555-0101", user_id),
                ("Liam Carter", "S2", "liam.carter@example.com", "555-0102", user_id),
            ]
            c.executemany(
                """
                INSERT INTO students (name, subject, email, phone, active, owner_user_id)
                VALUES (?, ?, ?, ?, 1, ?)
                """,
                fictitious_students,
            )

        # Seed two fictitious assistants if user has no staff yet
        assistant_count = c.execute(
            "SELECT COUNT(*) FROM staff WHERE owner_user_id = ?",
            (user_id,),
        ).fetchone()[0]

        if assistant_count == 0:
            fictitious_assistants = [
                ("Noah Bennett", "Assistant", "noah.bennett@example.com", "555-0201", user_id),
                ("Mia Rodriguez", "Assistant", "mia.rodriguez@example.com", "555-0202", user_id),
            ]
            c.executemany(
                """
                INSERT INTO staff (name, role, email, phone, owner_user_id)
                VALUES (?, ?, ?, ?, ?)
                """,
                fictitious_assistants,
            )

        # Copy existing book catalog for this user if user has no books yet.
        # Keep titles/metadata, but force unavailable with copies erased (0).
        book_count = c.execute(
            "SELECT COUNT(*) FROM books WHERE owner_user_id = ?",
            (user_id,),
        ).fetchone()[0]

        if book_count == 0:
            source_books = c.execute(
                """
                SELECT title, author, isbn, isbn13, publisher, reading_level
                FROM books
                WHERE owner_user_id = 1
                ORDER BY title
                """
            ).fetchall()

            if not source_books:
                source_books = c.execute(
                    """
                    SELECT title, author, isbn, isbn13, publisher, reading_level
                    FROM books
                    WHERE title IS NOT NULL AND TRIM(title) != ''
                    ORDER BY title
                    """
                ).fetchall()

            if source_books:
                c.executemany(
                    """
                    INSERT INTO books (
                        title, author, isbn, isbn13, publisher, available, reading_level, copies, borrower_id, owner_user_id
                    )
                    VALUES (?, ?, ?, ?, ?, 0, ?, 0, NULL, ?)
                    """,
                    [
                        (title, author, isbn, isbn13, publisher, reading_level, user_id)
                        for (title, author, isbn, isbn13, publisher, reading_level) in source_books
                    ],
                )

        conn.commit()
        conn.close()
        return (True, "Starter data initialized")
    except Exception as e:
        print(f"[auth] Error initializing starter data for user {user_id}: {e}")
        return (False, f"Starter data initialization failed: {str(e)}")


def clear_must_change_password(user_id):
    """Clear the must_change_password flag after user sets a new password."""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        now = datetime.now().isoformat()
        c.execute(
            "UPDATE users SET must_change_password = 0, updated_at = ? WHERE id = ?",
            (now, user_id)
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"[auth] Error clearing must_change_password: {e}")
        return False


def update_user_password(user_id, new_password):
    """Update user password. Returns (success: bool, message: str)."""
    try:
        # Validate password strength
        if len(new_password) < 8:
            return (False, "Password must be at least 8 characters")
        
        password_hash = generate_password_hash(new_password, method='pbkdf2:sha256')
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        now = datetime.now().isoformat()
        
        c.execute("""
            UPDATE users SET password_hash = ?, updated_at = ? WHERE id = ?
        """, (password_hash, now, user_id))
        
        conn.commit()
        conn.close()
        
        if c.rowcount == 0:
            return (False, "User not found")
        
        return (True, "Password updated successfully")
    
    except Exception as e:
        print(f"[auth] Error updating password: {e}")
        return (False, f"Update failed: {str(e)}")


def deactivate_user(user_id):
    """Deactivate a user account."""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        now = datetime.now().isoformat()
        
        c.execute("""
            UPDATE users SET is_active = 0, updated_at = ? WHERE id = ?
        """, (now, user_id))
        
        conn.commit()
        conn.close()
        
        return (True, "User deactivated")
    
    except Exception as e:
        print(f"[auth] Error deactivating user: {e}")
        return (False, f"Deactivation failed: {str(e)}")


def list_all_users():
    """Fetch all users (for admin panel)."""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""
            SELECT id, email, role, is_active, created_at FROM users ORDER BY created_at DESC
        """)
        rows = c.fetchall()
        conn.close()
        
        users = []
        for row in rows:
            users.append({
                'id': row[0],
                'email': row[1],
                'role': row[2],
                'is_active': bool(row[3]),
                'created_at': row[4]
            })
        
        return users
    
    except Exception as e:
        print(f"[auth] Error listing users: {e}")
        return []
