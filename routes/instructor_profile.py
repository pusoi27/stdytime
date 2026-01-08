# routes/instructor_profile.py
from flask import render_template, request, redirect, url_for, flash, jsonify
from modules import instructor_profile_manager


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
                    center_location
                )
                flash("Instructor profile updated successfully.", "success")
            else:
                # Create new profile
                instructor_profile_manager.create_instructor_profile(
                    name,
                    email,
                    phone,
                    center_location
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
