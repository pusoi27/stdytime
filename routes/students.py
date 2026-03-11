# routes/students.py
from flask import render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
from modules import student_manager, instructor_profile_manager, server_cache, db_backup_recovery, auth_manager
from routes.auth import require_login, require_admin
from routes.operation_utils import flash_scoped_failure, invalidate_scoped_cache
import sqlite3
from modules.database import DB_PATH
import os


def _students_list_cache_key(owner_user_id: int) -> str:
    return f"{server_cache.STUDENTS_LIST_CACHE_KEY}:u:{owner_user_id}"


def _student_goal_cache_key(owner_user_id: int, student_id: int) -> str:
    return f"{server_cache.STUDENT_GOAL_CACHE_PREFIX}u:{owner_user_id}:{student_id}"


def _student_goal_cache_prefix(owner_user_id: int) -> str:
    return f"{server_cache.STUDENT_GOAL_CACHE_PREFIX}u:{owner_user_id}:"


def _invalidate_student_caches(owner_user_id: int, student_id: int | None = None, all_goal_keys_for_user: bool = False):
    """Invalidate tenant-scoped student cache lanes."""
    server_cache.invalidate(_students_list_cache_key(owner_user_id))

    if student_id is not None:
        server_cache.invalidate(_student_goal_cache_key(owner_user_id, student_id))

    if all_goal_keys_for_user:
        server_cache.invalidate_prefix(_student_goal_cache_prefix(owner_user_id))


