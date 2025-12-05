"""
Security logging utilities for tracking authentication and security events.
"""
import logging
from datetime import datetime
from functools import wraps
from flask import request
import os

# Configure security logger
security_logger = logging.getLogger('security')
security_logger.setLevel(logging.INFO)

# Create logs directory if it doesn't exist
log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
os.makedirs(log_dir, exist_ok=True)

# File handler for security events
security_handler = logging.FileHandler(os.path.join(log_dir, 'security.log'))
security_handler.setLevel(logging.INFO)

# Console handler for development
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.WARNING)

# Formatter
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
security_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

security_logger.addHandler(security_handler)
security_logger.addHandler(console_handler)


def get_client_ip():
    """Get client IP address from request."""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr


def log_failed_login(username, reason='Invalid credentials'):
    """Log failed login attempt."""
    ip = get_client_ip()
    user_agent = request.headers.get('User-Agent', 'Unknown')
    security_logger.warning(
        f"Failed login attempt - Username: {username}, IP: {ip}, "
        f"Reason: {reason}, User-Agent: {user_agent}"
    )


def log_successful_login(username):
    """Log successful login."""
    ip = get_client_ip()
    user_agent = request.headers.get('User-Agent', 'Unknown')
    security_logger.info(
        f"Successful login - Username: {username}, IP: {ip}, "
        f"User-Agent: {user_agent}"
    )


def log_account_locked(username):
    """Log account lockout event."""
    ip = get_client_ip()
    security_logger.warning(
        f"Account locked due to failed login attempts - Username: {username}, IP: {ip}"
    )


def log_password_change(username, changed_by=None):
    """Log password change event."""
    ip = get_client_ip()
    if changed_by and changed_by != username:
        security_logger.info(
            f"Password changed - Username: {username}, Changed by: {changed_by}, IP: {ip}"
        )
    else:
        security_logger.info(
            f"Password changed - Username: {username}, IP: {ip}"
        )


def log_user_created(username, created_by):
    """Log user creation event."""
    ip = get_client_ip()
    security_logger.info(
        f"User created - Username: {username}, Created by: {created_by}, IP: {ip}"
    )


def log_user_deleted(username, deleted_by):
    """Log user deletion event."""
    ip = get_client_ip()
    security_logger.warning(
        f"User deleted - Username: {username}, Deleted by: {deleted_by}, IP: {ip}"
    )


def log_user_updated(username, updated_by, fields_changed):
    """Log user update event."""
    ip = get_client_ip()
    security_logger.info(
        f"User updated - Username: {username}, Updated by: {updated_by}, "
        f"Fields: {', '.join(fields_changed)}, IP: {ip}"
    )


def log_unauthorized_access(endpoint, username=None):
    """Log unauthorized access attempt."""
    ip = get_client_ip()
    user_info = f"Username: {username}" if username else "Anonymous"
    security_logger.warning(
        f"Unauthorized access attempt - Endpoint: {endpoint}, {user_info}, IP: {ip}"
    )


def log_rate_limit_exceeded(endpoint, identifier):
    """Log rate limit exceeded event."""
    ip = get_client_ip()
    security_logger.warning(
        f"Rate limit exceeded - Endpoint: {endpoint}, Identifier: {identifier}, IP: {ip}"
    )


def log_suspicious_activity(description, username=None):
    """Log suspicious activity."""
    ip = get_client_ip()
    user_info = f"Username: {username}" if username else "Anonymous"
    security_logger.warning(
        f"Suspicious activity - {description}, {user_info}, IP: {ip}"
    )


def log_admin_action(action, username, details=None):
    """Log admin action."""
    ip = get_client_ip()
    detail_str = f", Details: {details}" if details else ""
    security_logger.info(
        f"Admin action - Action: {action}, User: {username}, IP: {ip}{detail_str}"
    )


def security_audit(action_description):
    """
    Decorator to automatically log security-relevant actions.
    
    Usage:
        @security_audit("User login")
        def login_view():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from flask_login import current_user
            username = current_user.username if current_user.is_authenticated else 'Anonymous'
            ip = get_client_ip()
            
            # Log the action
            security_logger.info(
                f"Security audit - Action: {action_description}, User: {username}, IP: {ip}"
            )
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator
