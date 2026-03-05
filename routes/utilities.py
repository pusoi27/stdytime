"""
Utilities routes for KumoClock
- Student Report Card
- Student Evaluation  
- Award Ceremony Analysis
"""

from flask import Blueprint, render_template, request, jsonify, send_file, session
from datetime import datetime
import os
import sys
from pathlib import Path
import uuid
import json
import pandas as pd
import numpy as np
from werkzeug.utils import secure_filename
import re
import calendar

# Add parent directory to path for module imports
PARENT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PARENT_DIR / 'modules'))

from modules.database import get_db_connection
from modules.utils import format_hhmm
from modules.email_manager import get_email_manager
from modules import instructor_profile_manager
from modules.award_rules_engine import get_worksheets_per_day, normalize_level

# Temporary storage directory for report-card file data to avoid bloating session cookies
TEMP_REPORTCARD_DIR = Path('data') / 'tmp_reportcard'
TEMP_REPORTCARD_DIR.mkdir(parents=True, exist_ok=True)


def _get_report_card_token():
    """Return a stable per-session token; create if missing."""
    token = session.get('report_card_token')
    if not token:
        token = uuid.uuid4().hex
        session['report_card_token'] = token
        session.modified = True
    return token


def _save_subject_payload(token: str, subject: str, payload: dict):
    """Persist subject payload to disk (JSON) and keep only minimal metadata in session."""
    subject_key = subject.lower()
    token_dir = TEMP_REPORTCARD_DIR / token
    token_dir.mkdir(parents=True, exist_ok=True)
    file_path = token_dir / f"{subject_key}.json"
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False)

    # Store lightweight metadata in session (to keep cookie small)
    meta = session.get('report_card_meta', {})
    meta[subject_key] = {
        'subject': payload.get('subject', subject.title()),
        'filename': payload.get('filename'),
        'columns': payload.get('columns', []),
        'path': str(file_path)
    }
    session['report_card_meta'] = meta
    session.modified = True