def register_student_routes(app, upload_folder):
    """Register student CRUD and CSV routes."""
    
    @app.route("/students")
    @require_login
    def students_list():
        # Get current user ID for tenant scoping
        owner_user_id = auth_manager.get_current_user_id()
        
        # Get duplicate information to display alerts
        duplicate_summary = student_manager.get_duplicate_summary(owner_user_id)
        has_duplicates = student_manager.has_duplicate_names(owner_user_id)
        
        return render_template(
            "students.html",
            students=student_manager.get_all_students(owner_user_id),
            deleted_students=student_manager.get_deleted_students(owner_user_id),
            has_duplicates=has_duplicates,
            duplicate_summary=duplicate_summary,
        )

    @app.route("/students/duplicates")
    @require_login
    def students_duplicates():
        """Display all duplicate student names with their details."""
        owner_user_id = auth_manager.get_current_user_id()
        duplicate_summary = student_manager.get_duplicate_summary(owner_user_id)
        return render_template(
            "students_duplicates.html",
            duplicate_summary=duplicate_summary,
            has_duplicates=len(duplicate_summary) > 0,
        )

    @app.route("/api/students/duplicates")
    @require_login
    def api_get_duplicates():
        """API endpoint to get duplicate student names (JSON response)."""
        from flask import jsonify
        owner_user_id = auth_manager.get_current_user_id()
        duplicate_summary = student_manager.get_duplicate_summary(owner_user_id)
        has_duplicates = len(duplicate_summary) > 0
        
        return jsonify({
            'success': True,
            'has_duplicates': has_duplicates,
            'total_duplicate_names': len(duplicate_summary),
            'duplicates': duplicate_summary
        })

    @app.route("/students/add", methods=["GET", "POST"])
    @require_login
    def students_add():
        owner_user_id = auth_manager.get_current_user_id()
        if request.method == "POST":
            subject = (request.form.get("subject", "").strip() or "")
            if subject not in {"S1", "S2"}:
                flash("Please select a valid Subject (S1 or S2).", "danger")
                return redirect(url_for("students_add"))
            student_id = student_manager.add_student(
                request.form["name"],
                subject,
                request.form.get("email", ""),
                request.form.get("phone", ""),
                request.form.get("whatsapp", ""),
                book_loaned=int(bool(request.form.get("book_loaned"))),
                paper_ws=int(bool(request.form.get("paper_ws"))),
                math_goal=request.form.get("math_goal", ""),
                math_worksheets_per_week=request.form.get("math_worksheets_per_week", 0),
                reading_goal=request.form.get("reading_goal", ""),
                reading_worksheets_per_week=request.form.get("reading_worksheets_per_week", 0),
                el=int(bool(request.form.get("el"))),
                pi=int(bool(request.form.get("pi"))),
                v=int(bool(request.form.get("v"))),
                day1=request.form.get("day1", ""),
                day2=request.form.get("day2", ""),
                day1_time=request.form.get("day1_time", ""),
                day2_time=request.form.get("day2_time", ""),
                owner_user_id=owner_user_id,
            )
            # Invalidate tenant-scoped list lane + this student's static profile lane.
            _invalidate_student_caches(owner_user_id, student_id=student_id)
            flash("Student added successfully.", "success")
            return redirect(url_for("students_list"))
        
        # Get instructor profile for class hours
        profile = instructor_profile_manager.get_instructor_profile(owner_user_id=owner_user_id)
        return render_template("student_form.html", action="Add", student=None, profile=profile)

    @app.route("/students/edit/<int:sid>", methods=["GET", "POST"])
    @require_login
    def students_edit(sid):
        owner_user_id = auth_manager.get_current_user_id()
        stu = student_manager.get_student(sid, owner_user_id)
        if not stu:
            return "Student not found", 404
        if request.method == "POST":
            subject = (request.form.get("subject", "").strip() or "")
            if subject not in {"S1", "S2"}:
                flash("Please select a valid Subject (S1 or S2).", "danger")
                return redirect(url_for("students_edit", sid=sid))
            student_manager.update_student(
                sid,
                request.form["name"],
                request.form.get("email", ""),
                request.form.get("phone", ""),
                request.form.get("whatsapp", ""),
                subject=subject,
                book_loaned=int(bool(request.form.get("book_loaned"))),
                paper_ws=int(bool(request.form.get("paper_ws"))),
                math_goal=request.form.get("math_goal", ""),
                math_worksheets_per_week=request.form.get("math_worksheets_per_week", 0),
                reading_goal=request.form.get("reading_goal", ""),
                reading_worksheets_per_week=request.form.get("reading_worksheets_per_week", 0),
                el=int(bool(request.form.get("el"))),
                pi=int(bool(request.form.get("pi"))),
                v=int(bool(request.form.get("v"))),
                day1=request.form.get("day1", ""),
                day2=request.form.get("day2", ""),
                day1_time=request.form.get("day1_time", ""),
                day2_time=request.form.get("day2_time", ""),
                owner_user_id=owner_user_id,
            )
            # Invalidate static profile/goals lane for this student + user-scoped list lane.
            _invalidate_student_caches(owner_user_id, student_id=sid)
            flash("Student updated.", "info")
            # Check if came from calendar
            from_calendar = request.args.get('from_calendar')
            if from_calendar:
                return redirect(url_for('center_calendar'))
            return redirect(url_for("students_list"))
        
        # Get instructor profile for class hours
        profile = instructor_profile_manager.get_instructor_profile(owner_user_id=owner_user_id)
        from_calendar = request.args.get('from_calendar')
        return render_template("student_form.html", action="Edit", student=stu, profile=profile, from_calendar=from_calendar)

    @app.route("/students/delete/<int:sid>", methods=["POST"])
    @require_admin
    def students_delete(sid):
        owner_user_id = auth_manager.get_current_user_id()
        student_manager.delete_student(sid, owner_user_id)
        _invalidate_student_caches(owner_user_id, student_id=sid)
        flash("Student deleted.", "warning")
        return redirect(url_for("students_list"))

    @app.route("/students/reactivate/<int:sid>", methods=["POST"])
    @require_admin
    def students_reactivate(sid):
        owner_user_id = auth_manager.get_current_user_id()
        student_manager.reactivate_student(sid, owner_user_id)
        _invalidate_student_caches(owner_user_id, student_id=sid)
        flash("Student reactivated.", "success")
        return redirect(url_for("students_list"))

    @app.route("/students/permanent-delete/<int:sid>", methods=["POST"])
    @require_admin
    def students_permanent_delete(sid):
        owner_user_id = auth_manager.get_current_user_id()
        student_manager.permanent_delete_student(sid, owner_user_id)
        _invalidate_student_caches(owner_user_id, student_id=sid)
        flash("Student permanently deleted.", "danger")
        return redirect(url_for("students_list"))

    @app.route("/students/import", methods=["POST"])
    @require_login
    def students_import():
        owner_user_id = auth_manager.get_current_user_id()
        file = request.files.get("csvfile")
        if not file or file.filename == "":
            flash("No file selected.", "danger")
            return redirect(url_for("students_list"))
        path = os.path.join(upload_folder, secure_filename(file.filename))
        file.save(path)
        backup_path = db_backup_recovery.create_backup("students_import")
        cache_invalidators = (
            lambda: _invalidate_student_caches(owner_user_id, all_goal_keys_for_user=True),
        )
        try:
            result = student_manager.import_csv(path, owner_user_id)
            if isinstance(result, dict) and result.get("error"):
                flash_scoped_failure(
                    backup_path=backup_path,
                    owner_user_id=owner_user_id,
                    table_names=("students",),
                    error=result.get("error"),
                    invalidators=cache_invalidators,
                )
                return redirect(url_for("students_list"))
        except Exception as e:
            flash_scoped_failure(
                backup_path=backup_path,
                owner_user_id=owner_user_id,
                table_names=("students",),
                error=e,
                invalidators=cache_invalidators,
            )
            return redirect(url_for("students_list"))
        added = result.get("added", 0) if isinstance(result, dict) else result
        updated = result.get("updated", 0) if isinstance(result, dict) else 0
        deleted = result.get("deleted", 0) if isinstance(result, dict) else 0
        
        message = f"Imported {added} new student(s)"
        if updated > 0:
            message += f", Updated {updated} student(s)"
        if deleted > 0:
            message += f", Deleted {deleted} student(s)"
        message += "."
        invalidate_scoped_cache(*cache_invalidators)
        flash(message, "success")
        return redirect(url_for("students_list"))

    @app.route("/students/export")
    @require_login
    def students_export():
        from flask import send_file
        export_folder = "exports"
        export_path = os.path.join(export_folder, "students_export.csv")
        owner_user_id = auth_manager.get_current_user_id()
        # Export only this user's students
        student_manager.export_csv(export_path, owner_user_id)
        return send_file(export_path, as_attachment=True)
