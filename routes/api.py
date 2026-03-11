# routes/api.py
from flask import jsonify, request
from modules import student_manager, assistant_manager, timer_manager, auth_manager
from modules import server_cache
from modules.database import DB_PATH
from modules.utils import duration_seconds, time_now
from datetime import datetime
import sqlite3
from routes.auth import require_login, require_admin

# Global helper cache for performance (UI helpers)


def _students_list_cache_key(owner_user_id: int) -> str:
    return f"{server_cache.STUDENTS_LIST_CACHE_KEY}:u:{owner_user_id}"


def _student_goal_cache_key(owner_user_id: int, student_id: int) -> str:
    return f"{server_cache.STUDENT_GOAL_CACHE_PREFIX}u:{owner_user_id}:{student_id}"


def _assistants_profile_cache_key(owner_user_id: int) -> str:
    return f"{server_cache.ASSISTANTS_PROFILE_LIST_CACHE_KEY}:u:{owner_user_id}"


def _assistants_duty_cache_key(owner_user_id: int) -> str:
    return f"{server_cache.ASSISTANTS_DUTY_LIST_CACHE_KEY}:u:{owner_user_id}"

def register_api_routes(app):
    """Register API/AJAX routes."""
    
    @app.route("/api/students/list")
    @require_login
    def api_students_list():
        """Return students with computed status: registered | active | checked."""
        owner_user_id = auth_manager.get_current_user_id()

        def _build_students_list_payload():
            students = student_manager.get_all_students(owner_user_id=owner_user_id)

            with sqlite3.connect(DB_PATH) as conn:
                c = conn.cursor()
                active_rows = c.execute(
                    """
                    SELECT student_id, start_time
                    FROM sessions
                    WHERE end_time IS NULL
                      AND owner_user_id = ?
                    """,
                    (owner_user_id,),
                ).fetchall()
                active_map = {sid: start for sid, start in active_rows}

                today = datetime.now().date().isoformat()
                today_rows = c.execute(
                    """
                    SELECT student_id, SUM(duration)
                    FROM sessions
                    WHERE DATE(start_time)=?
                      AND end_time IS NOT NULL
                      AND owner_user_id = ?
                    GROUP BY student_id
                    """,
                    (today, owner_user_id),
                ).fetchall()
                today_sum = {sid: total or 0 for sid, total in today_rows}

                latest_rows = c.execute(
                    """
                    SELECT student_id, duration
                    FROM sessions
                    WHERE end_time IS NOT NULL
                      AND owner_user_id = ?
                    ORDER BY id DESC
                    """,
                    (owner_user_id,),
                ).fetchall()
                latest_duration = {}
                for sid, dur in latest_rows:
                    if sid not in latest_duration:
                        latest_duration[sid] = dur

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
                    "active": s[7] if len(s) > 7 else 0,
                    "book_loaned": s[8] if len(s) > 8 else 0,
                    "paper_ws": s[9] if len(s) > 9 else 0,
                    "day1": s[17] if len(s) > 17 else None,
                    "day2": s[19] if len(s) > 19 else None,
                    "day1_time": s[18] if len(s) > 18 else None,
                    "day2_time": s[20] if len(s) > 20 else None,
                    "status": status,
                    "start_time": start_time,
                    "total_seconds": total_seconds,
                    "duration": dur,
                }
                result.append(student_dict)
            return result

        result = server_cache.get_or_set(
            _students_list_cache_key(owner_user_id),
            _build_students_list_payload,
            policy="checkin",
        )

        return jsonify(result)

    @app.route("/api/students/profile-goals/<int:sid>")
    @require_login
    def api_student_profile_goals(sid):
        """Return static student profile/goals payload with long-lived cache policy."""
        owner_user_id = auth_manager.get_current_user_id()
        cache_key = _student_goal_cache_key(owner_user_id, sid)

        def _build_profile_goals_payload():
            profile = student_manager.get_student_static_profile(sid, owner_user_id=owner_user_id)
            if not profile:
                return None
            return {
                "id": profile.get("id"),
                "name": profile.get("name"),
                "subject": profile.get("subject"),
                "math_goal": profile.get("math_goal"),
                "math_ws_per_week": profile.get("math_ws_per_week"),
                "reading_goal": profile.get("reading_goal"),
                "reading_ws_per_week": profile.get("reading_ws_per_week"),
                "day1": profile.get("day1"),
                "day2": profile.get("day2"),
                "day1_time": profile.get("day1_time"),
                "day2_time": profile.get("day2_time"),
            }

        payload = server_cache.get_or_set(
            cache_key,
            _build_profile_goals_payload,
            policy="student_goal",
        )
        if payload is None:
            return jsonify({"error": "Student not found"}), 404
        return jsonify(payload)

    @app.route("/api/students/start/<int:sid>", methods=["POST"])
    @require_login
    def api_students_start(sid):
        owner_user_id = auth_manager.get_current_user_id()
        student = student_manager.get_student(sid, owner_user_id=owner_user_id)
        if not student:
            return jsonify({"error": "Student not found"}), 404
        timer_manager.start_session(sid, owner_user_id)
        server_cache.invalidate(_students_list_cache_key(owner_user_id))
        return jsonify({"status": "started"})

    @app.route("/api/students/stop/<int:sid>", methods=["POST"])
    @require_login
    def api_students_stop(sid):
        owner_user_id = auth_manager.get_current_user_id()
        student = student_manager.get_student(sid, owner_user_id=owner_user_id)
        if not student:
            return jsonify({"error": "Student not found"}), 404
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            open_row = c.execute(
                """
                SELECT id, start_time
                FROM sessions
                WHERE student_id = ?
                  AND end_time IS NULL
                  AND owner_user_id = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (sid, owner_user_id),
            ).fetchone()
            if open_row:
                sess_id, start = open_row
                end = time_now()
                try:
                    duration = duration_seconds(start, end)
                except Exception:
                    duration = 0
                c.execute(
                    "UPDATE sessions SET end_time = ?, duration = ? WHERE id = ?",
                    (end, duration, sess_id),
                )
                conn.commit()
                timer_manager.active_sessions.pop(sid, None)
        server_cache.invalidate(_students_list_cache_key(owner_user_id))
        return jsonify({"status": "stopped"})

    @app.route("/api/sessions/active")
    @require_login
    def api_sessions_active():
        """Return only currently active sessions; auto-stop any over 2h."""
        owner_user_id = auth_manager.get_current_user_id()
        now_str = time_now()
        today = datetime.now().date().isoformat()

        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            active_rows = c.execute(
                """
                SELECT student_id, start_time
                FROM sessions
                WHERE end_time IS NULL
                  AND DATE(start_time)=?
                  AND owner_user_id = ?
                """,
                (today, owner_user_id),
            ).fetchall()

        for sid, start in list(active_rows):
            try:
                if duration_seconds(start, now_str) >= 7200:
                    with sqlite3.connect(DB_PATH) as conn:
                        c = conn.cursor()
                        end = time_now()
                        try:
                            duration = duration_seconds(start, end)
                        except Exception:
                            duration = 0
                        c.execute(
                            """
                            UPDATE sessions
                            SET end_time = ?, duration = ?
                            WHERE id = (
                                SELECT id
                                FROM sessions
                                WHERE student_id = ?
                                  AND end_time IS NULL
                                  AND owner_user_id = ?
                                ORDER BY id DESC
                                LIMIT 1
                            )
                            """,
                            (end, duration, sid, owner_user_id),
                        )
                        conn.commit()
                    timer_manager.active_sessions.pop(sid, None)
            except Exception:
                continue

        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            active_rows = c.execute(
                """
                SELECT student_id, start_time
                FROM sessions
                WHERE end_time IS NULL
                  AND DATE(start_time)=?
                  AND owner_user_id = ?
                """,
                (today, owner_user_id),
            ).fetchall()

        students = {s[0]: s for s in student_manager.get_all_students(owner_user_id=owner_user_id)}
        result = []
        for sid, start in active_rows:
            s = students.get(sid)
            if not s:
                continue
            result.append({
                "id": sid,
                "name": s[1],
                "subject": s[2],
                "level": s[3],
                "book_loaned": s[8] if len(s) > 8 else 0,
                "paper_ws": s[9] if len(s) > 9 else 0,
                "start_time": start,
            })

        return jsonify(result)

    @app.route("/api/sessions/clear", methods=["POST"])
    @require_admin
    def api_sessions_clear():
        """Stop all active sessions (DB + cache) and clear timer buffers."""
        owner_user_id = auth_manager.get_current_user_id()
        try:
            with sqlite3.connect(DB_PATH) as conn:
                c = conn.cursor()
                c.execute("DELETE FROM sessions WHERE owner_user_id = ?", (owner_user_id,))
                closed_rows = c.rowcount
                conn.commit()
            ended = []
            server_cache.invalidate(_students_list_cache_key(owner_user_id))
            return jsonify({"stopped": ended, "closed_rows": closed_rows}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/sessions/toggle", methods=["POST"])
    @require_login
    def api_sessions_toggle():
        """Toggle a student's session: start if not active, stop if active.
        Request JSON: {"student_id": <id>}
        Returns: {"action": "started"|"checked_out", "student_id": <id>, "name": <name>}
        Validation: Student must have at least one goal (Math or Reading) to start session.
        """
        try:
            owner_user_id = auth_manager.get_current_user_id()
            data = request.get_json() or {}
            student_id = data.get("student_id")
            
            if not student_id:
                return jsonify({"error": "Missing student_id"}), 400
            
            # Get student info
            student = student_manager.get_student(student_id, owner_user_id=owner_user_id)
            if not student:
                return jsonify({"error": "Student not found"}), 404
            
            student_name = student[1]  # name is at index 1
            # Get goals from student tuple: indices after removal of 'photo' field
            # Tuple: (id, name, subject, email, phone, active, book_loaned, paper_ws, math_goal, math_worksheets_per_week, reading_goal, reading_worksheets_per_week)
            math_goal = student[8] if len(student) > 8 else None
            reading_goal = student[10] if len(student) > 10 else None
            
            # Check if student has goals (both goals cannot be blank)
            # A goal is "filled" if it's not None and has non-whitespace text
            math_filled = bool(math_goal and str(math_goal).strip())
            reading_filled = bool(reading_goal and str(reading_goal).strip())
            
            if not (math_filled or reading_filled):
                return jsonify({
                    "error": f"⚠️ {student_name} cannot start a session. Math Goal and Reading Goal are both blank. Please set at least one goal (Math or Reading)."
                }), 400
            
            # Check if student has an open session
            with sqlite3.connect(DB_PATH) as conn:
                c = conn.cursor()
                open_session = c.execute(
                    "SELECT id FROM sessions WHERE student_id=? AND end_time IS NULL AND owner_user_id = ? LIMIT 1",
                    (student_id, owner_user_id)
                ).fetchone()
            
            if open_session:
                # Stop the session (check out)
                with sqlite3.connect(DB_PATH) as conn:
                    c = conn.cursor()
                    open_row = c.execute(
                        """
                        SELECT id, start_time
                        FROM sessions
                        WHERE student_id = ?
                          AND end_time IS NULL
                          AND owner_user_id = ?
                        ORDER BY id DESC
                        LIMIT 1
                        """,
                        (student_id, owner_user_id),
                    ).fetchone()
                    if open_row:
                        sess_id, start = open_row
                        end = time_now()
                        try:
                            duration = duration_seconds(start, end)
                        except Exception:
                            duration = 0
                        c.execute(
                            "UPDATE sessions SET end_time = ?, duration = ? WHERE id = ?",
                            (end, duration, sess_id),
                        )
                        conn.commit()
                server_cache.invalidate(_students_list_cache_key(owner_user_id))
                return jsonify({
                    "action": "checked_out",
                    "student_id": student_id,
                    "name": student_name
                }), 200
            else:
                # Start a new session
                timer_manager.start_session(student_id, owner_user_id)
                server_cache.invalidate(_students_list_cache_key(owner_user_id))
                return jsonify({
                    "action": "started",
                    "student_id": student_id,
                    "name": student_name
                }), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/attendance/reset_today", methods=["POST"])
    @require_admin
    def api_attendance_reset_today():
        """Reset today's attendance data and clear any active class timers.
        - Stops all active sessions
        - Deletes sessions whose start_time is today
        - Clears active cache for dashboard columns
        """
        owner_user_id = auth_manager.get_current_user_id()
        # Stop any active timers first
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            open_rows = c.execute(
                "SELECT id, student_id, start_time FROM sessions WHERE end_time IS NULL AND owner_user_id = ?",
                (owner_user_id,)
            ).fetchall()
            end = time_now()
            for sess_id, sid, start in open_rows:
                try:
                    duration = duration_seconds(start, end)
                except Exception:
                    duration = 0
                c.execute(
                    "UPDATE sessions SET end_time = ?, duration = ? WHERE id = ?",
                    (end, duration, sess_id),
                )
            conn.commit()

        today = datetime.now().date().isoformat()
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute("DELETE FROM sessions WHERE DATE(start_time)=? AND owner_user_id = ?", (today, owner_user_id))
            deleted = c.rowcount
            conn.commit()

        server_cache.invalidate(_students_list_cache_key(owner_user_id))
        return jsonify({"deleted": deleted, "date": today})

    @app.route("/api/assistants/profiles")
    @require_login
    def api_assistants_profiles():
        """Return assistant static profile list with longer TTL lane."""
        owner_user_id = auth_manager.get_current_user_id()

        def _build_profiles_payload():
            rows = assistant_manager.get_all_assistants(owner_user_id=owner_user_id)
            return [
                dict(
                    id=a[0],
                    name=a[1],
                    role=a[2] if len(a) > 2 else "",
                    email=a[3] if len(a) > 3 else "",
                    phone=a[4] if len(a) > 4 else "",
                )
                for a in rows
            ]

        payload = server_cache.get_or_set(
            _assistants_profile_cache_key(owner_user_id),
            _build_profiles_payload,
            policy="assistant_profile",
        )
        return jsonify(payload)

    @app.route("/api/assistants/list")
    @require_login
    def api_assistants_list():
        """Return all assistants with on-duty status and start time.
        DB is the source of truth: an "open" assistant_sessions row (end_time NULL) => on duty.
        """
        owner_user_id = auth_manager.get_current_user_id()

        def _build_duty_payload():
            assistants = assistant_manager.get_all_assistants(owner_user_id=owner_user_id)
            with sqlite3.connect(DB_PATH) as conn:
                c = conn.cursor()
                open_rows = c.execute(
                    "SELECT assistant_id, start_time FROM assistant_sessions WHERE end_time IS NULL AND owner_user_id = ?",
                    (owner_user_id,),
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
            return result

        payload = server_cache.get_or_set(
            _assistants_duty_cache_key(owner_user_id),
            _build_duty_payload,
            policy="assistant_duty",
        )
        return jsonify(payload)

    @app.route("/api/assistants/select/<int:aid>", methods=["POST"])
    @require_login
    def api_assistants_select(aid):
        """Toggle assistant on/off duty with payroll time tracking.
        Uses DB open-row semantics so checkout works reliably (even after restarts).
        """
        owner_user_id = auth_manager.get_current_user_id()
        assistant = assistant_manager.get_assistant(aid, owner_user_id=owner_user_id)
        if not assistant:
            return jsonify({"error": "Assistant not found"}), 404

        now = datetime.now()
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            open_row = cur.execute(
                "SELECT id, start_time FROM assistant_sessions WHERE assistant_id=? AND end_time IS NULL AND owner_user_id = ? ORDER BY id DESC LIMIT 1",
                (aid, owner_user_id)
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
                server_cache.invalidate(_assistants_duty_cache_key(owner_user_id))
                return jsonify({"success": True, "on_duty": False, "duration": duration})
            else:
                # Start new open session
                cur.execute(
                    "INSERT INTO assistant_sessions (assistant_id, start_time, end_time, duration, owner_user_id) VALUES (?,?,NULL,NULL,?)",
                    (aid, now.isoformat(), owner_user_id)
                )
                conn.commit()
                server_cache.invalidate(_assistants_duty_cache_key(owner_user_id))
                return jsonify({"success": True, "on_duty": True})
