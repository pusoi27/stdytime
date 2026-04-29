"""License-aware access decorators and legacy auth redirects."""

from functools import wraps

from flask import flash, g, jsonify, redirect, request, url_for

from modules import license_manager


def _license_denied_response():
    status = g.get('license_status') or license_manager.get_license_context()
    message = status.get('message', 'A valid license is required to use Stdytime.')
    if request.path.startswith('/api/'):
        return jsonify({'error': message, 'license_status': status.get('status', 'unlicensed')}), 403

    flash(message, 'warning')
    target = 'license_expired' if status.get('status') == 'expired' else 'license_page'
    return redirect(url_for(target))


def require_login(f):
    """Decorator retained for compatibility; now requires a valid local license."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not (g.get('license_status') or {}).get('is_valid'):
            return _license_denied_response()
        return f(*args, **kwargs)
    return decorated_function


def require_admin(f):
    """Single-machine licensed installs always operate as the local owner."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not (g.get('license_status') or {}).get('is_valid'):
            return _license_denied_response()
        return f(*args, **kwargs)
    return decorated_function


def require_feature(feature):
    """Backward-compatible decorator; feature checks are currently disabled."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not (g.get('license_status') or {}).get('is_valid'):
                return _license_denied_response()
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def register_auth_routes(app):
    """Register redirects for removed multi-user auth endpoints."""

    @app.route('/auth/login', methods=['GET', 'POST'])
    @app.route('/auth/register', methods=['GET', 'POST'])
    @app.route('/auth/change-password', methods=['GET', 'POST'])
    @app.route('/auth/users', methods=['GET', 'POST'])
    def legacy_auth_redirect():
        flash('User logins were removed. This installation now uses a local license.', 'info')
        return redirect(url_for('license_page'))

    @app.route('/auth/logout', methods=['GET', 'POST'])
    def legacy_logout():
        flash('There is no logout for local licensed installs. Manage the license instead.', 'info')
        return redirect(url_for('license_page'))

    @app.route('/auth/<path:_unused>', methods=['GET', 'POST'])
    def legacy_auth_catchall(_unused):
        flash('The account-management screen was removed. Use the license screen instead.', 'info')
        return redirect(url_for('license_page'))
