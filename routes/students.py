# routes/students.py
from flask import render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
from modules import student_manager, instructor_profile_manager
import sqlite3
from modules.database import DB_PATH
import os

def register_student_routes(app, upload_folder):
    """Register student CRUD and CSV routes."""
    
    @app.route("/students")
    def students_list():
        # Get duplicate information to display alerts
        duplicate_summary = student_manager.get_duplicate_summary()
        has_duplicates = student_manager.has_duplicate_names()
        
        return render_template(
            "students.html",
            students=student_manager.get_all_students(),
            deleted_students=student_manager.get_deleted_students(),
            has_duplicates=has_duplicates,
            duplicate_summary=duplicate_summary,
        )

    @app.route("/students/duplicates")
    def students_duplicates():
        """Display all duplicate student names with their details."""
        duplicate_summary = student_manager.get_duplicate_summary()
        return render_template(
            "students_duplicates.html",
            duplicate_summary=duplicate_summary,
            has_duplicates=len(duplicate_summary) > 0,
        )

    @app.route("/api/students/duplicates")
    def api_get_duplicates():
        """API endpoint to get duplicate student names (JSON response)."""
        from flask import jsonify
        duplicate_summary = student_manager.get_duplicate_summary()
        has_duplicates = len(duplicate_summary) > 0
        
        return jsonify({
            'success': True,
            'has_duplicates': has_duplicates,
            'total_duplicate_names': len(duplicate_summary),
            'duplicates': duplicate_summary
        })

    @app.route("/students/add", methods=["GET", "POST"])
    def students_add():
        if request.method == "POST":
            subject = (request.form.get("subject", "").strip() or "")
            if subject not in {"S1", "S2"}:
                flash("Please select a valid Subject (S1 or S2).", "danger")
                return redirect(url_for("students_add"))
            student_manager.add_student(
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
            )
            flash("Student added successfully.", "success")
            return redirect(url_for("students_list"))
        
        # Get instructor profile for class hours
        profile = instructor_profile_manager.get_instructor_profile()
        return render_template("student_form.html", action="Add", student=None, profile=profile)

    @app.route("/students/edit/<int:sid>", methods=["GET", "POST"])
    def students_edit(sid):
        stu = student_manager.get_student(sid)
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
            )
            flash("Student updated.", "info")
            # Check if came from calendar
            from_calendar = request.args.get('from_calendar')
            if from_calendar:
                return redirect(url_for('center_calendar'))
            return redirect(url_for("students_list"))
        
        # Get instructor profile for class hours
        profile = instructor_profile_manager.get_instructor_profile()
        from_calendar = request.args.get('from_calendar')
        return render_template("student_form.html", action="Edit", student=stu, profile=profile, from_calendar=from_calendar)

    @app.route("/students/delete/<int:sid>")
    def students_delete(sid):
        student_manager.delete_student(sid)
        flash("Student deleted.", "warning")
        return redirect(url_for("students_list"))

    @app.route("/students/reactivate/<int:sid>")
    def students_reactivate(sid):
        student_manager.reactivate_student(sid)
        flash("Student reactivated.", "success")
        return redirect(url_for("students_list"))

    @app.route("/students/permanent-delete/<int:sid>")
    def students_permanent_delete(sid):
        student_manager.permanent_delete_student(sid)
        flash("Student permanently deleted.", "danger")
        return redirect(url_for("students_list"))

    @app.route("/students/import", methods=["POST"])
    def students_import():
        file = request.files.get("csvfile")
        if not file or file.filename == "":
            flash("No file selected.", "danger")
            return redirect(url_for("students_list"))
        path = os.path.join(upload_folder, secure_filename(file.filename))
        file.save(path)
        result = student_manager.import_csv(path)
        if isinstance(result, dict) and result.get("error"):
            flash(result.get("error"), "danger")
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
        flash(message, "success")
        return redirect(url_for("students_list"))

    @app.route("/students/export")
    def students_export():
        from flask import send_file
        export_folder = "exports"
        export_path = os.path.join(export_folder, "students_export.csv")
        student_manager.export_csv(export_path)
        return send_file(export_path, as_attachment=True)