def _load_subject_payload(token: str, subject_key: str):
    """Load subject payload from disk for this session token."""
    token_dir = TEMP_REPORTCARD_DIR / token
    file_path = token_dir / f"{subject_key}.json"
    if not file_path.exists():
        return None
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def register_utilities_routes(app):
    """Register all utilities routes"""

    @app.context_processor
    def inject_instructor_email():
        profile = instructor_profile_manager.get_instructor_profile()
        return {'instructor_email': profile.get('email') if profile else None}

    def _parse_report_dates(name: str):
        """Parse date range from filename.

        Rules:
        - Find month+year tokens like "Dec 2025"
        - Start date = 1st of first month
        - End date = today if second month is current; otherwise last day of second month
        - If only one month/year is present, use it for both start/end (end to end-of-month)
        """
        month_map = {
            'jan': 1, 'january': 1,
            'feb': 2, 'february': 2,
            'mar': 3, 'march': 3,
            'apr': 4, 'april': 4,
            'may': 5,
            'jun': 6, 'june': 6,
            'jul': 7, 'july': 7,
            'aug': 8, 'august': 8,
            'sep': 9, 'sept': 9, 'september': 9,
            'oct': 10, 'october': 10,
            'nov': 11, 'november': 11,
            'dec': 12, 'december': 12,
        }
        pattern = re.compile(r"(?i)\b(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+(\d{4})\b")
        clean_name = (name or '').replace('_', ' ').replace('-', ' ')
        matches = pattern.findall(clean_name)
        if not matches:
            return None
        my = []
        for mname, year in matches:
            mkey = mname.lower()
            if mkey == 'sept':
                mkey = 'sep'
            month = month_map.get(mkey)
            if month:
                my.append((int(year), month))
        if not my:
            return None
        start_year, start_month = my[0]
        start_dt = datetime(start_year, start_month, 1)
        end_year, end_month = my[1] if len(my) > 1 else my[0]
        now = datetime.now()
        if end_year == now.year and end_month == now.month:
            end_dt = now
        else:
            last_day = calendar.monthrange(end_year, end_month)[1]
            end_dt = datetime(end_year, end_month, last_day)
        return {
            'start_date': f"{start_dt.month}/{start_dt.day}/{start_dt.year}",
            'end_date': f"{end_dt.month}/{end_dt.day}/{end_dt.year}"
        }
    
    @app.route('/utilities')
    def utilities_index():
        """Main utilities page"""
        return render_template('utilities/index.html')
    
    # ==================== Student Report Card ====================
    @app.route('/utilities/report-card')
    def report_card_page():
        """Student Report Card page"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get all students for the dropdown
        cursor.execute('SELECT id, name FROM students ORDER BY name')
        students = [{'id': row[0], 'name': row[1]} for row in cursor.fetchall()]
        conn.close()
        
        return render_template('utilities/report_card.html', students=students)
    
    @app.route('/api/utilities/get-student-email-by-name', methods=['POST'])
    def api_get_student_email_by_name():
        """Get student email by matching first name from full name"""
        try:
            data = request.get_json()
            full_name = data.get('full_name', '').strip()
            
            if not full_name:
                return jsonify({'success': False, 'error': 'No name provided'}), 400
            
            # Extract first name (first word)
            first_name = full_name.split()[0].lower() if full_name else ''
            
            if not first_name:
                return jsonify({'success': False, 'error': 'Invalid name format'}), 400
            
            # Query database for students with matching first name
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, name, email, math_ws_per_week, reading_ws_per_week
                FROM students 
                WHERE LOWER(SUBSTR(name, 1, INSTR(name || ' ', ' ') - 1)) = ?
                ORDER BY name
            """, (first_name,))
            
            matches = cursor.fetchall()
            conn.close()
            
            if not matches:
                return jsonify({
                    'success': False,
                    'error': f'No student found with first name "{first_name.title()}"'
                })
            
            # If multiple matches, return the first one (or could return all for user to choose)
            student_id, student_name, student_email, student_math_ws_per_week, student_reading_ws_per_week = matches[0]
            
            return jsonify({
                'success': True,
                'student_id': student_id,
                'student_name': student_name,
                'email': student_email or '',
                'matches_count': len(matches),
                'math_ws_per_week': student_math_ws_per_week,
                'reading_ws_per_week': student_reading_ws_per_week
            })
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/utilities/report-card/<int:student_id>', methods=['GET'])
    def api_get_report_card(student_id):
        """Get student report card data"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Get student info including active status and subject
            cursor.execute('SELECT id, name, email, phone, active, subject FROM students WHERE id = ?', (student_id,))
            student = cursor.fetchone()
            
            if not student:
                conn.close()
                return jsonify({'error': 'Student not found'}), 404
            
            # Get attendance records (using correct table name 'sessions')
            cursor.execute('''
                SELECT DATE(start_time) as date, COUNT(*) as sessions, 
                       SUM(CASE WHEN end_time IS NOT NULL THEN 1 ELSE 0 END) as attended
                FROM sessions 
                WHERE student_id = ? 
                GROUP BY DATE(start_time)
                ORDER BY date DESC
                LIMIT 30
            ''', (student_id,))
            
            attendance = []
            for row in cursor.fetchall():
                attendance.append({
                    'date': row[0],
                    'sessions': row[1],
                    'attended': row[2] if row[2] else 0
                })
            
            conn.close()
            
            # Check if student is active
            is_active = student[4] == 1
            student_name = student[1]
            student_subject = student[5] or ''
            
            # Helper function to normalize names for matching
            def normalize_name_for_matching(name):
                """
                Extracts comparable parts from a name, handling abbreviations.
                Examples:
                - "Aahan Agarwal" -> ["aahan", "agarwal"]
                - "Aahan A." -> ["aahan", "a"]
                - "Kella St Luce" -> ["kella", "st", "luce"]
                - "Kella St.L." -> ["kella", "st", "l"]
                """
                if not name:
                    return []
                # Remove extra punctuation and split
                name = name.strip().lower()
                # Split by spaces and remove periods
                parts = []
                for part in name.split():
                    # Remove periods and keep the core word/letter
                    clean_part = part.replace('.', '')
                    if clean_part:
                        parts.append(clean_part)
                return parts
            
            def names_match(db_name, file_name):
                """
                Compare two names with flexible matching:
                - Must have matching first name
                - Additional name parts should be compatible (exact or abbreviation)
                """
                db_parts = normalize_name_for_matching(db_name)
                file_parts = normalize_name_for_matching(file_name)
                
                if not db_parts or not file_parts:
                    return False
                
                # First names MUST match exactly
                if db_parts[0] != file_parts[0]:
                    return False
                
                # If either name has only first name, that's a match
                if len(db_parts) == 1 or len(file_parts) == 1:
                    return True
                
                # For multi-part names, check remaining parts for compatibility
                # Compare parts position by position
                for i in range(1, min(len(db_parts), len(file_parts))):
                    db_part = db_parts[i]
                    file_part = file_parts[i]
                    
                    # Parts match if:
                    # 1. Exact match: "agarwal" == "agarwal"
                    # 2. One is abbrev of other: "agarwal".startswith("a") or "a".startswith("agarwal")
                    if db_part != file_part and not (db_part.startswith(file_part) or file_part.startswith(db_part)):
                        # This part doesn't match and isn't compatible
                        return False
                
                # All checked parts matched
                return True
            
            # Get subject data from temp storage (disk) if student is active
            subject_data = {'math': None, 'reading': None}
            if is_active and session.get('report_card_token'):
                token = session['report_card_token']
                for subject_key in ['math', 'reading']:
                    payload = _load_subject_payload(token, subject_key)
                    if not payload:
                        continue
                    for record in payload.get('data', []):
                        record_name = str(record.get('name', '') or record.get('Name', '') or record.get('Student Name', ''))
                        if names_match(student_name, record_name):
                            subj = str(record.get('subject', '') or record.get('Subject', '')).lower()
                            highest_ws = record.get('Highest WS Completed') or record.get('Highest WS Completed This Month') or '-'
                            num_ws = record.get('# of WS') or record.get('Number of Worksheets') or '-'
                            study_days = record.get('# of Study Days') or record.get('Study Days') or '-'
                            cum_study_time = record.get('Cum. Study Time') or record.get('Cumulative Study Time') or '-'
                            entry = {
                                'highest_ws': highest_ws,
                                'num_ws': num_ws,
                                'study_days': study_days,
                                'cum_study_time': cum_study_time
                            }
                            if 'math' in subj:
                                subject_data['math'] = entry
                            elif 'reading' in subj:
                                subject_data['reading'] = entry
            
            return jsonify({
                'student': {
                    'id': student[0],
                    'name': student[1],
                    'email': student[2],
                    'phone': student[3],
                    'active': is_active,
                    'subject': student_subject
                },
                'attendance': attendance,
                'subject_data': subject_data
            })
        
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/utilities/report-card/export/<int:student_id>', methods=['GET'])
    def api_export_report_card(student_id):
        """Export report card as PDF/CSV"""
        try:
            # This would generate a PDF report
            # For now, return a basic response
            return jsonify({'message': 'Report card export functionality coming soon'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/utilities/report-card/generate-report', methods=['GET'])
    def api_generate_unified_report():
        """Return structured rows for Math/Reading with inactive filtered out"""
        try:
            def get_field(record, candidate_keys):
                """Get first matching key (case-insensitive)."""
                lower_map = {str(k).lower(): v for k, v in record.items()}
                for key in candidate_keys:
                    if key.lower() in lower_map:
                        return lower_map[key.lower()]
                return None

            def zero_if_missing(val):
                """Return 0 when value is None/empty, else original."""
                if val is None:
                    return 0
                if isinstance(val, str) and val.strip() == '':
                    return 0
                return val

            structured_rows = []

            token = session.get('report_card_token')
            meta = session.get('report_card_meta', {}) if token else {}

            for subject_key in ['math', 'reading']:
                payload = _load_subject_payload(token, subject_key) if token else None
                if not payload:
                    continue

                subject_label = (payload.get('subject') or subject_key.title()).strip()
                report_dates = None
                try:
                    report_dates = (payload.get('parse_meta') or {}).get('report_dates')
                    if not report_dates:
                        report_dates = _parse_report_dates(payload.get('filename', ''))
                except Exception:
                    report_dates = _parse_report_dates(payload.get('filename', ''))
                filename = payload.get('filename', subject_label)

                for record in payload.get('data', []):
                    # Determine status and skip inactive rows
                    status = get_field(record, ['Current Subject Status', 'Status'])
                    status_str = str(status).strip() if status is not None else ''
                    if status_str.lower() == 'inactive':
                        continue

                    structured_rows.append({
                        'subject': subject_label or filename,
                        'full_name': get_field(record, ['Full Name', 'Student Name', 'Name']) or '',
                        'highest_ws_completed': get_field(record, ['Highest WS Completed', 'Highest WS Completed This Month']) or '',
                        'num_ws': zero_if_missing(get_field(record, ['# of WS', 'Number of Worksheets'])),
                        'study_days': zero_if_missing(get_field(record, ['# of Study Days', 'Study Days'])),
                        'cum_study_time': zero_if_missing(get_field(record, ['Cum. Study Time', 'Cumulative Study Time'])),
                        'current_subject_status': status_str or '',
                        'start_date': (report_dates or {}).get('start_date') if report_dates else None,
                        'end_date': (report_dates or {}).get('end_date') if report_dates else None
                    })

            return jsonify({'students': structured_rows})

        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/utilities/report-card/load-file', methods=['POST'])
    def api_load_subject_file():
        """Load Math or Reading file and parse data - subject extracted from filename"""
        try:
            if 'file' not in request.files:
                return jsonify({'error': 'No file provided'}), 400
            
            file = request.files['file']
            
            if file.filename == '':
                return jsonify({'error': 'No file selected'}), 400
            
            filename = file.filename
            file_ext = os.path.splitext(filename)[1].lower()
            
            # Extract subject from filename
            if 'math' in filename.lower():
                subject = 'Math'
            elif 'reading' in filename.lower():
                subject = 'Reading'
            else:
                return jsonify({'error': 'Filename must contain "Math" or "Reading"'}), 400

            # Extract report date range from filename (e.g., "..._Dec 2025_Jan 2026_01072026.csv")
            
            # Parse file
            try:
                df = None
                used_encoding = None
                used_delimiter = None
                parse_attempts = []
                
                if file_ext in ['.xlsx', '.xls']:
                    df = pd.read_excel(file)
                    used_encoding = 'excel'
                    used_delimiter = 'excel'
                elif file_ext == '.csv':
                    # Try reading CSV with multiple encodings and delimiters, skipping bad lines
                    encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'windows-1252']
                    delimiters = [None, ',', ';', '\t', '|']  # None lets pandas sniff
                    for enc in encodings:
                        for sep in delimiters:
                            try:
                                file.seek(0)
                                df = pd.read_csv(
                                    file,
                                    encoding=enc,
                                    sep=sep,
                                    engine='python',
                                    on_bad_lines='skip'
                                )
                                used_encoding = enc
                                used_delimiter = sep or 'auto-detect'
                                break
                            except Exception as err:
                                parse_attempts.append(f"encoding={enc}, sep={sep or 'auto'} -> {err}")
                        if df is not None:
                            break
                else:
                    return jsonify({'success': False, 'error': 'Use Excel (.xlsx, .xls) or CSV file'}), 400
                
                if df is None:
                    return jsonify({
                        'success': False,
                        'error': 'Failed to parse file',
                        'attempts': parse_attempts
                    }), 400
                
                # Ensure Subject column exists with the detected subject for all rows
                try:
                    df['Subject'] = subject
                except Exception:
                    # If for some reason assignment fails, fall back to copy
                    df = df.copy()
                    df['Subject'] = subject

                # Replace NaN/NaT/inf/-inf with None so JSON returned is valid
                # Must be done BEFORE to_dict() to ensure clean JSON serialization
                df = df.replace([np.inf, -np.inf], np.nan)
                df = df.fillna('')  # Replace all NaN with empty string for JSON safety
                
                # Convert dataframe to list of dicts for response
                file_data = df.to_dict('records')

                # Persist to disk (per-session token) to avoid cookie bloat
                token = _get_report_card_token()
                payload = {
                    'filename': filename,
                    'subject': subject,
                    'data': file_data,
                    'columns': list(df.columns),
                    'parse_meta': {
                        'encoding': used_encoding,
                        'delimiter': used_delimiter,
                        'report_dates': _parse_report_dates(filename)
                    }
                }
                _save_subject_payload(token, subject, payload)

                # Clean any legacy in-session blobs to keep cookie minimal
                session.pop(f'{subject.lower()}_file_data', None)
                session.pop('loaded_subject_data', None)

                return jsonify({
                    'success': True,
                    'subject': subject,
                    'filename': filename,
                    'records': len(df),
                    'columns': list(df.columns),
                    'data': file_data,
                    'parse_meta': {
                        'encoding': used_encoding,
                        'delimiter': used_delimiter,
                        'attempts': parse_attempts[-5:],  # show a few failures for debugging
                        'report_dates': _parse_report_dates(filename)
                    }
                })
                
            except Exception as parse_error:
                import traceback
                error_trace = traceback.format_exc()
                return jsonify({'success': False, 'error': f'Parse error: {str(parse_error)}', 'trace': error_trace}), 400
        
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/utilities/report-card/send-email', methods=['POST'])
    def api_send_report_email():
        """Send student report card via email"""
        try:
            data = request.get_json()
            
            if not data:
                return jsonify({'success': False, 'error': 'No data provided'}), 400
            
            student_name = data.get('student_name')
            student_id = data.get('student_id')  # Get student ID to fetch ws_per_week values
            recipient_email = data.get('recipient_email')
            instructor_email_from_client = data.get('instructor_email')  # null if checkbox unchecked
            report_data = data.get('report_data', [])
            
            if not student_name or not recipient_email:
                return jsonify({'success': False, 'error': 'Student name and recipient email are required'}), 400
            
            if not report_data or len(report_data) == 0:
                return jsonify({'success': False, 'error': 'No report data available'}), 400
            
            # Load instructor profile to get center name and email
            profile = instructor_profile_manager.get_instructor_profile()
            center_location = profile.get('center_location', 'KumoClock Academic Management System') if profile else 'KumoClock Academic Management System'
            
            # Check if user wants to send to instructor (based on checkbox)
            send_to_instructor = instructor_email_from_client is not None
            
            # Load instructor email from profile if needed
            instructor_email = None
            if send_to_instructor:
                if profile:
                    instructor_email = profile.get('email')
            
            print(f"[send-email] Send to instructor: {send_to_instructor}, Instructor email: {instructor_email}, Center: {center_location}")

            # Get email manager instance
            email_manager = get_email_manager()
            
            # Get student's ws_per_week values from database if student_id provided
            def _as_positive_number(val):
                """Return float value if > 0, else None (handles str/int/float)."""
                if val is None:
                    return None
                try:
                    num = float(val)
                    return num if num > 0 else None
                except (TypeError, ValueError):
                    return None

            student_math_ws_per_week = None
            student_reading_ws_per_week = None
            if student_id:
                try:
                    from modules.student_manager import get_student
                    student = get_student(student_id)
                    if student:
                        # Index 10 is math_ws_per_week, index 12 is reading_ws_per_week (from get_student)
                        student_math_ws_per_week = _as_positive_number(student[10] if len(student) > 10 else None)
                        student_reading_ws_per_week = _as_positive_number(student[12] if len(student) > 12 else None)
                        print(f"[send-email] Student {student_id} has math_ws_per_week={student_math_ws_per_week}, reading_ws_per_week={student_reading_ws_per_week}")
                except Exception as e:
                    print(f"[send-email] Error loading student data: {e}")
            
            # Helpers for target worksheet calculation
            def _parse_date(date_str: str):
                if not date_str:
                    return None
                candidates = ["%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d", "%m-%d-%Y", "%m-%d-%y"]
                s = str(date_str).strip()
                for fmt in candidates:
                    try:
                        return datetime.strptime(s, fmt).date()
                    except Exception:
                        continue
                return None

            def _business_days(start_date, end_date):
                if not start_date or not end_date:
                    return None
                if end_date < start_date:
                    return None
                total_days = (end_date - start_date).days + 1
                weeks = total_days // 7
                extra = total_days % 7
                business = weeks * 5
                start_weekday = start_date.weekday()  # Monday=0
                for i in range(extra):
                    if (start_weekday + i) % 7 < 5:
                        business += 1
                return business

            def _get_bg_color(actual, target):
                """Return bgcolor for email tables: green >= 80%, yellow 50-80%, red < 50%"""
                if actual is None or target is None or target == 0 or target == 'N/A':
                    return ''
                try:
                    act_val = float(actual) if isinstance(actual, (int, float)) else float(actual)
                    tgt_val = float(target) if isinstance(target, (int, float)) else float(target)
                    if tgt_val == 0:
                        return ''
                    pct = (act_val / tgt_val) * 100
                    if pct >= 80:
                        return '#d1e7dd'  # Green
                    elif pct >= 50:
                        return '#fff3cd'  # Yellow
                    else:
                        return '#f8d7da'  # Red
                except (ValueError, TypeError):
                    return ''

            # Format report data for email (combine all subjects)
            combined_report = {
                'student_name': student_name,
                'subjects': []
            }

            def zero_if_missing(val):
                if val is None:
                    return 0
                if isinstance(val, str) and val.strip() == '':
                    return 0
                return val

            for record in report_data:
                subject_name = record.get('subject', 'N/A')
                highest_ws = record.get('highest_ws_completed')
                start_date_parsed = _parse_date(record.get('start_date'))
                end_date_parsed = _parse_date(record.get('end_date'))
                business_days = _business_days(start_date_parsed, end_date_parsed)

                # Calculate target worksheets
                target_ws = None
                
                # First, try to use student's ws_per_week values from database
                if business_days is not None:
                    weeks = business_days / 5.0  # 5 business days per week
                    
                    # Determine which ws_per_week to use based on subject
                    math_ws = _as_positive_number(student_math_ws_per_week)
                    reading_ws = _as_positive_number(student_reading_ws_per_week)

                    if subject_name and 'math' in subject_name.lower() and math_ws:
                        target_ws = int(weeks * math_ws)
                        print(f"[send-email] Using student math_ws_per_week: {weeks} weeks * {math_ws} = {target_ws}")
                    elif subject_name and 'reading' in subject_name.lower() and reading_ws:
                        target_ws = int(weeks * reading_ws)
                        print(f"[send-email] Using student reading_ws_per_week: {weeks} weeks * {reading_ws} = {target_ws}")
                    elif math_ws:
                        # Default to math ws/week if subject unclear but value exists
                        target_ws = int(weeks * math_ws)
                        print(f"[send-email] Using student math_ws_per_week (default): {weeks} weeks * {math_ws} = {target_ws}")
                    else:
                        # Fall back to default calculation based on worksheet level
                        subj_key = subject_name.lower() if isinstance(subject_name, str) else None
                        worksheets_per_day = get_worksheets_per_day(normalize_level(highest_ws), subject=subj_key)
                        if worksheets_per_day is not None:
                            target_ws = int(business_days * worksheets_per_day)  # Round down to integer
                            print(f"[send-email] Using default calculation: {business_days} days * {worksheets_per_day} = {target_ws}")

                combined_report['subjects'].append({
                    'subject': subject_name,
                    'target_ws': target_ws if target_ws is not None else 'N/A',
                    'num_ws': zero_if_missing(record.get('num_ws', 'N/A')),
                    'study_period': business_days if business_days is not None else 'N/A',
                    'study_days': zero_if_missing(record.get('study_days', 'N/A')),
                    'cum_study_time': zero_if_missing(record.get('cum_study_time', 'N/A')),
                    'current_subject_status': record.get('current_subject_status', 'N/A'),
                    'start_date': record.get('start_date'),
                    'end_date': record.get('end_date')
                })
            
            # Create email subject and body
            subject = f"Student Report Card - {student_name}"
            
            # Plain text body
            body = f"""
