from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
import bcrypt

db = SQLAlchemy()

# Association table for many-to-many relationship between profiles and resumes
profile_resumes = db.Table('profile_resumes',
    db.Column('profile_id', db.Integer, db.ForeignKey('profiles.id'), primary_key=True),
    db.Column('resume_id', db.Integer, db.ForeignKey('resumes.id'), primary_key=True)
)

class User(UserMixin, db.Model):
    """Admin user model"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Security fields
    failed_login_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime, nullable=True)
    password_changed_at = db.Column(db.DateTime, default=datetime.utcnow)
    must_change_password = db.Column(db.Boolean, default=False)
    last_login_at = db.Column(db.DateTime, nullable=True)
    last_login_ip = db.Column(db.String(45), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    
    def set_password(self, password):
        """Hash password with bcrypt and salt (14 rounds for enhanced security)"""
        salt = bcrypt.gensalt(rounds=14)  # Increased from default 12
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
        self.password_changed_at = datetime.utcnow()
    
    def check_password(self, password):
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
    
    def is_locked(self):
        """Check if account is currently locked"""
        if self.locked_until is None:
            return False
        return datetime.utcnow() < self.locked_until
    
    def lock_account(self, duration_minutes=30):
        """Lock account for specified duration"""
        from datetime import timedelta
        self.locked_until = datetime.utcnow() + timedelta(minutes=duration_minutes)
    
    def unlock_account(self):
        """Unlock account and reset failed attempts"""
        self.locked_until = None
        self.failed_login_attempts = 0
    
    def record_failed_login(self):
        """Record a failed login attempt"""
        self.failed_login_attempts += 1
        # Lock account after 5 failed attempts
        if self.failed_login_attempts >= 5:
            self.lock_account(duration_minutes=30)
    
    def record_successful_login(self, ip_address=None):
        """Record a successful login"""
        self.failed_login_attempts = 0
        self.locked_until = None
        self.last_login_at = datetime.utcnow()
        if ip_address:
            self.last_login_ip = ip_address


class ChatSession(db.Model):
    """Chat session tracking"""
    __tablename__ = 'chat_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), unique=True, nullable=False)
    ip_address = db.Column(db.String(45))  # IPv6 compatible
    location = db.Column(db.String(255))  # City, Country
    user_agent = db.Column(db.String(500))
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_activity = db.Column(db.DateTime, default=datetime.utcnow)
    message_count = db.Column(db.Integer, default=0)
    
    # Relationship to messages
    messages = db.relationship('ChatMessage', backref='session', lazy=True, cascade='all, delete-orphan')
    
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.utcnow()


class ChatMessage(db.Model):
    """Individual chat messages"""
    __tablename__ = 'chat_messages'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('chat_sessions.id'), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'user' or 'assistant'
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


class Settings(db.Model):
    """Chatbot configuration settings"""
    __tablename__ = 'settings'
    
    id = db.Column(db.Integer, primary_key=True)
    chatbot_name = db.Column(db.String(100), default='AI Assistant')
    personality_prompt = db.Column(db.Text, default='')
    chatbot_icon = db.Column(db.String(255), default='default-bot-icon.svg')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @staticmethod
    def get_settings():
        """Get or create settings singleton"""
        settings = Settings.query.first()
        if not settings:
            settings = Settings()
            db.session.add(settings)
            db.session.commit()
        return settings


class Profile(db.Model):
    """Resume profile for grouping artifacts"""
    __tablename__ = 'profiles'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    display_name = db.Column(db.String(100))
    introduction = db.Column(db.Text)
    is_default = db.Column(db.Boolean, default=False)
    primary_resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Many-to-many relationship with resumes
    resumes = db.relationship('Resume', secondary=profile_resumes, backref='profiles', lazy='dynamic')
    
    # Primary resume for downloads
    primary_resume = db.relationship('Resume', foreign_keys=[primary_resume_id], uselist=False)
    
    @staticmethod
    def get_default_profile():
        """Get the default profile"""
        profile = Profile.query.filter_by(is_default=True).first()
        if not profile:
            # If no default exists, create one
            profile = Profile(name='Default Profile', description='Default resume profile', is_default=True)
            db.session.add(profile)
            db.session.commit()
        return profile
    
    @staticmethod
    def get_all_active():
        """Get all active profiles"""
        return Profile.query.order_by(Profile.created_at.desc()).all()


class Resume(db.Model):
    """Uploaded resume artifacts"""
    __tablename__ = 'resumes'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    content = db.Column(db.Text)  # Extracted text content
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    @staticmethod
    def get_active_resumes(profile_id=None):
        """Get all active resumes, optionally filtered by profile"""
        if profile_id:
            profile = Profile.query.get(profile_id)
            if profile:
                return profile.resumes.filter_by(is_active=True).order_by(Resume.uploaded_at.desc()).all()
            return []
        return Resume.query.filter_by(is_active=True).order_by(Resume.uploaded_at.desc()).all()
