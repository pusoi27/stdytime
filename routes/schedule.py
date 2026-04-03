# routes/schedule.py
import io

from flask import render_template, request, jsonify, send_file, url_for
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from werkzeug.routing import BuildError
from modules import schedule_manager, instructor_profile_manager, assistant_manager, auth_manager
from routes.auth import require_login, require_feature


def register_schedule_routes(app):
    """Register assistant scheduling routes."""

    @app.route("/schedule/assistants")
    @require_login
    @require_feature(auth_manager.FEATURE_ASSISTANTS)
    def schedule_assistants():
        """Display calendar-based assistant scheduling interface."""
        owner_user_id = auth_manager.get_current_user_id()
        
        # Get current month/year (or from query params)
        today = datetime.today().date()
        year = request.args.get("year", default=today.year, type=int)
        month = request.args.get("month", default=today.month, type=int)
        
        # Validate month bounds
        if month < 1:
            month = 12
            year -= 1
        elif month > 12:
            month = 1
            year += 1
        
        # Get instructor profile to determine operating hours
        profile = instructor_profile_manager.get_instructor_profile(owner_user_id)
        
        # Map center operating hours by day of week (0=Monday, 6=Sunday)
        operating_days = {}
        if profile:
            days_map = {
                "monday": 0,
                "tuesday": 1,
                "wednesday": 2,
                "thursday": 3,
                "friday": 4,
                "saturday": 5,
                "sunday": 6,
            }
            for day_name, day_idx in days_map.items():
                start_col = f"{day_name}_start"
                end_col = f"{day_name}_end"
                start_time = profile.get(start_col)
                end_time = profile.get(end_col)
                if start_time:
                    operating_days[day_idx] = {
                        "start": start_time,
                        "end": end_time,
                    }
        
        # Build calendar grid
        first_day = datetime(year, month, 1).date()
        first_weekday = first_day.weekday()  # 0=Monday
        
        # Calculate number of days in month
        if month == 12:
            last_day = datetime(year + 1, 1, 1).date() - timedelta(days=1)
        else:
            last_day = datetime(year, month + 1, 1).date() - timedelta(days=1)
        
        days_in_month = last_day.day
        
        # Get scheduled assistants for this month
        scheduled = schedule_manager.get_assistants_schedule_for_month(year, month, owner_user_id)
        
        # Get all unscheduled assistants (pool)
        all_assistants = assistant_manager.get_all_assistants(owner_user_id)
        
        # Build calendar weeks
        calendar_weeks = []
        week = [None] * 7  # Monday to Sunday
        for offset in range(first_weekday):
            week[offset] = None  # Empty cells before month starts
        
        for day_num in range(1, days_in_month + 1):
            date_obj = datetime(year, month, day_num).date()
            date_str = date_obj.isoformat()
            weekday = date_obj.weekday()
            
            is_operating = weekday in operating_days
            scheduled_assistants = scheduled.get(date_str, [])
            
            week[weekday] = {
                "day": day_num,
                "date": date_str,
                "is_operating": is_operating,
                "assistants": scheduled_assistants,
            }
            
            # End of week or end of month
            if weekday == 6:
                calendar_weeks.append(week)
                week = [None] * 7
        
        # Add final week if it has any days
        if any(w is not None for w in week):
            calendar_weeks.append(week)
        
        try:
            pdf_url = url_for("schedule_assistants_pdf", year=year, month=month)
        except BuildError:
            # Fallback for stale server/module states; avoids template hard failure.
            pdf_url = f"/schedule/assistants/pdf?year={year}&month={month}"

        return render_template(
            "schedule_assistants.html",
            year=year,
            month=month,
            month_name=datetime(year, month, 1).strftime("%B"),
            calendar_weeks=calendar_weeks,
            operating_days=operating_days,
            all_assistants=all_assistants,
            today=today.isoformat(),
            pdf_url=pdf_url,
        )

    @app.route("/api/schedule/assign", methods=["POST"])
    @require_login
    @require_feature(auth_manager.FEATURE_ASSISTANTS)
    def api_schedule_assign():
        """Assign an assistant to a date (drag-drop or form submission)."""
        owner_user_id = auth_manager.get_current_user_id()
        data = request.get_json(silent=True) or {}

        try:
            assistant_id = int(data.get("assistant_id")) if data.get("assistant_id") is not None else None
        except (TypeError, ValueError):
            assistant_id = None
        scheduled_date = data.get("scheduled_date")
        
        if not assistant_id or not scheduled_date:
            return jsonify({"error": "Missing assistant_id or scheduled_date"}), 400
        
        # Verify assistant belongs to this user
        asst = assistant_manager.get_assistant(assistant_id, owner_user_id)
        if not asst:
            return jsonify({"error": "Assistant not found"}), 404
        
        success = schedule_manager.schedule_assistant(
            assistant_id, scheduled_date, owner_user_id
        )
        
        if success:
            return jsonify({"success": True, "message": "Assistant scheduled"}), 200
        else:
            return jsonify({"error": "Assistant already scheduled for this date"}), 400

    @app.route("/api/schedule/unassign", methods=["POST"])
    @require_login
    @require_feature(auth_manager.FEATURE_ASSISTANTS)
    def api_schedule_unassign():
        """Remove an assistant from a scheduled date."""
        owner_user_id = auth_manager.get_current_user_id()
        data = request.get_json(silent=True) or {}

        try:
            assistant_id = int(data.get("assistant_id")) if data.get("assistant_id") is not None else None
        except (TypeError, ValueError):
            assistant_id = None
        scheduled_date = data.get("scheduled_date")
        
        if not assistant_id or not scheduled_date:
            return jsonify({"error": "Missing assistant_id or scheduled_date"}), 400
        
        count = schedule_manager.unschedule_assistant(
            assistant_id, scheduled_date, owner_user_id
        )
        
        if count > 0:
            return jsonify({"success": True, "message": "Assistant unscheduled"}), 200
        else:
            return jsonify({"error": "Assistant not found in schedule"}), 400

    @app.route("/schedule/assistants/pdf")
    @require_login
    @require_feature(auth_manager.FEATURE_ASSISTANTS)
    def schedule_assistants_pdf():
        """Export monthly assistant schedule as PDF."""
        owner_user_id = auth_manager.get_current_user_id()
        today = datetime.today().date()
        year = request.args.get("year", default=today.year, type=int)
        month = request.args.get("month", default=today.month, type=int)

        if month < 1:
            month = 1
        if month > 12:
            month = 12

        profile = instructor_profile_manager.get_instructor_profile(owner_user_id)
        operating_days = set()
        if profile:
            days_map = {
                "monday": 0,
                "tuesday": 1,
                "wednesday": 2,
                "thursday": 3,
                "friday": 4,
                "saturday": 5,
                "sunday": 6,
            }
            for day_name, day_idx in days_map.items():
                if profile.get(f"{day_name}_start"):
                    operating_days.add(day_idx)

        first_day = datetime(year, month, 1).date()
        first_weekday = first_day.weekday()
        if month == 12:
            last_day = datetime(year + 1, 1, 1).date() - timedelta(days=1)
        else:
            last_day = datetime(year, month + 1, 1).date() - timedelta(days=1)

        scheduled = schedule_manager.get_assistants_schedule_for_month(year, month, owner_user_id)

        weeks = []
        week = [None] * 7
        for offset in range(first_weekday):
            week[offset] = None

        for day_num in range(1, last_day.day + 1):
            date_obj = datetime(year, month, day_num).date()
            date_str = date_obj.isoformat()
            weekday = date_obj.weekday()
            week[weekday] = {
                "day": day_num,
                "date": date_str,
                "is_operating": weekday in operating_days,
                "assistants": scheduled.get(date_str, []),
            }
            if weekday == 6:
                weeks.append(week)
                week = [None] * 7
        if any(w is not None for w in week):
            weeks.append(week)

        buffer = io.BytesIO()
        canv = canvas.Canvas(buffer, pagesize=landscape(letter))
        width, height = landscape(letter)

        month_title = datetime(year, month, 1).strftime("%B %Y")
        canv.setFont("Helvetica-Bold", 15)
        canv.drawString(0.6 * inch, height - 0.6 * inch, f"Assistant Schedule — {month_title}")
        canv.setFont("Helvetica", 9)
        canv.drawString(0.6 * inch, height - 0.85 * inch, "Open days are labeled 'Open'.")

        left = 0.45 * inch
        right = width - 0.45 * inch
        top = height - 1.1 * inch
        bottom = 0.45 * inch

        grid_w = right - left
        grid_h = top - bottom
        cols = 7
        rows = max(len(weeks) + 1, 2)  # +1 header row
        cell_w = grid_w / cols
        cell_h = grid_h / rows

        day_headers = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        canv.setFont("Helvetica-Bold", 9)
        for c in range(cols):
            x = left + c * cell_w
            y = top - cell_h
            canv.rect(x, y, cell_w, cell_h, stroke=1, fill=0)
            canv.drawString(x + 4, y + cell_h - 12, day_headers[c])

        for r, week_data in enumerate(weeks, start=1):
            y = top - (r + 1) * cell_h
            for c in range(cols):
                x = left + c * cell_w
                day = week_data[c]
                canv.rect(x, y, cell_w, cell_h, stroke=1, fill=0)

                if not day:
                    continue

                canv.setFont("Helvetica-Bold", 9)
                canv.drawString(x + 4, y + cell_h - 12, str(day["day"]))

                canv.setFont("Helvetica", 7)
                status = "Open" if day["is_operating"] else "Closed"
                canv.drawRightString(x + cell_w - 4, y + cell_h - 12, status)

                lines = [a[1] for a in day["assistants"]]
                max_lines = max(int((cell_h - 18) // 9), 1)
                if len(lines) > max_lines:
                    lines = lines[: max_lines - 1] + [f"+{len(day['assistants']) - (max_lines - 1)} more"]

                ty = y + cell_h - 22
                canv.setFont("Helvetica", 7)
                for line in lines:
                    if ty < y + 3:
                        break
                    canv.drawString(x + 4, ty, str(line)[:26])
                    ty -= 8

        canv.save()
        buffer.seek(0)
        filename = f"assistant_schedule_{year:04d}_{month:02d}.pdf"
        return send_file(buffer, mimetype="application/pdf", as_attachment=True, download_name=filename)
