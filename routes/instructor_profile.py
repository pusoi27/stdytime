# routes/instructor_profile.py
from flask import render_template, request, redirect, url_for, flash, jsonify
from modules import instructor_profile_manager, student_manager
from datetime import datetime


def register_instructor_profile_routes(app):
    """Register instructor profile CRUD routes."""
    
    @app.route("/instructor/profile")
    def instructor_profile():
        """Display the instructor profile page"""
        profile = instructor_profile_manager.get_instructor_profile()
        return render_template("instructor_profile.html", profile=profile)

    @app.route("/instructor/profile/edit", methods=["GET", "POST"])
    def instructor_profile_edit():
        """Edit or create instructor profile"""
        profile = instructor_profile_manager.get_instructor_profile()
        
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip()
            phone = request.form.get("phone", "").strip()
            center_location = request.form.get("center_location", "").strip()
            center_address = request.form.get("center_address", "").strip()
            center_hours = request.form.get("center_hours", "").strip()
            
            # Collect weekly hours from separate hour and minute dropdowns
            weekly_hours = {}
            days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
            for day in days:
                # Combine hour and minute for start time
                start_hour = request.form.get(f'{day}_start_hour', '').strip()
                start_min = request.form.get(f'{day}_start_min', '').strip()
                if start_hour and start_min:
                    weekly_hours[f'{day}_start'] = f"{start_hour}:{start_min}"
                else:
                    weekly_hours[f'{day}_start'] = ''
                
                # Combine hour and minute for end time
                end_hour = request.form.get(f'{day}_end_hour', '').strip()
                end_min = request.form.get(f'{day}_end_min', '').strip()
                if end_hour and end_min:
                    weekly_hours[f'{day}_end'] = f"{end_hour}:{end_min}"
                else:
                    weekly_hours[f'{day}_end'] = ''
            
            if not name:
                flash("Instructor name is required.", "error")
                return render_template("instructor_profile_form.html", profile=profile, action="Edit" if profile else "Create")
            
            if profile:
                # Update existing profile
                instructor_profile_manager.update_instructor_profile(
                    profile['id'],
                    name,
                    email,
                    phone,
                    center_location,
                    center_address,
                    center_hours,
                    weekly_hours
                )
                flash("Instructor profile updated successfully.", "success")
            else:
                # Create new profile
                instructor_profile_manager.create_instructor_profile(
                    name,
                    email,
                    phone,
                    center_location,
                    center_address,
                    center_hours,
                    weekly_hours
                )
                flash("Instructor profile created successfully.", "success")
            
            return redirect(url_for("instructor_profile"))
        
        action = "Edit" if profile else "Create"
        return render_template("instructor_profile_form.html", profile=profile, action=action)

    @app.route("/api/instructor/profile", methods=["GET"])
    def api_get_instructor_profile():
        """API endpoint to get instructor profile (for AJAX requests)

        Always returns HTTP 200 with a `success` flag so frontend fetch won't
        throw on non-200 responses.
        """
        profile = instructor_profile_manager.get_instructor_profile()
        if profile:
            return jsonify({
                'success': True,
                'profile': profile,
            })
        return jsonify({
            'success': False,
            'profile': None,
            'error': 'Instructor profile not found'
        })

    @app.route("/instructor/calendar")
    def center_calendar():
        """Display the center calendar with student schedules"""
        profile = instructor_profile_manager.get_instructor_profile()
        students = student_manager.get_all_students()
        
        # Determine which days have class hours
        active_days = []
        day_mapping = [
            ('Monday', 'monday'),
            ('Tuesday', 'tuesday'),
            ('Wednesday', 'wednesday'),
            ('Thursday', 'thursday'),
            ('Friday', 'friday'),
            ('Saturday', 'saturday'),
            ('Sunday', 'sunday')
        ]
        
        if profile:
            for day_name, day_key in day_mapping:
                start_key = f'{day_key}_start'
                end_key = f'{day_key}_end'
                if profile.get(start_key) and profile.get(end_key):
                    active_days.append(day_name)
        
        # Build the calendar structure
        schedule = {
            'time_slots': [],
            'active_days': active_days,
            'calendar': {day: {} for day in active_days}
        }
        
        # Collect virtual students (marked as V=1)
        virtual_students = []
        
        # Get all unique time slots from instructor profile and students
        time_slots_set = set()
        
        if profile:
            days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
            for day in days:
                start_key = f'{day}_start'
                end_key = f'{day}_end'
                if profile.get(start_key) and profile.get(end_key):
                    # Generate 30-minute slots for this day
                    start_time = profile[start_key]
                    end_time = profile[end_key]
                    slots = generate_time_slots(start_time, end_time)
                    time_slots_set.update(slots)
        
        # Sort time slots
        schedule['time_slots'] = sorted(list(time_slots_set), key=lambda t: time_to_minutes(t))
        
        # Place students in calendar
        for student in students:
            student_data = {
                'id': student[0],
                'name': student[1],
                'subject': student[2] if student[2] else 'N/A',
                'email': student[4] if len(student) > 4 else '',
                'el': student[15] if len(student) > 15 else 0,
                'pi': student[16] if len(student) > 16 else 0,
                'v': student[17] if len(student) > 17 else 0,
            }
            
            # Check if student is virtual
            is_virtual = student[17] if len(student) > 17 else 0
            
            # If virtual, add to virtual students list instead of calendar
            if is_virtual:
                virtual_students.append(student_data)
                continue
            
            # Helper function to add student to a specific day/time, with optional next slot
            def add_student_to_slot(day, time_display, student_data, schedule, add_next_slot=False):
                if day not in schedule['calendar']:
                    return
                if time_display not in schedule['calendar'][day]:
                    schedule['calendar'][day][time_display] = []
                schedule['calendar'][day][time_display].append(student_data)
                
                # If S2 subject, also add to next 30-minute slot
                if add_next_slot:
                    current_minutes = time_to_minutes(time_display)
                    next_minutes = current_minutes + 30
                    next_time_display = minutes_to_time_display(next_minutes)
                    
                    if next_time_display in schedule['time_slots']:
                        if next_time_display not in schedule['calendar'][day]:
                            schedule['calendar'][day][next_time_display] = []
                        schedule['calendar'][day][next_time_display].append(student_data)
            
            # Add to Day 1
            if len(student) > 18 and student[18]:  # day1
                day1 = student[18]
                time1 = student[19] if len(student) > 19 else None
                if time1:
                    time_display = format_time_display(time1)
                    is_s2 = student[2] == 'S2'
                    add_student_to_slot(day1, time_display, student_data, schedule, add_next_slot=is_s2)
            
            # Add to Day 2
            if len(student) > 20 and student[20]:  # day2
                day2 = student[20]
                time2 = student[21] if len(student) > 21 else None
                if time2:
                    time_display = format_time_display(time2)
                    is_s2 = student[2] == 'S2'
                    add_student_to_slot(day2, time_display, student_data, schedule, add_next_slot=is_s2)
        
        total_students = len([s for s in students if (len(s) > 18 and s[18]) or (len(s) > 20 and s[20])])
        schedule['virtual_students'] = virtual_students
        
        return render_template("center_calendar.html", schedule=schedule, total_students=total_students)


