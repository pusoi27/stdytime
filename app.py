# KumoClock v2.3.12 - Main Flask Application (Refactored)
# ================================================================
"""
KumoClock: Student class management system with dashboard, QR codes, and PDF label generation.
Features: Student management, session tracking, QR generation, Avery 8160 PDF output, assistant duty tracking.
"""

from flask import Flask, render_template, request, send_from_directory, jsonify
from werkzeug.utils import secure_filename
from datetime import datetime
import sqlite3
import os
import shutil
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from modules.database import init_db, DB_PATH
from modules import student_manager, timer_manager, qr_generator, assistant_manager, reports
from modules.utils import format_hhmm

# ================================================================
#  Flask setup
# ================================================================
app = Flask(__name__)
app.secret_key = "kumoclock_secret_key"

# Initialize / verify sqlite DB
init_db()

# ================================================================
#  Request Profiling - Track reads and writes
# ================================================================
class RequestProfiler:
    """Track HTTP read (GET) and write (POST/PUT/DELETE/PATCH) operations."""
    def __init__(self):
        self.total_reads = 0
        self.total_writes = 0
        self.endpoint_stats = {}
        self.log_file = os.path.join(os.getcwd(), 'request_profile.log')
    
    def log_request(self, method, endpoint, status_code):
        """Log a request and update statistics."""
        is_write = method in ('POST', 'PUT', 'DELETE', 'PATCH')
        
        if is_write:
            self.total_writes += 1
        else:
            self.total_reads += 1
        
        # Track by endpoint
        key = f"{method} {endpoint}"
        if key not in self.endpoint_stats:
            self.endpoint_stats[key] = {'count': 0, 'statuses': []}
        self.endpoint_stats[key]['count'] += 1
        if status_code not in self.endpoint_stats[key]['statuses']:
            self.endpoint_stats[key]['statuses'].append(status_code)
        
        # Console output (compact format)
        req_type = "WRITE" if is_write else "READ"
        print(f"[{req_type}] {method:6} {endpoint:40} {status_code}")
        
        # Log to file
        self._write_log(f"[{req_type}] {method:6} {endpoint:40} {status_code}")
    
    def _write_log(self, message):
        """Append to log file."""
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {message}\n")
        except Exception:
            pass
    
    def print_summary(self):
        """Print summary of requests."""
        total = self.total_reads + self.total_writes
        if total == 0:
            return
        
        summary = (
            f"\n{'='*80}\n"
            f"REQUEST PROFILE SUMMARY\n"
            f"{'='*80}\n"
            f"📖 Total READs  (GET):                 {self.total_reads}\n"
            f"✏️  Total WRITEs (POST/PUT/DELETE):   {self.total_writes}\n"
            f"📊 Total Requests:                     {total}\n"
            f"{'='*80}\n"
        )
        print(summary)
        self._write_log(summary)
        
        # Endpoint breakdown
        if self.endpoint_stats:
            print("\nEndpoint Breakdown:")
            for endpoint, stats in sorted(self.endpoint_stats.items(), key=lambda x: x[1]['count'], reverse=True):
                print(f"  {endpoint:50} {stats['count']:3} requests (Status: {', '.join(map(str, stats['statuses']))})")

profiler = RequestProfiler()

@app.before_request
def before_request_profiler():
    """Capture request start time."""
    from flask import g
    g.start_time = datetime.now()

@app.after_request
def after_request_profiler(response):
    """Log request after it completes."""
    from flask import g
    endpoint = request.path
    profiler.log_request(request.method, endpoint, response.status_code)
    return response

