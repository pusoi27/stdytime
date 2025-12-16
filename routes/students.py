# routes/students.py
from flask import render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
from modules import student_manager
import sqlite3
from modules.database import DB_PATH
import os

def register_student_routes(app, student_photos_static, templates_student_photos, upload_folder):
    """Register student CRUD and CSV routes."""
    
    @app.route("/students")
    def students_list():
        return render_template(
            "students.html",
            students=student_manager.get_all_students(),
        )

    @app.route("/students/add", methods=["GET", "POST"])
    def students_add():
        if request.method == "POST":
            file = request.files.get("photo")
            filename = None
            if file and file.filename:
                filename = secure_filename(file.filename)
                file.save(os.path.join(student_photos_static, filename))
                try:
                    file.stream.seek(0)
                    file.save(os.path.join(templates_student_photos, filename))
                except Exception:
                    pass
            student_manager.add_student(
                request.form["name"],
                request.form.get("subject", ""),
                request.form.get("level", ""),
                request.form.get("email", ""),
                request.form.get("phone", ""),
                filename,
            )
            flash("Student added successfully.", "success")
            return redirect(url_for("students_list"))
        return render_template("student_form.html", action="Add", student=None)

    @app.route("/students/edit/<int:sid>", methods=["GET", "POST"])
    def students_edit(sid):
        stu = student_manager.get_student(sid)
        if not stu:
            return "Student not found", 404
        if request.method == "POST":
            file = request.files.get("photo")
            if file and file.filename:
                filename = secure_filename(file.filename)
                file.save(os.path.join(student_photos_static, filename))
                try:
                    file.stream.seek(0)
                    file.save(os.path.join(templates_student_photos, filename))
                except Exception:
                    pass
                with sqlite3.connect(DB_PATH) as conn:
                    conn.execute("UPDATE students SET photo=? WHERE id=?", (filename, sid))
                    conn.commit()
            student_manager.update_student(
                sid,
                request.form["name"],
                request.form.get("subject", ""),
                request.form.get("level", ""),
                request.form.get("email", ""),
                request.form.get("phone", ""),
            )
            flash("Student updated.", "info")
            return redirect(url_for("students_list"))
        return render_template("student_form.html", action="Edit", student=stu)

    @app.route("/students/delete/<int:sid>")
    def students_delete(sid):
        student_manager.delete_student(sid)
        flash("Student deleted.", "warning")
        return redirect(url_for("students_list"))

    @app.route("/students/import", methods=["POST"])
    def students_import():
        file = request.files.get("csvfile")
        if not file or file.filename == "":
            flash("No file selected.", "danger")
            return redirect(url_for("students_list"))
        path = os.path.join(upload_folder, secure_filename(file.filename))
        file.save(path)
        added = student_manager.import_csv(path)
        flash(f"Imported {added} new student(s).", "success")
        return redirect(url_for("students_list"))

    @app.route("/students/export")
    def students_export():
        from flask import send_file
        export_folder = "exports"
        export_path = os.path.join(export_folder, "students_export.csv")
        student_manager.export_csv(export_path)
        return send_file(export_path, as_attachment=True)
