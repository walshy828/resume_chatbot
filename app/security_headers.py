"""
Security headers middleware for Flask application.
"""
from flask import Flask


def init_security_headers(app: Flask):
    """
    Initialize security headers for the Flask application.
    
    Adds the following security headers to all responses:
    - Content-Security-Policy
    - X-Content-Type-Options
    - X-Frame-Options
    - X-XSS-Protection
    - Referrer-Policy
    - Permissions-Policy
    """
    
    @app.after_request
    def add_security_headers(response):
        """Add security headers to every response."""
        
        # Content Security Policy
        # Allow self, inline styles (for dynamic UI), and specific external resources
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.socket.io https://unpkg.com https://cdn.tailwindcss.com https://cdn.ckeditor.com https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.tailwindcss.com; "
            "font-src 'self' https://fonts.gstatic.com https://r2cdn.perplexity.ai data:; "
            "img-src 'self' data: https:; "
            "connect-src 'self' wss: ws: https://unpkg.com https://cdn.socket.io https://cdnjs.cloudflare.com https://cdn.jsdelivr.net; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        response.headers['Content-Security-Policy'] = csp
        
        # Prevent MIME type sniffing
        response.headers['X-Content-Type-Options'] = 'nosniff'
        
        # Prevent clickjacking
        response.headers['X-Frame-Options'] = 'DENY'
        
        # XSS Protection (legacy, but still good to include)
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        # Referrer Policy
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Permissions Policy (formerly Feature Policy)
        response.headers['Permissions-Policy'] = (
            'geolocation=(), '
            'microphone=(), '
            'camera=(), '
            'payment=(), '
            'usb=(), '
            'magnetometer=(), '
            'gyroscope=(), '
            'accelerometer=()'
        )
        
        # Only add HSTS in production with HTTPS
        if app.config.get('SESSION_COOKIE_SECURE', False):
            # HTTP Strict Transport Security (1 year)
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        return response
    
    return app

