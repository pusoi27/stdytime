# ================================================================
#  KumoClock v2.3.12 - Main Flask Application (Refactored)
# ================================================================
"""
KumoClock: Student class management system with dashboard, QR codes, and PDF label generation.
Features: Student management, session tracking, photo support, QR generation, Avery 8160 PDF output, assistant duty tracking.
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

# Student photo directories
STUDENT_PHOTOS_STATIC = os.path.join('static', 'img', 'students')
TEMPLATES_STUDENT_PHOTOS = os.path.join('templates', 'static', 'img', 'students')
os.makedirs(STUDENT_PHOTOS_STATIC, exist_ok=True)
os.makedirs(TEMPLATES_STUDENT_PHOTOS, exist_ok=True)

# ================================================================
#  Photo scanning and management
# ================================================================
@app.route('/api/photos/scan', methods=['POST'])
def api_photos_scan():
    """Scan a user-provided folder for image files and copy them into the
    application's photo folders so the dashboard can serve them.

    Expects JSON: { "path": "<absolute-or-relative-path>" }
    Returns JSON with `copied` (files copied) and `available` (all image files seen).
    """
    data = request.get_json(silent=True) or {}
    path = (data.get('path') or '').strip()
    if not path:
        return jsonify({'error': 'no path provided'}), 400
    if not os.path.isabs(path):
        path = os.path.abspath(os.path.join(os.getcwd(), path))
    if not os.path.isdir(path):
        return jsonify({'error': 'path not found', 'path': path}), 400

    allowed_ext = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp'}
    copied = []
    available = []
    try:
        for fname in sorted(os.listdir(path)):
            if os.path.splitext(fname)[1].lower() in allowed_ext:
                available.append(fname)
                src = os.path.join(path, fname)
                dst = os.path.join(STUDENT_PHOTOS_STATIC, fname)
                tdst = os.path.join(TEMPLATES_STUDENT_PHOTOS, fname)
                try:
                    if (not os.path.exists(dst)) or (os.path.getmtime(src) > os.path.getmtime(dst)):
                        shutil.copy2(src, dst)
                        copied.append(fname)
                    if (not os.path.exists(tdst)) or (os.path.getmtime(src) > os.path.getmtime(tdst)):
                        shutil.copy2(src, tdst)
                except Exception:
                    continue
    except Exception as e:
        return jsonify({'error': 'scan failed', 'detail': str(e)}), 500

    return jsonify({'copied': copied, 'available': available, 'path': path})


# Serve student photos from templates folder as a fallback path
@app.route('/templates_static/img/students/<path:filename>')
def serve_templates_student_photo(filename):
    return send_from_directory(TEMPLATES_STUDENT_PHOTOS, filename)


# ================================================================
#  Context processors
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
    parts = version.split('.')
    if not parts:
        return version
    last = parts[-1]
    if not last.isdigit():
        return version
    width = len(last)
    bumped = str(int(last) + 1).zfill(width)
    parts[-1] = bumped
    return '.'.join(parts)


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
    version = "06.07.43"
    vpath = os.path.join(os.path.dirname(__file__), 'VERSION')
    try:
        if os.path.exists(vpath):
            with open(vpath, 'r', encoding='utf-8') as vf:
                version = (vf.read().strip() or version)
        latest_mtime = _find_latest_source_mtime(os.path.dirname(__file__))
        v_mtime = os.path.getmtime(vpath) if os.path.exists(vpath) else 0
        if latest_mtime > v_mtime:
            version = _bump_patch_version(version)
            try:
                with open(vpath, 'w', encoding='utf-8') as vf:
                    vf.write(version)
            except Exception:
                pass
    except Exception:
        pass
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
register_student_routes(app, STUDENT_PHOTOS_STATIC, TEMPLATES_STUDENT_PHOTOS, UPLOAD_FOLDER)
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
#  Error Handling
# ================================================================
@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


# ================================================================
#  Run app
# ================================================================
if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
