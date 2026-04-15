#*****************************
#student_manager.py   ver 04--------------
#*****************************

import sqlite3, csv, os, json
from modules.database import DB_PATH


def safe_int(value, default=0):
    """Safely convert value to int, returning default if empty or invalid."""
    try:
        val = str(value).strip()
        if not val:
            return default
        return int(val)
    except (ValueError, TypeError):
        return default


def normalize_subject_entries(subjects, minutes):
    """Normalize subjects and their durations.

    Returns:
        tuple[list[str], list[int], int]: (subjects, minutes, total_minutes)
    """
    cleaned_subjects = []
    cleaned_minutes = []

    for idx, raw_subj in enumerate(subjects or []):
        subj = str(raw_subj or "").strip()
        if not subj:
            continue
        minute_raw = minutes[idx] if idx < len(minutes or []) else 30
        minute_val = max(5, safe_int(minute_raw, default=30))
        cleaned_subjects.append(subj)
        cleaned_minutes.append(minute_val)

    if not cleaned_subjects:
        cleaned_subjects = ["Math"]
        cleaned_minutes = [30]

    total_minutes = sum(cleaned_minutes) if cleaned_minutes else 30
    return cleaned_subjects, cleaned_minutes, total_minutes


def get_all_students(owner_user_id=1):
    """Get all active students with their information for a specific user.
    
    Args:
        owner_user_id: User ID to filter students (default: 1 for backward compatibility)
    """
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        # Get only active student data for this owner
        c.execute("""
             SELECT s.id, s.name, s.subject, s.level, s.email, s.phone, '' AS legacy_contact, s.active, s.book_loaned, s.paper_ws,
                 s.el, s.pi, s.v, s.day1, s.day1_time, s.day2, s.day2_time, s.subjects_json, s.subject_minutes_json, s.total_study_minutes
            FROM students s
            WHERE s.active = 1 AND s.owner_user_id = ?
            ORDER BY s.name
        """, (owner_user_id,))
        return c.fetchall()


def get_student(student_id, owner_user_id=1):
    """Get a single student by ID, with ownership check.
    
    Args:
        student_id: Student ID to retrieve
        owner_user_id: User ID to verify ownership (default: 1 for backward compatibility)
    """
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        row = c.execute("""
            SELECT id,name,subject,email,phone,'' AS legacy_contact,active,book_loaned,paper_ws,
                   el,pi,v,day1,day2,day1_time,day2_time,subjects_json,subject_minutes_json,total_study_minutes
            FROM students WHERE id=? AND owner_user_id=?
        """, (student_id, owner_user_id)).fetchone()
        return row


def get_student_static_profile(student_id, owner_user_id=1):
    """Get a single student by ID as a dictionary."""
    row = get_student(student_id, owner_user_id=owner_user_id)
    if not row:
        return None
    return {
        'id': row[0],
        'name': row[1],
        'subject': row[2],
        'email': row[3],
        'phone': row[4],
        'active': row[6],
        'book_loaned': row[7],
        'paper_ws': row[8],
        'el': row[9],
        'pi': row[10],
        'v': row[11],
        'day1': row[12],
        'day2': row[13],
        'day1_time': row[14],
        'day2_time': row[15],
        'subjects': json.loads(row[16] or '[]') if len(row) > 16 else ([row[2]] if row[2] else []),
        'subject_minutes': json.loads(row[17] or '[]') if len(row) > 17 else ([30] if row[2] else []),
        'total_study_minutes': int(row[18] or 30) if len(row) > 18 else 30,
    }



