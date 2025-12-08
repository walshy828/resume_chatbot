import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Application configuration"""
    
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URI', 'sqlite:///chatbot.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Google Gemini
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
    GEMINI_API_MODEL = os.getenv('GEMINI_API_MODEL', 'gemini-2.5-flash-lite')
    
    # File upload settings
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16MB max file size
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
    RESUME_FOLDER = os.path.join(UPLOAD_FOLDER, 'resumes')
    ICONS_FOLDER = os.path.join(UPLOAD_FOLDER, 'icons')
    ALLOWED_RESUME_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt'}
    ALLOWED_ICON_EXTENSIONS = {'png', 'jpg', 'jpeg', 'svg', 'webp'}
    
    # Admin credentials (from environment variables)
    ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
    ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin')
    
    # Default admin credentials
    DEFAULT_ADMIN_USERNAME = os.getenv('DEFAULT_ADMIN_USERNAME', 'admin')
    DEFAULT_ADMIN_PASSWORD = os.getenv('DEFAULT_ADMIN_PASSWORD', 'changeme123')
    
    # Session settings
    PERMANENT_SESSION_LIFETIME = int(os.getenv('SESSION_LIFETIME', 3600))  # 1 hour default
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Strict'  # Changed from 'Lax' for better security
    SESSION_REFRESH_EACH_REQUEST = True
    
    # CSRF Protection
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None  # Use session lifetime
    WTF_CSRF_SSL_STRICT = SESSION_COOKIE_SECURE
    WTF_CSRF_CHECK_DEFAULT = False  # Don't check by default, we'll use decorators

    
    # CORS Configuration
    CORS_ALLOWED_ORIGINS = os.getenv('CORS_ALLOWED_ORIGINS', 'http://localhost:8080,http://127.0.0.1:8080,http://localhost:8181,http://127.0.0.1:8181').split(',')

    CORS_ALLOW_CREDENTIALS = True
    
    # Rate Limiting
    RATELIMIT_STORAGE_URL = os.getenv('RATELIMIT_STORAGE_URL', 'memory://')
    RATELIMIT_STRATEGY = 'fixed-window'
    
    # Security Settings
    BCRYPT_LOG_ROUNDS = int(os.getenv('BCRYPT_LOG_ROUNDS', 14))
    MAX_LOGIN_ATTEMPTS = int(os.getenv('MAX_LOGIN_ATTEMPTS', 5))
    ACCOUNT_LOCKOUT_DURATION = int(os.getenv('ACCOUNT_LOCKOUT_DURATION', 30))  # minutes

