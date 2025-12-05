from functools import wraps
from flask import redirect, url_for, flash
from flask_login import LoginManager, current_user
from app.models import User, db

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
        return f(*args, **kwargs)
    return decorated_function

def init_default_admin(app):
    """Initialize default admin user if none exists"""
    with app.app_context():
        # Check if admin user already exists
        admin_username = app.config['ADMIN_USERNAME']
        if not User.query.filter_by(username=admin_username).first():
            admin = User(username=admin_username)
            admin.set_password(app.config['ADMIN_PASSWORD'])
            db.session.add(admin)
            db.session.commit()
            print(f"Created default admin user: {admin_username}")
