"""
Rate limiting configuration for Flask application.
"""
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Initialize rate limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",  # Use Redis in production: "redis://localhost:6379"
    strategy="fixed-window"
)

# Rate limit configurations for different endpoint types
RATE_LIMITS = {
    'login': "5 per 15 minutes",
    'api': "100 per hour",
    'chat': "30 per minute",
    'upload': "10 per hour",
    'admin_action': "50 per hour"
}


def init_limiter(app):
    """Initialize rate limiter with Flask app."""
    limiter.init_app(app)
    return limiter
