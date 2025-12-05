from functools import wraps
from flask import redirect, url_for, flash, request
from flask_login import LoginManager, current_user
from app.models import User, db
from app.password_validator import validate_password

login_manager = LoginManager()

@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login"""
    return User.query.get(int(user_id))

@login_manager.unauthorized_handler
def unauthorized():
    """Redirect unauthorized users to login page"""
    flash('Please log in to access this page.', 'warning')
    return redirect(url_for('admin_login'))

def admin_required(f):
    """Decorator to require admin authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('admin_login'))
        
        # Check if user is active
        if not current_user.is_active:
            flash('Your account has been deactivated. Please contact an administrator.', 'error')
            return redirect(url_for('admin_login'))
        
        # Check if password change is required
        if current_user.must_change_password and request.endpoint != 'change_password':
            flash('You must change your password before continuing.', 'warning')
            return redirect(url_for('change_password'))
        
        return f(*args, **kwargs)
    return decorated_function

def init_default_admin(app):
    """Initialize default admin user if none exists"""
    with app.app_context():
        # Check if any admin user exists
        if User.query.count() == 0:
            admin_username = app.config['DEFAULT_ADMIN_USERNAME']
            admin_password = app.config['DEFAULT_ADMIN_PASSWORD']
            
            admin = User(
                username=admin_username,
                email=None,  # No email for default admin
                must_change_password=True  # Force password change on first login
            )
            admin.set_password(admin_password)
            db.session.add(admin)
            db.session.commit()
            print(f"Created default admin user: {admin_username}")
            print(f"IMPORTANT: Change the default password immediately after first login!")

def validate_new_password(password, username=None):
    """
    Validate a new password against security requirements.
    
    Args:
        password: Password to validate
        username: Optional username to check for similarity
        
    Returns:
        Tuple of (is_valid, list_of_error_messages)
    """
    return validate_password(password, username)

