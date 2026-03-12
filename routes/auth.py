"""
routes/auth.py - Authentication routes (login, logout, register)
Handles user authentication flow and session management.
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from modules import auth_manager
from functools import wraps
from modules.rate_limiter import limiter

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


def require_login(f):
    """Decorator to require user login for protected routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        if session.get('must_change_password'):
            flash('You must set a new password before continuing.', 'warning')
            return redirect(url_for('auth.change_password'))
        return f(*args, **kwargs)
    return decorated_function


def require_admin(f):
    """Decorator to require admin role for routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        
        user = auth_manager.get_user_by_id(session['user_id'])
        if not user or not user.is_admin():
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function


@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute", error_message="Too many login attempts. Please wait a minute and try again.")
def login():
    """Handle user login. GET shows form, POST processes credentials."""
    
    # If user already logged in, redirect to dashboard
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        
        # Validate inputs
        if not email or not password:
            flash('Email and password are required.', 'danger')
            return render_template('auth/login.html', email=email)
        
        # Authenticate user
        user = auth_manager.authenticate_user(email, password)
        
        if user:
            # Store user info in session
            session['user_id'] = user.id
            session['email'] = user.email
            session['role'] = user.role
            session.permanent = True  # Session persists across browser restarts
            
            if user.must_change_password:
                session['must_change_password'] = True
                flash('Welcome! Please set a new password to continue.', 'warning')
                return redirect(url_for('auth.change_password'))
            
            flash(f'Welcome, {user.email}!', 'success')
            
            # Redirect to next page if provided, otherwise dashboard
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password.', 'danger')
            return render_template('auth/login.html', email=email)
    
    return render_template('auth/login.html')


@auth_bp.route('/logout', methods=['POST', 'GET'])
def logout():
    """Handle user logout. Clear session and redirect to login."""
    session.clear()
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('auth.login'))


@auth_bp.route('/change-password', methods=['GET', 'POST'])
def change_password():
    """Force password change for users flagged with must_change_password."""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    user_id = session['user_id']

    if request.method == 'POST':
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not new_password or not confirm_password:
            flash('Both password fields are required.', 'danger')
            return render_template('auth/change_password.html')

        if new_password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/change_password.html')

        success, message = auth_manager.update_user_password(user_id, new_password)
        if not success:
            flash(f'Could not update password: {message}', 'danger')
            return render_template('auth/change_password.html')

        auth_manager.clear_must_change_password(user_id)
        session.pop('must_change_password', None)
        flash('Password updated successfully. Welcome!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('auth/change_password.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Handle user registration (public registration enabled)."""
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')
        role = request.form.get('role', 'instructor').strip().lower()

        # Public registration defaults to non-admin roles.
        # Admins can still create admin users when logged in.
        if role not in (auth_manager.ROLE_INSTRUCTOR, auth_manager.ROLE_ASSISTANT, auth_manager.ROLE_ADMIN):
            role = auth_manager.ROLE_INSTRUCTOR
        if role == auth_manager.ROLE_ADMIN and session.get('role') != auth_manager.ROLE_ADMIN:
            role = auth_manager.ROLE_INSTRUCTOR
        
        # Validate inputs
        if not email or not password:
            flash('Email and password are required.', 'danger')
            return render_template('auth/register.html', email=email, role=role)
        
        if len(email) < 5 or '@' not in email:
            flash('Please enter a valid email address.', 'danger')
            return render_template('auth/register.html', email=email, role=role)
        
        if password != password_confirm:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/register.html', email=email, role=role)
        
        if len(password) < 8:
            flash('Password must be at least 8 characters.', 'danger')
            return render_template('auth/register.html', email=email, role=role)
        
        # Register user
        success, user_id_or_error = auth_manager.register_user(email, password, role=role)
        
        if success:
            init_ok, init_msg = auth_manager.initialize_new_user_data(user_id_or_error)
            if not init_ok:
                flash(f'Account created for {email}, but starter data setup had an issue: {init_msg}', 'warning')
            flash(f'User {email} registered successfully with role "{role}".', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash(f'Registration failed: {user_id_or_error}', 'danger')
            return render_template('auth/register.html', email=email, role=role)
    
    return render_template('auth/register.html')


@auth_bp.route('/users', methods=['GET'])
@require_admin
def list_users():
    """Admin panel: List all users."""
    users = auth_manager.list_all_users()
    return render_template('auth/users.html', users=users)


@auth_bp.route('/user/<int:user_id>/deactivate', methods=['POST'])
@require_admin
def deactivate_user(user_id):
    """Admin action: Deactivate a user."""
    
    # Prevent admin from deactivating themselves
    if user_id == session.get('user_id'):
        flash('Cannot deactivate your own account.', 'danger')
        return redirect(url_for('auth.list_users'))
    
    success, message = auth_manager.deactivate_user(user_id)
    
    if success:
        flash(f'User deactivated. Message: {message}', 'success')
    else:
        flash(f'Failed to deactivate user: {message}', 'danger')
    
    return redirect(url_for('auth.list_users'))


def register_auth_routes(app):
    """Register auth blueprint with the Flask app."""
    app.register_blueprint(auth_bp)