def add_student(name, subject, email, phone, book_loaned=0, paper_ws=0, el=0, pi=0, v=0, day1="", day2="", day1_time="", day2_time="", owner_user_id=1, subjects=None, subject_minutes=None):
    """Add a new student to the database and automatically generate QR code.
    
    Args:
        owner_user_id: User ID to assign as owner (default: 1 for backward compatibility)
    """
    subjects_list, minutes_list, total_minutes = normalize_subject_entries(
        subjects if subjects is not None else [subject],
        subject_minutes if subject_minutes is not None else [30],
    )
    primary_subject = subjects_list[0]

    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""INSERT INTO students
            (name,subject,subjects_json,subject_minutes_json,total_study_minutes,email,phone,active,book_loaned,paper_ws,el,pi,v,day1,day2,day1_time,day2_time,owner_user_id)
            VALUES (?,?,?,?,?,?,?,1,?,?,?,?,?,?,?,?,?,?)""",
            (
                name,
                primary_subject,
                json.dumps(subjects_list),
                json.dumps(minutes_list),
                total_minutes,
                email,
                phone,
                int(bool(book_loaned)),
                int(bool(paper_ws)),
                int(bool(el)),
                int(bool(pi)),
                int(bool(v)),
                day1,
                day2,
                day1_time,
                day2_time,
                owner_user_id,
            ))
        student_id = c.lastrowid
        conn.commit()
    
    # Automatically generate QR code for the new student
    try:
        from modules import qr_generator
        qr_data = f"ID:{student_id}\nName:{name}"
        qr_generator.generate_qr(qr_data, f"student_{student_id}")
    except Exception as e:
        print(f"Warning: Failed to generate QR code for student {student_id}: {e}")
    
    return student_id



def update_student(sid, name, email, phone, subject="", book_loaned=0, paper_ws=0, el=0, pi=0, v=0, day1="", day2="", day1_time="", day2_time="", owner_user_id=1, subjects=None, subject_minutes=None):
    """Update an existing student's information with ownership check."""
    subjects_list, minutes_list, total_minutes = normalize_subject_entries(
        subjects if subjects is not None else [subject],
        subject_minutes if subject_minutes is not None else [30],
    )
    primary_subject = subjects_list[0]

    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""UPDATE students SET name=?,subject=?,subjects_json=?,subject_minutes_json=?,total_study_minutes=?,email=?,phone=?,book_loaned=?,paper_ws=?,el=?,pi=?,v=?,day1=?,day2=?,day1_time=?,day2_time=? WHERE id=? AND owner_user_id=?""",
                  (
                      name,
                      primary_subject,
                      json.dumps(subjects_list),
                      json.dumps(minutes_list),
                      total_minutes,
                      email,
                      phone,
                      int(bool(book_loaned)),
                      int(bool(paper_ws)),
                      int(bool(el)),
                      int(bool(pi)),
                      int(bool(v)),
                      day1,
                      day2,
                      day1_time,
                      day2_time,
                      sid,
                      owner_user_id,
                  ))
        conn.commit()


def delete_student(sid, owner_user_id=1):
    """Soft delete: mark student as inactive instead of hard delete with ownership check."""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("UPDATE students SET active=0 WHERE id=? AND owner_user_id=?", (sid, owner_user_id))
        conn.commit()


def permanent_delete_student(sid, owner_user_id=1):
    """Permanently delete student from database (hard delete) with ownership check."""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM students WHERE id=? AND owner_user_id=?", (sid, owner_user_id))
        conn.commit()


def get_deleted_students(owner_user_id=1):
    """Get all deleted/inactive students for a specific user."""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""
            SELECT s.id, s.name, s.subject, s.level, s.email, s.phone, '' AS legacy_contact, s.active, s.book_loaned, s.paper_ws,
                   s.math_goal, s.math_ws_per_week, s.reading_goal, s.reading_ws_per_week,
                   s.el, s.pi, s.v, s.day1, s.day1_time, s.day2, s.day2_time
            FROM students s
            WHERE s.active = 0 AND s.owner_user_id = ?
            ORDER BY s.name
        """, (owner_user_id,))
        return c.fetchall()


def reactivate_student(sid, owner_user_id=1):
    """Reactivate a deleted/inactive student with ownership check."""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("UPDATE students SET active=1 WHERE id=? AND owner_user_id=?", (sid, owner_user_id))
        conn.commit()


def import_csv(file_path, owner_user_id=1):
    """Import students from CSV with ownership assignment.
    
    Args:
        file_path: Path to CSV file
        owner_user_id: User ID to assign as owner of imported students (default: 1)
    """
    if not os.path.exists(file_path):
        return {"added": 0, "updated": 0, "deleted": 0}
    added=0
    updated=0
    deleted=0
    csv_names=set()  # Track names from CSV
    
    with sqlite3.connect(DB_PATH) as conn, open(file_path,newline="",encoding="utf-8-sig") as f:
        reader=csv.DictReader(f)
        
        # Debug: Log column headers
        first_row = True
        for row in reader:
            if first_row:
                print(f"CSV Columns: {list(row.keys())}")
                first_row = False
            
            name=row.get("name") or ""
            if not name.strip(): continue
            csv_names.add(name.lower().strip())  # Store lowercase name for matching
            
            email=row.get("email") or ""
            phone=row.get("phone") or ""
            subject=row.get("subject") or ""
            math_goal=row.get("math_goal") or ""
            # Map CSV column Math/WS to database column math_ws_per_week
            math_ws=safe_int(row.get("Math/WS") or row.get("math/ws") or "0", default=0)
            reading_goal=row.get("reading_goal") or ""
            # Map CSV column Reading/WS to database column reading_ws_per_week
            reading_ws=safe_int(row.get("Reading/WS") or row.get("reading/ws") or "0", default=0)
            print(f"Student: {name}, Math/WS: {math_ws}, Reading/WS: {reading_ws}")
            
            if subject.strip() not in {"S1", "S2"}:
                return {"error": "CSV import failed: subject must be S1 or S2 for every student."}
            
            # Check if student exists (owned by this user)
            student_record=conn.execute("SELECT id FROM students WHERE LOWER(TRIM(name))=LOWER(?) AND owner_user_id=?",(name.strip(), owner_user_id)).fetchone()
            
            if student_record:
                # UPDATE existing student - set all fields from CSV
                student_id = student_record[0]
                print(f"UPDATING student ID {student_id}: {name}")
                conn.execute("""UPDATE students SET name=?, subject=?, email=?, phone=?, math_goal=?, math_ws_per_week=?, reading_goal=?, reading_ws_per_week=?, active=1 WHERE id=? AND owner_user_id=?"""
                             ,(name,subject,email,phone,math_goal,math_ws,reading_goal,reading_ws,student_id,owner_user_id))
                updated+=1
            else:
                # INSERT new student with owner_user_id
                print(f"INSERTING new student: {name}")
                conn.execute("""INSERT INTO students(name,subject,email,phone,active,math_goal,math_ws_per_week,reading_goal,reading_ws_per_week,owner_user_id)
                                VALUES(?,?,?,?,1,?,?,?,?,?)""",(name,subject,email,phone,math_goal,math_ws,reading_goal,reading_ws,owner_user_id))
                added+=1
        
        # PERMANENTLY delete students not in CSV (owned by this user only)
        cursor=conn.cursor()
        cursor.execute("SELECT id, name FROM students WHERE owner_user_id=?", (owner_user_id,))
        db_students=cursor.fetchall()
        print(f"CSV names: {csv_names}")
        for student_id, student_name in db_students:
            student_name_lower = student_name.lower().strip()
            if student_name_lower not in csv_names:
                conn.execute("DELETE FROM students WHERE id=? AND owner_user_id=?", (student_id, owner_user_id))
                deleted+=1
                print(f"Permanently deleting: {student_name}")
        
        conn.commit()
    return {"added": added, "updated": updated, "deleted": deleted}

