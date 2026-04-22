"""Fix the broken routes/students.py by rewriting the mangled POST handlers."""
import re

with open('routes/students.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the start of the function (students_add)
# Rewrite the entire students_add function body
students_add_post = '''    @app.route("/students/add", methods=["GET", "POST"])
    @require_login
    def students_add():
        owner_user_id = auth_manager.get_current_user_id()
        if request.method == "POST":
            subjects, subject_minutes = _parse_subjects_from_form(request.form)
            if not subjects:
                flash("Please add at least one subject.", "danger")
                return redirect(url_for("students_add"))

            _sched_json = request.form.get("schedule_json", "")
            _d1, _d2, _dt1, _dt2 = _extract_days(_sched_json)
            student_id = student_manager.add_student(
                request.form["name"],
                subjects[0],
                request.form.get("email", ""),
                request.form.get("phone", ""),
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
            # Invalidate tenant-scoped list lane + this student\'s static profile lane.
            _invalidate_student_caches(owner_user_id, student_id=student_id)
            # Save photo after we have the student_id
            photo_file = request.files.get(\'photo\')
            if photo_file and photo_file.filename:
                saved = _save_student_photo(photo_file, student_id)
                if saved:
                    student_manager.set_student_photo(student_id, saved, owner_user_id)
            flash("Student added successfully.", "success")
            return redirect(url_for("students_list"))
        
        # Get instructor profile for class hours
        profile = instructor_profile_manager.get_instructor_profile(owner_user_id=owner_user_id)
        subject_rows = [
            {"name": "Math", "minutes": 30, "selected": True},
            {"name": "Reading", "minutes": 30, "selected": False},
            {"name": "Writing", "minutes": 30, "selected": False},
        ]
        return render_template("student_form.html", action="Add", student=None, profile=profile, subject_rows=subject_rows, student_photo=\'\', student_schedule=[])'''

students_edit_post_core = '''    @app.route("/students/edit/<int:sid>", methods=["GET", "POST"])
    @require_login
    def students_edit(sid):
        owner_user_id = auth_manager.get_current_user_id()
        stu = student_manager.get_student(sid, owner_user_id)
        if not stu:
            return "Student not found", 404
        if request.method == "POST":
            subjects, subject_minutes = _parse_subjects_from_form(request.form)
            if not subjects:
                flash("Please add at least one subject.", "danger")
                return redirect(url_for("students_edit", sid=sid))

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
            # Invalidate static profile/goals lane for this student + user-scoped list lane.
            _invalidate_student_caches(owner_user_id, student_id=sid)
            # Save photo if a new one was uploaded
            photo_file = request.files.get(\'photo\')
            if photo_file and photo_file.filename:
                saved = _save_student_photo(photo_file, sid)
                if saved:
                    student_manager.set_student_photo(sid, saved, owner_user_id)
            flash("Student updated.", "info")
            # Check if came from calendar
            from_calendar = request.args.get(\'from_calendar\')
            if from_calendar:
                return redirect(url_for(\'center_calendar\'))
            return redirect(url_for("students_list"))
        
        # Get instructor profile for class hours
        profile = instructor_profile_manager.get_instructor_profile(owner_user_id=owner_user_id)
        from_calendar = request.args.get(\'from_calendar\')
        subjects = []
        minutes = []
        if len(stu) > 16 and stu[16]:
            try:
                subjects = json.loads(stu[16])
            except (TypeError, ValueError):
                subjects = []
        if len(stu) > 17 and stu[17]:
            try:
                minutes = json.loads(stu[17])
            except (TypeError, ValueError):
                minutes = []
        if not subjects:
            subjects = [stu[2]] if len(stu) > 2 and stu[2] else [""]
        if not minutes:
            minutes = [30] * len(subjects)

        subject_rows = []
        for idx, subject_name in enumerate(subjects):
            minute_val = 30
            if idx < len(minutes):
                try:
                    minute_val = max(5, int(minutes[idx]))
                except (TypeError, ValueError):
                    minute_val = 30
            subject_rows.append({"name": str(subject_name or ""), "minutes": minute_val})
        if not subject_rows:
            subject_rows = [
                {"name": "Math", "minutes": 30, "selected": True},
                {"name": "Reading", "minutes": 30, "selected": False},
                {"name": "Writing", "minutes": 30, "selected": False},
            ]

        student_schedule = []
        if len(stu) > 20 and stu[20]:
            try:
                student_schedule = json.loads(stu[20])
            except (ValueError, TypeError):
                pass
        if not student_schedule:
            if stu[12]:
                student_schedule.append({\'day\': stu[12], \'time\': stu[14] or \'\'})
            if stu[13]:
                student_schedule.append({\'day\': stu[13], \'time\': stu[15] or \'\'})
        return render_template(
            "student_form.html",
            action="Edit",
            student=stu,
            profile=profile,
            from_calendar=from_calendar,
            subject_rows=subject_rows,
            student_photo=str(stu[19] or \'\') if len(stu) > 19 else \'\',
            student_schedule=student_schedule,
        )'''

# Use regex to replace the broken section from the students/add route declaration
# through the students/edit route declaration end
pattern = re.compile(
    r'    @app\.route\("/students/add", methods=\["GET", "POST"\]\).*?'
    r'(?=    @app\.route\("/students/delete/)',
    re.DOTALL
)

replacement = students_add_post + '\n\n' + students_edit_post_core + '\n\n'
new_content = pattern.sub(replacement, content)

if new_content == content:
    print("ERROR: pattern not found!")
else:
    print("Pattern replaced OK")
    with open('routes/students.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Written")

# Verify
import ast
with open('routes/students.py', 'r', encoding='utf-8') as f:
    src = f.read()
try:
    ast.parse(src)
    print("Syntax OK")
except SyntaxError as e:
    print(f"Syntax error at line {e.lineno}: {e}")
