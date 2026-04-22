"""Final fix for routes/students.py - remove all garbage fragments."""
import re

with open('routes/students.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Fix students_delete (body was replaced with just redirect)
old_delete = '''    def students_delete(sid):
        return redirect(url_for("students_list"))'''
new_delete = '''    def students_delete(sid):
        owner_user_id = auth_manager.get_current_user_id()
        student_manager.delete_student(sid, owner_user_id)
        _invalidate_student_caches(owner_user_id, student_id=sid)
        flash("Student deleted.", "warning")
        return redirect(url_for("students_list"))'''
content = content.replace(old_delete, new_delete, 1)

# 2. Remove garbage between @require_admin decorator and students_reactivate def
old_garbage = '''    @app.route("/students/reactivate/<int:sid>", methods=["POST"])
    @require_admin
                    _sched_json = request.form.get("schedule_json", "")
                    _d1, _d2, _dt1, _dt2 = _extract_days(_sched_json)
                    student_manager.update_student(
                        sid,
                        request.form["name"],
                        request.form.get("email", ""),
                        request.form.get("phone", ""),
                        subject=subjects[0],
                        book_loaned=int(bool(request.form.get("book_loaned"))),
                        paper_ws=int(bool(request.form.get("paper_ws"))),
                        el=int(bool(request.form.get("el"))),
                        pi=int(bool(request.form.get("pi"))),
                        v=int(bool(request.form.get("v"))),
                        day1=_d1,
                        day2=_d2,
                        day1_time=_dt1,
                        day2_time=_dt2,
                        owner_user_id=owner_user_id,
                        subjects=subjects,
                        subject_minutes=subject_minutes,
                        schedule_json=_sched_json,
                    )
    def students_reactivate(sid):'''
new_reactivate = '''    @app.route("/students/reactivate/<int:sid>", methods=["POST"])
    @require_admin
    def students_reactivate(sid):'''
content = content.replace(old_garbage, new_reactivate, 1)

# 3. Fix students_export (has garbage injected)
old_export = '''    def students_export():
        from flask import send_file
        export_folder = "exports"
        export_path = os.path.join(export_folder, "students_export.csv")
                    student_schedule=student_schedule,
        owner_user_id = auth_manager.get_current_user_id()
        # Export only this user's students
        student_manager.export_csv(export_path, owner_user_id)
        return send_file(export_path, as_attachment=True)'''
new_export = '''    def students_export():
        from flask import send_file
        export_folder = "exports"
        export_path = os.path.join(export_folder, "students_export.csv")
        owner_user_id = auth_manager.get_current_user_id()
        # Export only this user's students
        student_manager.export_csv(export_path, owner_user_id)
        return send_file(export_path, as_attachment=True)'''
content = content.replace(old_export, new_export, 1)

with open('routes/students.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Written")

# Verify syntax
import ast
with open('routes/students.py', 'r', encoding='utf-8') as f:
    src = f.read()
try:
    ast.parse(src)
    print("Syntax OK")
except SyntaxError as e:
    print(f"Syntax error at line {e.lineno}: {e.msg}")
    # Print context around error
    lines = src.splitlines()
    start = max(0, e.lineno - 3)
    end = min(len(lines), e.lineno + 2)
    for i, line in enumerate(lines[start:end], start + 1):
        marker = " >>>" if i == e.lineno else "    "
        print(f"{marker} {i}: {line}")