def export_csv(path, owner_user_id=1):
    """Export all active students to CSV with proper alignment of headers and data."""
    data=get_all_students(owner_user_id)
    # Headers must match the order of columns returned by get_all_students()
    # get_all_students returns: id, name, subject, level, email, phone, legacy_contact, active,
    # book_loaned, paper_ws, math_goal, math_ws_per_week, reading_goal, reading_ws_per_week,
    # el, pi, v, day1, day1_time, day2, day2_time
    headers=[
        "ID",
        "Student Name",
        "Subject",
        "Level",
        "Email",
        "Phone",
        "Active",
        "Book Loaned",
        "Paper Worksheets",
        "Math Goal",
        "Math Worksheets/Week",
        "Reading Goal",
        "Reading Worksheets/Week",
        "Early Learner",
        "Primary Instruction",
        "Virtual",
        "Day 1",
        "Day 1 Time",
        "Day 2",
        "Day 2 Time"
    ]
    with open(path,"w",newline="",encoding="utf-8") as f:
        writer=csv.writer(f)
        writer.writerow(headers)
        writer.writerows([list(row[:6]) + list(row[7:]) for row in data])


def find_duplicates_by_name(name, owner_user_id: int = 1):
    """Find all students with a given name (case-insensitive, whitespace-trimmed)."""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""
            SELECT id, name, email, phone, subject, day1, day1_time, day2, day2_time
            FROM students
            WHERE LOWER(TRIM(name)) = LOWER(TRIM(?))
              AND owner_user_id = ?
            ORDER BY id
        """, (name, owner_user_id))
        return c.fetchall()


def get_duplicate_names(owner_user_id: int = 1):
    """Get all student names that appear more than once in the student list."""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""
            SELECT LOWER(TRIM(name)) as name_key, COUNT(*) as count
            FROM students
            WHERE active = 1
              AND owner_user_id = ?
            GROUP BY LOWER(TRIM(name))
            HAVING COUNT(*) > 1
            ORDER BY count DESC, name_key
        """, (owner_user_id,))
        return c.fetchall()


def get_duplicate_summary(owner_user_id: int = 1):
    """Get a detailed summary of all duplicate names with their student information."""
    duplicates = get_duplicate_names(owner_user_id)
    summary = []
    
    for name_key, count in duplicates:
        # Find the original name (with correct casing) and get all students with this name
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute("""
                SELECT id, name, email, phone, subject, day1, day1_time, day2, day2_time, el, pi, v
                FROM students
                WHERE LOWER(TRIM(name)) = LOWER(TRIM(?))
                AND active = 1
                AND owner_user_id = ?
                ORDER BY id
            """, (name_key, owner_user_id))
            students = c.fetchall()
            
            if students:
                original_name = students[0][1]  # Get the actual name with correct casing
                summary.append({
                    'name': original_name,
                    'count': count,
                    'students': [
                        {
                            'id': s[0],
                            'name': s[1],
                            'email': s[2],
                            'phone': s[3],
                            'subject': s[4],
                            'day1': s[5],
                            'day1_time': s[6],
                            'day2': s[7],
                            'day2_time': s[8],
                            'el': s[9],
                            'pi': s[10],
                            'v': s[11]
                        }
                        for s in students
                    ]
                })
    
    return summary


def has_duplicate_names(owner_user_id: int = 1):
    """Check if there are any duplicate names in the active student list."""
    duplicates = get_duplicate_names(owner_user_id)
    return len(duplicates) > 0