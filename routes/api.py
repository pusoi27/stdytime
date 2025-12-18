# routes/api.py
from flask import jsonify, request
from modules import student_manager, assistant_manager, timer_manager
from modules.database import DB_PATH
from modules.utils import duration_seconds, time_now
from datetime import datetime
import sqlite3

# Global caches for performance (UI helpers)
active_students_cache = {}  # sid -> student dict (only active)
checked_out_cache = {}
selected_assistants_cache = []  # List of dicts for assistants on duty (legacy; DB is source of truth)

def register_api_routes(app):
    """Register API/AJAX routes."""
    
    @app.route("/api/students/list")
    def api_students_list():
        """Return students with computed status: registered | active | checked."""
        students = student_manager.get_all_students()

        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            active_rows = c.execute(
                "SELECT student_id, start_time FROM sessions WHERE end_time IS NULL"
            ).fetchall()
            active_map = {sid: start for sid, start in active_rows}

            today = datetime.now().date().isoformat()
            today_rows = c.execute(
                "SELECT student_id, SUM(duration) FROM sessions WHERE DATE(start_time)=? AND end_time IS NOT NULL GROUP BY student_id",
                (today,),
            ).fetchall()
            today_sum = {sid: total or 0 for sid, total in today_rows}

            latest_rows = c.execute(
                "SELECT student_id, duration FROM sessions WHERE end_time IS NOT NULL ORDER BY id DESC"
            ).fetchall()
            latest_duration = {}
            for sid, dur in latest_rows:
                if sid not in latest_duration:
                    latest_duration[sid] = dur

        active_students_cache.clear()
        result = []
        for s in students:
            sid = s[0]
            status = "registered"
            start_time = None
            total_seconds = None
            dur = latest_duration.get(sid)

            if sid in active_map:
                status = "active"
                start_time = active_map[sid]
            elif sid in today_sum:
                status = "checked"
                total_seconds = today_sum.get(sid, 0)

            student_dict = {
                "id": sid,
                "name": s[1],
                "subject": s[2],
                "level": s[3],
                "email": s[4],
                "phone": s[5],
                "photo": s[6] if len(s) > 6 else None,
                "active": s[7] if len(s) > 7 else 0,
                "book_loaned": s[8] if len(s) > 8 else 0,
                "paper_ws": s[9] if len(s) > 9 else 0,
                "status": status,
                "start_time": start_time,
                "total_seconds": total_seconds,
                "duration": dur,
            }

            if status == "active":
                active_students_cache[sid] = student_dict

            result.append(student_dict)
        return jsonify(result)

    @app.route("/api/students/start/<int:sid>", methods=["POST"])
    def api_students_start(sid):
        timer_manager.start_session(sid)
        return jsonify({"status": "started"})

    @app.route("/api/students/stop/<int:sid>", methods=["POST"])
    def api_students_stop(sid):
        timer_manager.stop_session(sid)
        return jsonify({"status": "stopped"})

    @app.route("/api/sessions/active")
    def api_sessions_active():
        """Return only currently active sessions; auto-stop any over 2h."""
        now_str = time_now()
        today = datetime.now().date().isoformat()
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            active_rows = c.execute(
                "SELECT student_id, start_time FROM sessions WHERE end_time IS NULL AND DATE(start_time)=?",
                (today,)
            ).fetchall()

        # Enforce 2h limit
        for sid, start in list(active_rows):
            try:
                if duration_seconds(start, now_str) >= 7200:
                    timer_manager.stop_session(sid)
            except Exception:
                continue

        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            active_rows = c.execute(
                "SELECT student_id, start_time FROM sessions WHERE end_time IS NULL AND DATE(start_time)=?",
                (today,)
            ).fetchall()

        students = {s[0]: s for s in student_manager.get_all_students()}
        result = []
        active_students_cache.clear()
        for sid, start in active_rows:
            s = students.get(sid)
            if not s:
                continue
            student_dict = {
                "id": sid,
                "name": s[1],
                "subject": s[2],
                "level": s[3],
                "photo": s[6] if len(s) > 6 else None,
                "book_loaned": s[8] if len(s) > 8 else 0,
                "paper_ws": s[9] if len(s) > 9 else 0,
                "start_time": start,
            }
            active_students_cache[sid] = student_dict
            result.append(student_dict)

        return jsonify(result)

    @app.route("/api/sessions/clear", methods=["POST"])
    def api_sessions_clear():
        """Stop all active sessions (DB + cache) and clear timer buffers."""
        try:
            # Hard delete ALL session rows to ensure clean slate
            closed_rows = timer_manager.delete_all_sessions()
            ended = []
            active_students_cache.clear()
            return jsonify({"stopped": ended, "closed_rows": closed_rows}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/sessions/toggle", methods=["POST"])
    def api_sessions_toggle():
        """Toggle a student's session: start if not active, stop if active.
        Request JSON: {"student_id": <id>}
        Returns: {"action": "started"|"checked_out", "student_id": <id>, "name": <name>}
        """
        try:
            data = request.get_json() or {}
            student_id = data.get("student_id")
            
            if not student_id:
                return jsonify({"error": "Missing student_id"}), 400
            
            # Get student info
            student = student_manager.get_student(student_id)
            if not student:
                return jsonify({"error": "Student not found"}), 404
            
            student_name = student[1]  # name is second field
            
            # Check if student has an open session
            with sqlite3.connect(DB_PATH) as conn:
                c = conn.cursor()
                open_session = c.execute(
                    "SELECT id FROM sessions WHERE student_id=? AND end_time IS NULL LIMIT 1",
                    (student_id,)
                ).fetchone()
            
            if open_session:
                # Stop the session (check out)
                timer_manager.stop_session(student_id)
                active_students_cache.pop(student_id, None)
                return jsonify({
                    "action": "checked_out",
                    "student_id": student_id,
                    "name": student_name
                }), 200
            else:
                # Start a new session
                timer_manager.start_session(student_id)
                return jsonify({
                    "action": "started",
                    "student_id": student_id,
                    "name": student_name
                }), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/attendance/reset_today", methods=["POST"])
    def api_attendance_reset_today():
        """Reset today's attendance data and clear any active class timers.
        - Stops all active sessions
        - Deletes sessions whose start_time is today
        - Clears active cache for dashboard columns
        """
        # Stop any active timers first
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            open_ids = c.execute(
                "SELECT DISTINCT student_id FROM sessions WHERE end_time IS NULL"
            ).fetchall()
        for row in open_ids:
            timer_manager.stop_session(row[0])

        timer_manager.stop_all_active()

        today = datetime.now().date().isoformat()
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute("DELETE FROM sessions WHERE DATE(start_time)=?", (today,))
            deleted = c.rowcount
            conn.commit()

        active_students_cache.clear()
        return jsonify({"deleted": deleted, "date": today})

    @app.route("/api/assistants/list")
    def api_assistants_list():
        """Return all assistants with on-duty status and start time.
        DB is the source of truth: an "open" assistant_sessions row (end_time NULL) => on duty.
        """
        assistants = assistant_manager.get_all_assistants()
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            open_rows = c.execute(
                "SELECT assistant_id, start_time FROM assistant_sessions WHERE end_time IS NULL"
            ).fetchall()
        open_map = {aid: start for (aid, start) in open_rows}
        result = []
        for a in assistants:
            aid = a[0]
            result.append(
                dict(
                    id=aid,
                    name=a[1],
                    role=a[2] if len(a) > 2 else "",
                    email=a[3] if len(a) > 3 else "",
                    phone=a[4] if len(a) > 4 else "",
                    on_duty=aid in open_map,
                    start_time=open_map.get(aid),
                )
            )
        return jsonify(result)

    @app.route("/api/assistants/select/<int:aid>", methods=["POST"])
    def api_assistants_select(aid):
        """Toggle assistant on/off duty with payroll time tracking.
        Uses DB open-row semantics so checkout works reliably (even after restarts).
        """
        assistant = assistant_manager.get_assistant(aid)
        if not assistant:
            return jsonify({"error": "Assistant not found"}), 404

        now = datetime.now()
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            open_row = cur.execute(
                "SELECT id, start_time FROM assistant_sessions WHERE assistant_id=? AND end_time IS NULL ORDER BY id DESC LIMIT 1",
                (aid,)
            ).fetchone()

            if open_row:
                sess_id, start_iso = open_row
                try:
                    start_dt = datetime.fromisoformat(start_iso) if start_iso else None
                except Exception:
                    start_dt = None
                duration = int((now - start_dt).total_seconds()) if start_dt else 0
                cur.execute(
                    "UPDATE assistant_sessions SET end_time=?, duration=? WHERE id=?",
                    (now.isoformat(), duration, sess_id)
                )
                conn.commit()
                # Keep legacy cache in sync (best-effort)
                selected_assistants_cache[:] = [a for a in selected_assistants_cache if a.get("id") != aid]
                return jsonify({"success": True, "on_duty": False, "duration": duration})
            else:
                # Start new open session
                cur.execute(
                    "INSERT INTO assistant_sessions (assistant_id, start_time, end_time, duration) VALUES (?,?,NULL,NULL)",
                    (aid, now.isoformat())
                )
                conn.commit()
                # Keep legacy cache in sync (best-effort)
                selected_assistants_cache.append(dict(id=aid, name=assistant[1], role=assistant[2] if len(assistant) > 2 else "", start_time=now.isoformat()))
                return jsonify({"success": True, "on_duty": True})