Dear Parent/Guardian,

Please find below the report card for {student_name}.

*** DO NOT REPLY TO THIS EMAIL ***

"""
            for subj in combined_report['subjects']:
                date_line = ""
                if subj.get('start_date') or subj.get('end_date'):
                    date_line = f"Date Range: {subj.get('start_date') or 'N/A'} to {subj.get('end_date') or 'N/A'}\n"
                body += f"""
SUBJECT: {subj['subject']}
-------------------
{date_line}Target # Worksheets: {subj.get('target_ws', 'N/A')}
Number Of Worksheets Completed: {subj['num_ws']}
Study Period: {subj['study_period']}
Study Days: {subj['study_days']}
Cumulative Study Time: {subj['cum_study_time']}
Current Subject Status: {subj['current_subject_status']}

"""
            
            body += f"""
Best regards,
{center_location}
This is an automated message. Please do not reply.
"""
            
            # HTML body
            html_body = f"""
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .header {{ background-color: #0d6efd; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; }}
        .subject-section {{ margin-bottom: 30px; padding: 15px; background-color: #f8f9fa; border-left: 4px solid #0d6efd; }}
        .report-table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
        .report-table th, .report-table td {{ 
            border: 1px solid #ddd; padding: 12px; text-align: left; 
        }}
        .report-table th {{ background-color: #e9ecef; font-weight: bold; width: 50%; }}
        .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; 
                   color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="header">
        <h2>🎓 Student Report Card</h2>
        <p>{center_location}</p>
    </div>
    <div class="content">
        <p>Dear Parent/Guardian,</p>
        <p>Please find below the report card for <strong>{student_name}</strong>.</p>
        <div style="padding:10px; background:#fff3cd; border:1px solid #ffeeba; border-radius:6px; color:#856404; margin-bottom:15px;">
            <strong>Do not reply:</strong> This mailbox is not monitored.
        </div>
"""
            
            for subj in combined_report['subjects']:
                date_line = ""
                if subj.get('start_date') or subj.get('end_date'):
                    date_line = f"<tr><th>Report Date Range</th><td>{subj.get('start_date') or 'N/A'} to {subj.get('end_date') or 'N/A'}</td></tr>"
                
                # Calculate color styling for email-safe rendering
                num_ws = subj.get('num_ws')
                target_ws = subj.get('target_ws')
                ws_bgcolor = _get_bg_color(num_ws, target_ws)
                ws_row_attr = f' bgcolor="{ws_bgcolor}"' if ws_bgcolor else ''
                
                study_days = subj.get('study_days')
                study_period = subj.get('study_period')
                sd_bgcolor = _get_bg_color(study_days, study_period)
                sd_row_attr = f' bgcolor="{sd_bgcolor}"' if sd_bgcolor else ''
                
                html_body += f"""
        <div class="subject-section">
            <h3 style="color: #0d6efd; margin-top: 0;">Subject: {subj['subject']}</h3>
            <table class="report-table">
                {date_line}
                <tr>
                    <th>Target # Worksheets</th>
                    <td>{target_ws}</td>
                </tr>
                <tr{ws_row_attr}>
                    <th>Number Of Worksheets Completed</th>
                    <td>{num_ws}</td>
                </tr>
                <tr>
                    <th>Study Period</th>
                    <td>{study_period}</td>
                </tr>
                <tr{sd_row_attr}>
                    <th>Study Days</th>
                    <td>{study_days}</td>
                </tr>
                <tr>
                    <th>Cumulative Study Time</th>
                    <td>{subj['cum_study_time']}</td>
                </tr>
                <tr>
                    <th>Current Subject Status</th>
                    <td>{subj['current_subject_status']}</td>
                </tr>
            </table>
        </div>
"""
            
            html_body += f"""
        <div class="footer">
            <p>This is an automated message from {center_location}.</p>
            <p>For any questions, please contact your institution.</p>
        </div>
    </div>
</body>
</html>
"""
            
            # Send emails based on checkbox state
            sent_count = 0
            email_recipients = []
            errors = []

            # Email 1: Always send to primary recipient
            print(f"[send-email] Sending to primary recipient: {recipient_email}")
            result = email_manager.send_email(
                recipient_email=recipient_email,
                subject=subject,
                body=body,
                html_body=html_body
            )
            if result.get('success', False):
                sent_count += 1
                email_recipients.append(recipient_email)
                print(f"[send-email] Success: sent to {recipient_email}")
            else:
                errors.append(f"Failed to send to {recipient_email}: {result.get('error')}")
                print(f"[send-email] Failed to send to {recipient_email}: {result.get('error')}")

            # Email 2: Send to instructor ONLY if checkbox is checked
            if send_to_instructor:
                if not instructor_email or not instructor_email.strip():
                    errors.append("Instructor email is not configured in the profile")
                    print(f"[send-email] Skipping instructor email: not configured")
                else:
                    instructor_email_clean = instructor_email.strip()
                    print(f"[send-email] Sending to instructor: {instructor_email_clean}")
                    result_instructor = email_manager.send_email(
                        recipient_email=instructor_email_clean,
                        subject=subject,
                        body=body,
                        html_body=html_body
                    )
                    if result_instructor.get('success', False):
                        email_recipients.append(instructor_email_clean)
                        sent_count += 1
                        print(f"[send-email] Success: sent to instructor {instructor_email_clean}")
                    else:
                        errors.append(f"Failed to send to instructor {instructor_email_clean}: {result_instructor.get('error')}")
                        print(f"[send-email] Failed to send to instructor: {result_instructor.get('error')}")
            else:
                print(f"[send-email] Skipping instructor email: checkbox not checked")

            # Return combined result
            if sent_count > 0:
                message = f'Report card sent to {sent_count} recipient(s): {", ".join(email_recipients)}'
                if errors:
                    message += f'. Errors: {"; ".join(errors)}'
                return jsonify({
                    'success': True,
                    'message': message,
                    'recipients': email_recipients,
                    'errors': errors if errors else None
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Failed to send email to any recipient',
                    'details': errors
                })
            
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            return jsonify({
                'success': False,
                'error': f'Error sending email: {str(e)}',
                'trace': error_trace
            }), 500
    
    
    # ==================== Student Evaluation ====================
    @app.route('/utilities/evaluation')
    def evaluation_page():
        """Student Evaluation page"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get all students for the dropdown
        cursor.execute('SELECT id, name FROM students ORDER BY name')
        students = [{'id': row[0], 'name': row[1]} for row in cursor.fetchall()]
        conn.close()
        
        return render_template('utilities/evaluation.html', students=students)
    
    @app.route('/api/utilities/evaluation/<int:student_id>', methods=['GET'])
    def api_get_evaluation(student_id):
        """Get student evaluation data"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Get student info
            cursor.execute('SELECT id, name FROM students WHERE id = ?', (student_id,))
            student = cursor.fetchone()
            
            if not student:
                conn.close()
                return jsonify({'error': 'Student not found'}), 404
            
            # Get performance metrics
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_sessions,
                    SUM(CASE WHEN checked_out = 1 THEN 1 ELSE 0 END) as attended,
                    COUNT(DISTINCT DATE(session_start)) as days_attended
                FROM session_log 
                WHERE student_id = ?
            ''', (student_id,))
            
            metrics = cursor.fetchone()
            
            conn.close()
            
            attendance_rate = 0
            if metrics[0] > 0:
                attendance_rate = round((metrics[1] or 0) / metrics[0] * 100, 2)
            
            return jsonify({
                'student': {
                    'id': student[0],
                    'name': student[1]
                },
                'metrics': {
                    'total_sessions': metrics[0],
                    'attended': metrics[1] or 0,
                    'days_attended': metrics[2],
                    'attendance_rate': attendance_rate
                }
            })
        
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    
    # ==================== Award Ceremony ====================
    @app.route('/utilities/award-ceremony')
    def award_ceremony_page():
        """Award Ceremony page"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get all students
        cursor.execute('SELECT id, name FROM students ORDER BY name')
        students = [{'id': row[0], 'name': row[1]} for row in cursor.fetchall()]
        
        conn.close()
        
        return render_template('utilities/award_ceremony.html', students=students)
    
    @app.route('/api/utilities/award-ceremony/analyze', methods=['POST'])
    def api_analyze_awards():
        """Analyze and determine awards for students"""
        try:
            data = request.get_json(silent=True) or {}
            criteria = data.get('criteria', {})
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Get all students with their metrics
            cursor.execute('''
                SELECT 
                    s.id,
                    s.name,
                    COUNT(*) as total_sessions,
                    SUM(CASE WHEN checked_out = 1 THEN 1 ELSE 0 END) as attended,
                    COUNT(DISTINCT DATE(session_log.session_start)) as days_attended
                FROM students s
                LEFT JOIN session_log ON s.id = session_log.student_id
                GROUP BY s.id, s.name
                ORDER BY s.name
            ''')
            
            students = cursor.fetchall()
            conn.close()
            
            awards_list = []
            
            # Basic award criteria (customizable)
            for student in students:
                student_id, name, total_sessions, attended, days_attended = student
                attended = attended or 0
                days_attended = days_attended or 0
                
                awards = []
                
                # Perfect Attendance
                if total_sessions > 0 and attended == total_sessions:
                    awards.append('Perfect Attendance')
                
                # High Attendance (95%+)
                if total_sessions > 0 and (attended / total_sessions * 100) >= 95:
                    awards.append('High Attendance')
                
                # Regular Participant (10+ days)
                if days_attended >= 10:
                    awards.append('Regular Participant')
                
                # Dedicated Student (20+ sessions)
                if total_sessions >= 20:
                    awards.append('Dedicated Student')
                
                awards_list.append({
                    'id': student_id,
                    'name': name,
                    'metrics': {
                        'total_sessions': total_sessions,
                        'attended': attended,
                        'days_attended': days_attended,
                        'attendance_rate': round((attended / total_sessions * 100) if total_sessions > 0 else 0, 2)
                    },
                    'awards': awards
                })
            
            return jsonify({'awards': awards_list})
        
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/utilities/award-ceremony/export', methods=['POST'])
    def api_export_awards():
        """Export award ceremony results"""
        try:
            data = request.get_json(silent=True) or {}
            awards = data.get('awards', [])
            
            # Generate CSV content
            csv_content = "StudentID,Name,Attendance Rate,Awards\n"
            for award in awards:
                attendance_rate = award['metrics']['attendance_rate']
                award_list = '; '.join(award['awards']) if award['awards'] else 'No Awards'
                csv_content += f"{award['id']},{award['name']},{attendance_rate}%,\"{award_list}\"\n"
            
            return jsonify({
                'success': True,
                'message': 'Awards exported successfully',
                'csv': csv_content
            })
        
        except Exception as e:
            return jsonify({'error': str(e)}), 500    
    # ==================== Diploma Generation ====================
    @app.route('/utilities/diploma-generator')
    def diploma_generator_page():
        """Diploma/Certificate generation page"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get all students for the dropdown
        cursor.execute('SELECT id, name, subject, level FROM students ORDER BY name')
        students = [
            {
                'id': row[0],
                'name': row[1],
                'subject': row[2],
                'level': row[3]
            }
            for row in cursor.fetchall()
        ]
        conn.close()
        
        return render_template('utilities/diploma_generator.html', students=students)
    
    @app.route('/api/utilities/diploma-generator/generate', methods=['POST'])
    def api_generate_diplomas():
        """Generate diplomas for selected students"""
        try:
            from modules.diploma_generator import generate_diplomas, convert_diplomas_to_pdf
            
            data = request.get_json(silent=True) or {}
            student_names = data.get('students', [])
            diploma_type = data.get('diploma_type', 'Certificate')
            include_pdf = data.get('include_pdf', False)
            
            if not student_names:
                return jsonify({'error': 'No students selected'}), 400
            
            # Get the template and output directories
            template_dir = str(Path(__file__).parents[1] / 'data')
            output_docx = str(Path(__file__).parents[1] / 'exports' / 'diplomas_docx')
            output_pdf = str(Path(__file__).parents[1] / 'exports' / 'diplomas_pdf')
            
            # Create a temporary CSV with selected students
            import tempfile
            import csv
            
            temp_csv = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
            csv_writer = csv.writer(temp_csv)
            csv_writer.writerow(['Full Name', 'Diploma', 'Subject', 'NormalizedLevel'])
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            for name in student_names:
                cursor.execute(
                    'SELECT name, subject, level FROM students WHERE name = ?',
                    (name,)
                )
                row = cursor.fetchone()
                if row:
                    csv_writer.writerow([row[0], diploma_type, row[1], row[2]])
            
            conn.close()
            temp_csv.close()
            
            # Generate diplomas
            diplomas = generate_diplomas(
                temp_csv.name,
                template_dir,
                output_docx,
                student_names
            )
            
            result = {
                'success': True,
                'generated': len(diplomas),
                'diplomas': diplomas,
                'output_dir': output_docx
            }
            
            # Convert to PDF if requested
            if include_pdf and len(diplomas) > 0:
                pdf_result = convert_diplomas_to_pdf(diplomas, output_pdf)
                result['pdf_generated'] = pdf_result['success_count']
                result['pdf_failed'] = pdf_result['failed']
                result['pdf_dir'] = pdf_result['output_dir']
            
            # Clean up temp file
            os.unlink(temp_csv.name)
            
            return jsonify(result)
        
        except ImportError as e:
            return jsonify({
                'error': f'Required module not found: {str(e)}',
                'message': 'Install python-docx and docx2pdf: pip install python-docx docx2pdf'
            }), 500
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/utilities/diploma-generator/templates', methods=['GET'])
    def api_get_diploma_templates():
        """Get available diploma templates"""
        try:
            template_dir = Path(__file__).parents[1] / 'data'
            templates = []
            
            template_files = {
                'Award': 'Certificate of Award.docx',
                'Certificate': 'Certificate of Recognition.docx',
                'Welcome': 'Certificate of Welcome.docx'
            }
            
            for name, filename in template_files.items():
                path = template_dir / filename
                templates.append({
                    'type': name,
                    'filename': filename,
                    'exists': path.exists()
                })
            
            return jsonify({'templates': templates})
        
        except Exception as e:
            return jsonify({'error': str(e)}), 500