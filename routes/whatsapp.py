"""
WhatsApp Routes Module for KumoClock
Handles WhatsApp messaging endpoints
Version: 01.00.00
"""

from flask import Blueprint, render_template, request, jsonify
import sqlite3
from modules.database import DB_PATH
from modules.whatsapp_manager import WhatsAppManager
from modules import student_manager, auth_manager
from routes.auth import require_login


def register_whatsapp_routes(app):
    """Register all WhatsApp-related routes"""
    
    # Initialize WhatsApp manager
    wa_manager = WhatsAppManager()
    
    @app.route('/whatsapp')
    @require_login
    def whatsapp_dashboard():
        """WhatsApp messaging dashboard"""
        return render_template('whatsapp/dashboard.html', 
                             is_configured=wa_manager.is_configured())
    
    @app.route('/whatsapp/students')
    @require_login
    def whatsapp_students():
        """Send WhatsApp to students page"""
        owner_user_id = auth_manager.get_current_user_id()
        students = student_manager.get_all_students(owner_user_id=owner_user_id)
        return render_template('whatsapp/students.html', students=students)
    
    @app.route('/whatsapp/staff')
    @require_login
    def whatsapp_staff():
        """Send WhatsApp to staff page"""
        owner_user_id = auth_manager.get_current_user_id()
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, name, role, whatsapp FROM staff WHERE owner_user_id = ? ORDER BY name",
                (owner_user_id,),
            )
            staff = cursor.fetchall()
        return render_template('whatsapp/staff.html', staff=staff)
    
    @app.route('/whatsapp/broadcast')
    @require_login
    def whatsapp_broadcast():
        """Broadcast WhatsApp to multiple recipients"""
        return render_template('whatsapp/broadcast.html')
    
    # ================================================================
    #  API Endpoints
    # ================================================================
    
    @app.route('/api/whatsapp/status', methods=['GET'])
    @require_login
    def api_whatsapp_status():
        """Check WhatsApp configuration status"""
        return jsonify({
            'configured': wa_manager.is_configured(),
            'message': 'WhatsApp is configured and ready' if wa_manager.is_configured() 
                      else 'WhatsApp is not configured. Please set environment variables.'
        })
    
    @app.route('/api/whatsapp/send-to-student', methods=['POST'])
    @require_login
    def api_send_to_student():
        """Send WhatsApp message to a student"""
        owner_user_id = auth_manager.get_current_user_id()
        if not wa_manager.is_configured():
            return jsonify({'success': False, 'error': 'WhatsApp not configured'}), 400
        
        data = request.get_json(silent=True) or {}
        student_id = data.get('student_id')
        message = data.get('message', '').strip()
        
        if not student_id or not message:
            return jsonify({'success': False, 'error': 'Missing student_id or message'}), 400
        
        # Get student details
        student = student_manager.get_student(student_id, owner_user_id=owner_user_id)
        if not student:
            return jsonify({'success': False, 'error': 'Student not found'}), 404
        
        # Extract WhatsApp number from student record (column index varies, check name at index 1)
        student_name = student[1]
        student_whatsapp = student[5] if len(student) > 5 else None  # phone column
        
        # Prefer whatsapp column if it exists (check if table has it)
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(students)")
            cols = {r[1]: r[0] for r in cursor.fetchall()}
            if 'whatsapp' in cols:
                cursor.execute(
                    "SELECT whatsapp FROM students WHERE id=? AND owner_user_id = ?",
                    (student_id, owner_user_id),
                )
                row = cursor.fetchone()
                if row:
                    student_whatsapp = row[0]
        
        result = wa_manager.send_to_student(student_name, student_whatsapp, message)
        return jsonify(result), 200 if result['success'] else 400
    
    @app.route('/api/whatsapp/send-to-staff', methods=['POST'])
    @require_login
    def api_send_to_staff():
        """Send WhatsApp message to a staff member"""
        owner_user_id = auth_manager.get_current_user_id()
        if not wa_manager.is_configured():
            return jsonify({'success': False, 'error': 'WhatsApp not configured'}), 400
        
        data = request.get_json(silent=True) or {}
        staff_id = data.get('staff_id')
        message = data.get('message', '').strip()
        
        if not staff_id or not message:
            return jsonify({'success': False, 'error': 'Missing staff_id or message'}), 400
        
        # Get staff details
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name, whatsapp FROM staff WHERE id=? AND owner_user_id = ?",
                (staff_id, owner_user_id),
            )
            staff = cursor.fetchone()
        
        if not staff:
            return jsonify({'success': False, 'error': 'Staff member not found'}), 404
        
        staff_name, staff_whatsapp = staff[0], staff[1]
        result = wa_manager.send_to_staff(staff_name, staff_whatsapp, message)
        return jsonify(result), 200 if result['success'] else 400
    
    @app.route('/api/whatsapp/broadcast-students', methods=['POST'])
    @require_login
    def api_broadcast_to_students():
        """Broadcast WhatsApp to multiple students"""
        owner_user_id = auth_manager.get_current_user_id()
        if not wa_manager.is_configured():
            return jsonify({'success': False, 'error': 'WhatsApp not configured'}), 400
        
        data = request.get_json(silent=True) or {}
        student_ids = data.get('student_ids', [])
        message = data.get('message', '').strip()
        
        if not student_ids or not message:
            return jsonify({'success': False, 'error': 'Missing student_ids or message'}), 400
        
        # Get student details
        recipients = []
        for sid in student_ids:
            student = student_manager.get_student(sid, owner_user_id=owner_user_id)
            if student:
                student_name = student[1]
                # Get WhatsApp from database
                with sqlite3.connect(DB_PATH) as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT whatsapp FROM students WHERE id=? AND owner_user_id = ?",
                        (sid, owner_user_id),
                    )
                    row = cursor.fetchone()
                    student_whatsapp = row[0] if row and row[0] else student[5]  # fallback to phone
                
                recipients.append({
                    'name': student_name,
                    'whatsapp': student_whatsapp
                })
        
        if not recipients:
            return jsonify({'success': False, 'error': 'No valid recipients found'}), 400
        
        result = wa_manager.send_bulk_messages(recipients, message)
        return jsonify(result), 200 if result['success'] else 400
    
    @app.route('/api/whatsapp/broadcast-staff', methods=['POST'])
    @require_login
    def api_broadcast_to_staff():
        """Broadcast WhatsApp to multiple staff members"""
        owner_user_id = auth_manager.get_current_user_id()
        if not wa_manager.is_configured():
            return jsonify({'success': False, 'error': 'WhatsApp not configured'}), 400
        
        data = request.get_json(silent=True) or {}
        staff_ids = data.get('staff_ids', [])
        message = data.get('message', '').strip()
        
        if not staff_ids or not message:
            return jsonify({'success': False, 'error': 'Missing staff_ids or message'}), 400
        
        # Get staff details
        recipients = []
        for sid in staff_ids:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT name, whatsapp FROM staff WHERE id=? AND owner_user_id = ?",
                    (sid, owner_user_id),
                )
                staff = cursor.fetchone()
                if staff:
                    recipients.append({
                        'name': staff[0],
                        'whatsapp': staff[1]
                    })
        
        if not recipients:
            return jsonify({'success': False, 'error': 'No valid recipients found'}), 400
        
        result = wa_manager.send_bulk_messages(recipients, message)
        return jsonify(result), 200 if result['success'] else 400
    
    @app.route('/api/whatsapp/update-student-whatsapp', methods=['POST'])
    @require_login
    def api_update_student_whatsapp():
        """Update student WhatsApp number"""
        owner_user_id = auth_manager.get_current_user_id()
        data = request.get_json(silent=True) or {}
        student_id = data.get('student_id')
        whatsapp = data.get('whatsapp', '').strip()
        
        if not student_id:
            return jsonify({'success': False, 'error': 'Missing student_id'}), 400
        
        # Validate phone number format
        if whatsapp and not wa_manager.validate_phone_number(whatsapp):
            return jsonify({'success': False, 'error': 'Invalid phone number format'}), 400
        
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE students SET whatsapp=? WHERE id=? AND owner_user_id = ?",
                    (whatsapp, student_id, owner_user_id),
                )
                conn.commit()
            
            return jsonify({'success': True, 'message': 'WhatsApp number updated successfully'})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/whatsapp/update-staff-whatsapp', methods=['POST'])
    @require_login
    def api_update_staff_whatsapp():
        """Update staff WhatsApp number"""
        owner_user_id = auth_manager.get_current_user_id()
        data = request.get_json(silent=True) or {}
        staff_id = data.get('staff_id')
        whatsapp = data.get('whatsapp', '').strip()
        
        if not staff_id:
            return jsonify({'success': False, 'error': 'Missing staff_id'}), 400
        
        # Validate phone number format
        if whatsapp and not wa_manager.validate_phone_number(whatsapp):
            return jsonify({'success': False, 'error': 'Invalid phone number format'}), 400
        
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE staff SET whatsapp=? WHERE id=? AND owner_user_id = ?",
                    (whatsapp, staff_id, owner_user_id),
                )
                conn.commit()
            
            return jsonify({'success': True, 'message': 'WhatsApp number updated successfully'})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