# Prevent client/proxies from caching API responses
@app.after_request
def add_no_cache_headers(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

# Folders for CSV IO
UPLOAD_FOLDER = "uploads"
EXPORT_FOLDER = "exports"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(EXPORT_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# ================================================================
#  Request Profiling - Track reads and writes
# ================================================================
@app.context_processor
def inject_now():
    """Inject current date/time into all templates."""
    now = datetime.now()
    return dict(
        date_str=now.strftime("%A, %B %d, %Y"),
        time_str=now.strftime("%I:%M:%S %p"),
    )


@app.context_processor
def inject_dynamic_lists():
    """Make the in-memory active and checked lists available to templates."""
    from routes.api import active_students_cache, checked_out_cache
    return dict(active_list=active_students_cache, checked_list=checked_out_cache)


@app.context_processor
def inject_app_version():
    """Inject app version from VERSION file into all templates."""
    return dict(app_version=_ensure_version_up_to_date())


def _bump_patch_version(version):
    """Bump version with rollover: x.x.(x+1) where each segment goes 0-99.
    Example: 06.07.59 → 06.07.60, 06.07.99 → 06.08.00, 06.99.99 → 07.00.00
    """
    parts = version.split('.')
    if len(parts) < 3:
        return version
    
    try:
        major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
        width = [len(parts[0]), len(parts[1]), len(parts[2])]
        
        # Increment patch
        patch += 1
        
        # Rollover logic
        if patch > 99:
            patch = 0
            minor += 1
            if minor > 99:
                minor = 0
                major += 1
        
        return f"{str(major).zfill(width[0])}.{str(minor).zfill(width[1])}.{str(patch).zfill(width[2])}"
    except (ValueError, IndexError):
        return version


def _find_latest_source_mtime(base_dir):
    ignore_dirs = {
        '.venv', '__pycache__', '.git', 'build', 'dist', 'data',
        'exports', 'uploads', 'assets', 'static', 'templates\\static'
    }
    latest = 0.0
    for root, dirs, files in os.walk(base_dir):
        rel_root = os.path.relpath(root, base_dir)
        if rel_root == '.':
            rel_root = ''
        rel_parts = rel_root.split(os.sep) if rel_root else []
        if any(part in ignore_dirs for part in rel_parts):
            dirs[:] = []
            continue
        for fname in files:
            if fname == 'VERSION':
                continue
            fpath = os.path.join(root, fname)
            try:
                mtime = os.path.getmtime(fpath)
                if mtime > latest:
                    latest = mtime
            except Exception:
                continue
    return latest


def _ensure_version_up_to_date():
    """Read version from VERSION file, check if source files changed, and auto-bump if needed."""
    vpath = os.path.join(os.path.dirname(__file__), 'VERSION')
    
    # Try to read from VERSION file first
    version = None
    try:
        if os.path.exists(vpath):
            with open(vpath, 'r', encoding='utf-8') as vf:
                version = (vf.read().strip() or None)
    except Exception:
        pass
    
    # Fallback: if no VERSION file or empty, create default
    if not version:
        version = "00.00.01"
        try:
            with open(vpath, 'w', encoding='utf-8') as vf:
                vf.write(version)
        except Exception:
            pass
    
    try:
        latest_mtime = _find_latest_source_mtime(os.path.dirname(__file__))
        v_mtime = os.path.getmtime(vpath) if os.path.exists(vpath) else 0
        if latest_mtime > v_mtime:
            old_version = version
            version = _bump_patch_version(version)
            try:
                with open(vpath, 'w', encoding='utf-8') as vf:
                    vf.write(version)
                print(f"[version] Bumped: {old_version} → {version}")
            except Exception as e:
                print(f"[version] Failed to write VERSION file: {e}")
    except Exception as e:
        print(f"[version] Error checking version: {e}")
    return version


# ================================================================
#  Register all route modules
# ================================================================
from routes.dashboard import register_dashboard_routes
from routes.students import register_student_routes
from routes.assistants import register_assistant_routes
from routes.api import register_api_routes
from routes.qr import register_qr_routes
from routes.reports import register_reports_routes
from routes.books import register_book_routes
from routes.instructor_profile import register_instructor_profile_routes
from routes.whatsapp import register_whatsapp_routes

# Register scanner route
@app.route('/qr/scanner')
def qr_scanner():
    """Display QR code scanner input Name:Kennedy D.
    Name:Kennedy D.
    Name:Kennedy D.
    page for hardware barcode scanner."""
    return render_template('qr_scanner.html')

register_dashboard_routes(app)
register_student_routes(app, UPLOAD_FOLDER)
register_assistant_routes(app)
register_instructor_profile_routes(app)
register_api_routes(app)
register_qr_routes(app)
register_reports_routes(app)
register_book_routes(app)
register_whatsapp_routes(app)

# Register utilities routes
from routes.utilities import register_utilities_routes
register_utilities_routes(app)


# ================================================================
#  Startup sanitation: ensure no lingering active sessions
# ================================================================
def _clear_state_on_startup():
    """On app start, stop any DB sessions left open and clear caches.
    This guarantees the Active Class column starts empty after a restart.
    """
    try:
        # Close any open DB sessions by setting end_time & duration (preserve history)
        try:
            closed = timer_manager.close_all_open_db_sessions()
            print(f'[startup] closed open DB sessions: {closed}')
        except Exception as e:
            print('[startup] close_all_open_db_sessions failed:', e)

        # Clear dashboard helper cache
        try:
            from routes.api import active_students_cache
            active_students_cache.clear()
        except Exception:
            pass
    except Exception as e:
        print("[startup] clear_state error:", e)


_clear_state_on_startup()


# ================================================================
#  Auto-bump version on startup if source files changed
# ================================================================
def _check_version_on_startup():
    """Check and auto-bump version on app startup if source files have changed."""
    current_version = _ensure_version_up_to_date()
    print(f"[startup] KumoClock version: {current_version}")

_check_version_on_startup()


# ================================================================
#  Auto-generate QR codes for students and assistants without them
# ================================================================
def _auto_generate_missing_qr_codes():
    """Generate QR codes for any students or assistants that don't have them yet."""
    try:
        import os
        out_dir = os.path.join('assets', 'qr_codes')
        os.makedirs(out_dir, exist_ok=True)
        
        # Generate QR codes for students without them
        students = student_manager.get_all_students()
        student_count = 0
        for s in students:
            sid = s[0]
            name = s[1]
            qr_path = os.path.join(out_dir, f"student_{sid}.png")
            if not os.path.exists(qr_path):
                try:
                    qr_data = f"ID:{sid}\nName:{name}"
                    qr_generator.generate_qr(qr_data, f"student_{sid}")
                    student_count += 1
                except Exception as e:
                    print(f"[startup] Failed to generate QR for student {sid}: {e}")
        
        # Generate QR codes for assistants without them
        assistants = assistant_manager.get_all_assistants()
        assistant_count = 0
        for a in assistants:
            aid = a[0]
            name = a[1]
            qr_path = os.path.join(out_dir, f"assistant_{aid}.png")
            if not os.path.exists(qr_path):
                try:
                    qr_data = f"ASST:{aid}\nName:{name}"
                    qr_generator.generate_qr(qr_data, f"assistant_{aid}")
                    assistant_count += 1
                except Exception as e:
                    print(f"[startup] Failed to generate QR for assistant {aid}: {e}")
        
        if student_count > 0 or assistant_count > 0:
            print(f'[startup] Auto-generated QR codes: {student_count} students, {assistant_count} assistants')
    except Exception as e:
        print("[startup] auto_generate_qr_codes error:", e)


_auto_generate_missing_qr_codes()


# ================================================================
#  Exit/Shutdown Route
# ================================================================
@app.route("/exit", methods=["GET", "POST"])
def exit_app():
    """Handle application exit/shutdown with graceful browser window closure."""
    import sys
    import threading
    
    print("\n[EXIT] User initiated application shutdown...")
    profiler.print_summary()
    
    # Schedule shutdown after response is sent (1 second delay)
    def delayed_shutdown():
        import time
        time.sleep(1)
        print("[EXIT] Closing application...")
        sys.exit(0)
    
    shutdown_thread = threading.Thread(target=delayed_shutdown, daemon=True)
    shutdown_thread.start()
    
    # Return exit page with JavaScript to close the window
    return render_template("exit.html")


# ================================================================
#  Error Handling
# ================================================================
@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


# ================================================================
#  Shutdown handler - print profiler summary
# ================================================================
import atexit

def print_profiler_summary():
    """Print request profiler summary on app shutdown."""
    profiler.print_summary()

atexit.register(print_profiler_summary)


# ================================================================
#  Run app
# ================================================================
if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