def generate_time_slots(start_time, end_time):
    """Generate 30-minute time slots between start and end time"""
    slots = []
    start_minutes = time_to_minutes(start_time)
    end_minutes = time_to_minutes(end_time)
    
    current = start_minutes
    while current <= end_minutes:
        slots.append(minutes_to_time_display(current))
        current += 30
    
    return slots


def time_to_minutes(time_str):
    """Convert HH:MM or HH:MM PM to minutes since midnight"""
    if not time_str or ':' not in time_str:
        return 0
    # Remove AM/PM suffix if present
    time_str = time_str.replace(' PM', '').replace(' AM', '').strip()
    parts = time_str.split(':')
    return int(parts[0]) * 60 + int(parts[1])


def minutes_to_time_display(minutes):
    """Convert minutes to display format (12-hour PM)"""
    hour = minutes // 60
    minute = minutes % 60
    display_hour = hour if hour <= 12 else hour - 12
    if display_hour == 0:
        display_hour = 12
    return f"{display_hour}:{minute:02d} PM"


def format_time_display(time_str):
    """Format time from 24-hour to 12-hour PM format"""
    if not time_str or ':' not in time_str:
        return time_str
    parts = time_str.split(':')
    hour = int(parts[0])
    minute = parts[1]
    display_hour = hour if hour <= 12 else hour - 12
    if display_hour == 0:
        display_hour = 12
    return f"{display_hour}:{minute} PM"
