# routes/reports.py
import io
import csv
import sqlite3
from datetime import datetime, timedelta
from flask import render_template, request, send_file, redirect, url_for
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from modules import reports

DB_PATH = "kumoclock/data.db"

def register_reports_routes(app):
    """Register reports routes (assistant hours and attendance)."""
    
    # ================================================================
    # Assistant Hours Reports
    # ================================================================
    
    @app.route('/reports/assistants')
    def reports_assistants():
        """Display assistant hours summary report."""
        days = int(request.args.get('days', 30))
        data = reports.get_assistant_hours_summary(days=days)
        return render_template('reports_assistants.html', data=data, days=days)

    @app.route('/reports/assistants/pdf')
    def reports_assistants_pdf():
        """Generate PDF of assistant hours report."""
        days = int(request.args.get('days', 30))
        path = reports.generate_assistant_hours_report(days=days)
        return send_file(path, as_attachment=True)

    @app.route('/reports/assistants/csv')
    def reports_assistants_csv():
        """Generate CSV of assistant duty log with date range."""
        start = request.args.get('start')
        end = request.args.get('end')
        if not start or not end:
            return redirect(url_for('reports_assistants'))
        
        sessions = reports.get_assistant_sessions_between(start, end)
        summary = reports.get_assistant_hours_between(start, end)
        
        def round_up_to_0_1(value):
            import math
            return math.ceil(value * 10) / 10.0
        
        si = io.StringIO()
        writer = csv.writer(si)
        
        writer.writerow(['ASSISTANT DUTY LOG', start, 'to', end])
        writer.writerow([])
        writer.writerow(['Name', 'Date', 'Start Time', 'End Time', 'Duration (seconds)'])
        for name, date_only, start_iso, end_iso, duration_sec in sessions:
            start_time = start_iso.split('T')[1][:5] if 'T' in start_iso else start_iso
            end_time = end_iso.split('T')[1][:5] if 'T' in end_iso else end_iso
            writer.writerow([name, date_only, start_time, end_time, duration_sec])
        
        writer.writerow([])
        writer.writerow(['SUMMARY BY ASSISTANT'])
        writer.writerow(['Name', 'Total Hours (rounded up)'])
        for name, sessions_count, total_sec in summary:
            hours = total_sec / 3600.0
            hours_rounded = round_up_to_0_1(hours)
            writer.writerow([name, f'{hours_rounded:.1f}'])
        
        from flask import Response
        output = si.getvalue().encode('utf-8-sig')
        filename = f"assistant_hours_{start}_to_{end}.csv"
        headers = {
            'Content-Disposition': f'attachment; filename="{filename}"'
        }
        return Response(output, mimetype='text/csv', headers=headers)

    # ================================================================
    # Attendance Reports
    # ================================================================

    @app.route('/reports/class-attendance/pdf')
    def class_attendance_pdf():
        """Generate PDF: Class attendance by date with active student list."""
        start_param = request.args.get('start')
        end_param = request.args.get('end')
        if not start_param or not end_param:
            return "start and end parameters are required (YYYY-MM-DD)", 400

        try:
            start_date = datetime.strptime(start_param, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_param, '%Y-%m-%d').date()
        except ValueError:
            return "Invalid date format; expected YYYY-MM-DD", 400

        if end_date < start_date:
            return "end must be on or after start", 400

        today = datetime.today().date()
        earliest = today - timedelta(days=30)
        if start_date < earliest or end_date > today or (end_date - start_date).days > 30:
            return "Range must be within the last 30 calendar days", 400

        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            query = """
                SELECT DATE(sess.start_time) as day, s.name
                FROM sessions AS sess
                JOIN students AS s ON s.id = sess.student_id
                WHERE s.active = 1
                  AND DATE(sess.start_time) >= ? AND DATE(sess.start_time) <= ?
                ORDER BY day, s.name
            """
            c.execute(query, (start_date.isoformat(), end_date.isoformat()))
            rows = c.fetchall()

        by_day = {}
        for day, name in rows:
            by_day.setdefault(day, set()).add(name)

        buffer = io.BytesIO()
        canv = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter

        canv.setFont("Helvetica-Bold", 16)
        canv.drawString(inch, height - inch, "Class Attendance Report")
        canv.setFont("Helvetica", 12)
        canv.drawString(inch, height - inch - 0.3*inch, f"Date Range: {start_date} to {end_date}")

        y = height - inch - 0.7*inch
        canv.setFont("Helvetica-Bold", 11)
        canv.drawString(inch, y, "Session Date")
        canv.drawString(inch + 2.2*inch, y, "# Active Students")
        canv.drawString(inch + 4.2*inch, y, "Active Student List")

        y -= 0.3*inch
        canv.setFont("Helvetica", 10)
        for day in sorted(by_day.keys()):
            names = sorted(list(by_day[day]))
            count = len(names)
            names_str = ", ".join(names)

            def wrap_text(txt, limit=90):
                if len(txt) <= limit:
                    return [txt]
                parts, line = [], []
                for w in txt.split(', '):
                    candidate = (', '.join(line+[w])) if line else w
                    if len(candidate) > limit:
                        parts.append(', '.join(line))
                        line = [w]
                    else:
                        line.append(w)
                if line:
                    parts.append(', '.join(line))
                return parts

            lines = wrap_text(names_str, 90)

            canv.drawString(inch, y, str(day))
            canv.drawString(inch + 2.2*inch, y, str(count))
            canv.drawString(inch + 4.2*inch, y, lines[0] if lines else '')
            y -= 0.25*inch

            for extra in lines[1:]:
                canv.drawString(inch + 4.2*inch, y, extra)
                y -= 0.22*inch
                if y < inch:
                    canv.showPage()
                    canv.setFont("Helvetica", 10)
                    y = height - inch

            if y < inch:
                canv.showPage()
                canv.setFont("Helvetica", 10)
                y = height - inch

        canv.save()
        buffer.seek(0)
        filename = f"class_attendance_{start_date}_to_{end_date}.pdf"
        return send_file(buffer, mimetype='application/pdf', as_attachment=True, download_name=filename)

    @app.route('/reports/student-attendance/pdf')
    def student_attendance_pdf():
        """Generate PDF: Student session history with durations in HH:MM format."""
        sid = request.args.get('sid', type=int)
        start_param = request.args.get('start')
        end_param = request.args.get('end')
        if not sid or not start_param or not end_param:
            return "sid, start and end parameters are required", 400

        try:
            start_date = datetime.strptime(start_param, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_param, '%Y-%m-%d').date()
        except ValueError:
            return "Invalid date format; expected YYYY-MM-DD", 400

        if end_date < start_date:
            return "end must be on or after start", 400

        today = datetime.today().date()
        earliest = today - timedelta(days=30)
        if start_date < earliest or end_date > today or (end_date - start_date).days > 30:
            return "Range must be within the last 30 calendar days", 400

        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            srow = c.execute("SELECT name FROM students WHERE id=?", (sid,)).fetchone()
            if not srow:
                return "Student not found", 404
            student_name = srow[0]

            q = """
                SELECT DATE(start_time) as day, duration
                FROM sessions
                WHERE student_id = ?
                  AND DATE(start_time) >= ? AND DATE(start_time) <= ?
                ORDER BY start_time ASC
            """
            c.execute(q, (sid, start_date.isoformat(), end_date.isoformat()))
            sessions = c.fetchall()

        buffer = io.BytesIO()
        canv = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter

        canv.setFont("Helvetica-Bold", 16)
        canv.drawString(inch, height - inch, "Student Attendance Report")
        canv.setFont("Helvetica", 12)
        canv.drawString(inch, height - inch - 0.3*inch, f"Student: {student_name} (ID {sid})")
        canv.drawString(inch, height - inch - 0.55*inch, f"Date Range: {start_date} to {end_date}")

        y = height - inch - 0.9*inch
        canv.setFont("Helvetica-Bold", 11)
        canv.drawString(inch, y, "Session Date")
        canv.drawString(inch + 3.0*inch, y, "Session Active Time")

        y -= 0.3*inch
        canv.setFont("Helvetica", 10)
        def fmt(sec):
            sec = sec or 0
            h = sec // 3600
            m = (sec % 3600) // 60
            return f"{int(h):02d}:{int(m):02d}"

        for day, duration in sessions:
            canv.drawString(inch, y, str(day))
            canv.drawString(inch + 3.0*inch, y, fmt(duration))
            y -= 0.25*inch
            if y < inch:
                canv.showPage()
                canv.setFont("Helvetica", 10)
                y = height - inch

        if not sessions:
            canv.drawString(inch, y, "No sessions found in the selected range.")

        canv.save()
        buffer.seek(0)
        filename = f"student_{sid}_attendance_{start_date}_to_{end_date}.pdf"
        return send_file(buffer, mimetype='application/pdf', as_attachment=True, download_name=filename)
