"""Routes for activating and managing the local Stdytime license."""

from flask import flash, jsonify, redirect, render_template, request, url_for

from modules import license_manager
from modules.rate_limiter import limiter


def register_license_routes(app):
    """Register license activation and status routes."""

    @app.route('/license', methods=['GET'])
    def license_page():
        return render_template('license.html', license_status=license_manager.get_license_context())

    @app.route('/license/activate', methods=['POST'])
    @limiter.limit("10 per minute", error_message="Too many license activation attempts. Please wait a minute and try again.")
    def activate_license():
        license_key = request.form.get('license_key', '').strip()
        if not license_key:
            flash('Paste the license key you received after subscription payment.', 'danger')
            return redirect(url_for('license_page'))

        success, message, context = license_manager.activate_license(license_key)
        flash(message, 'success' if success else 'danger')
        if success:
            return redirect(url_for(context.get('default_home_endpoint', 'students_list')))
        return redirect(url_for('license_page'))

    @app.route('/license/remove', methods=['POST'])
    def remove_license():
        license_manager.remove_license()
        flash('The local license was removed from this machine.', 'warning')
        return redirect(url_for('license_page'))

    @app.route('/license/expired', methods=['GET'])
    def license_expired():
        return render_template('license_expired.html', license_status=license_manager.get_license_context())

    @app.route('/license/status', methods=['GET'])
    def license_status_api():
        return jsonify(license_manager.get_license_context())
