import os
import uuid
import ipaddress
# Force reload
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_from_directory
from flask_socketio import SocketIO, emit, join_room
from flask_login import login_user, logout_user, current_user
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from werkzeug.utils import secure_filename
import google.generativeai as genai

from config import Config
from app.models import db, User, ChatSession, ChatMessage, Settings, Resume, Profile
from app.auth import login_manager, admin_required, init_default_admin, validate_new_password
from app.rate_limiter import init_limiter, RATE_LIMITS
from app.security_headers import init_security_headers
from app import security_logger as sec_log

# Initialize Flask app
app = Flask(__name__, 
            template_folder='web/templates',
            static_folder='web/static')
app.config.from_object(Config)

# Initialize extensions
db.init_app(app)
login_manager.init_app(app)

# Initialize CSRF protection (will be applied manually to form routes)
csrf = CSRFProtect()
csrf.init_app(app)

# Initialize rate limiter
limiter = init_limiter(app)

# Initialize security headers
init_security_headers(app)

# Initialize SocketIO with environment-based CORS and threading mode (Python 3.13 compatible)
# SocketIO routes are automatically exempt from CSRF
socketio = SocketIO(app, cors_allowed_origins=app.config['CORS_ALLOWED_ORIGINS'], async_mode='threading')

# Initialize Flask-Migrate for database migrations
migrate = Migrate(app, db)





# Create logs directory
os.makedirs(os.path.join(os.path.dirname(__file__), '..', 'logs'), exist_ok=True)

# Configure Google Gemini
if app.config['GEMINI_API_KEY']:
    genai.configure(api_key=app.config['GEMINI_API_KEY'])

# Create upload folders
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['RESUME_FOLDER'], exist_ok=True)
os.makedirs(app.config['ICONS_FOLDER'], exist_ok=True)

# Initialize database
with app.app_context():
    # Security check: Ensure secret key is changed in production
    if app.config.get('IS_PRODUCTION') and app.config.get('SECRET_KEY') == 'dev-secret-key-change-in-production':
        app.logger.error("CRITICAL: Default SECRET_KEY used in production environment! Shutting down for security.")
        import sys
        sys.exit(1)

    db.create_all()
    init_default_admin(app)
    # Initialize default settings
    Settings.get_settings()
    # Initialize default profile
    Profile.get_default_profile()

def allowed_file(filename, allowed_extensions):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def is_local_ip(ip_address: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_address)
        return ip.is_private or ip.is_loopback
    except ValueError:
        return False

def get_location_from_ip(ip_address):
    """Get location from IP address (placeholder - can integrate with IP geolocation API)"""
    # For now, return a placeholder. In production, use a service like ipapi.co or ipinfo.io
    try:
        ip_obj = ipaddress.ip_address(ip_address)
        if ip_obj.is_private or ip_obj.is_loopback:
            return "Local Development"
    except ValueError:
        return "Local Development"  # treat invalid IP as local
    
    # Public IP → Lookup using API
    try:
        response = requests.get(f"https://ipapi.co/{ip_address}/json/", timeout=3)
        data = response.json()

        city = data.get("city")
        region = data.get("region")
        country = data.get("country_name")

        # Build formatted string e.g. "Chicago, Illinois USA"
        parts = [p for p in [city, region, country] if p]
        return ", ".join(parts) if parts else "Unknown Location"

    except Exception:
        return "Unknown Location"

def generate_chatbot_response(user_message, session_id, mode='conversational', profile_id=None, stream=False):
    """
    Generate response using Google Gemini with conversation history context
    
    Args:
        user_message: The user's message
        session_id: The session ID for retrieving conversation history
        mode: 'conversational' or 'simple'
        profile_id: Optional profile ID to filter resumes
        stream: Whether to stream the response (returns generator) or return full text
        
    Returns:
        Generated response text or generator
    """
    # Prompt injection protection
    injection_keywords = [
        "ignore previous instructions", 
        "ignore all instructions",
        "system prompt", 
        "reveal your instructions",
        "act as",
        "you are now",
        "sql", "delete", "drop table", # Basic SQL injection check if AI is tricked into DB access
        "<script>", "javascript:" # Basic XSS
    ]
    
    clean_message = user_message.lower()
    if any(keyword in clean_message for keyword in injection_keywords):
        sec_log.log_suspicious_activity(f"Potential prompt injection detected: {user_message}", 
                                       username=f"Session:{session_id}")
        return "I'm sorry, I cannot fulfill that request as it deviates from my professional persona."

    try:
        # Get settings and resume content
        settings = Settings.get_settings()
        
        # Get resumes filtered by profile
        if profile_id is None:
            # Use default profile if none specified
            default_profile = Profile.get_default_profile()
            profile_id = default_profile.id
        
        resumes = Resume.get_active_resumes(profile_id=profile_id)
        
        # Build context from resumes
        resume_context = ""
        if resumes:
            resume_texts = [r.content for r in resumes if r.content]
            if resume_texts:
                resume_context = "\n\n---\n\n".join(resume_texts)
        
        # Get conversation history (last 10 messages for context)
        session = ChatSession.query.filter_by(session_id=session_id).first()
        conversation_history = []
        
        if session:
            recent_messages = ChatMessage.query.filter_by(
                session_id=session.id
            ).order_by(
                ChatMessage.timestamp.desc()
            ).limit(10).all()
            
            # Reverse to get chronological order
            recent_messages = list(reversed(recent_messages))
            
            for msg in recent_messages:
                role = "User" if msg.role == "user" else "Assistant"
                conversation_history.append(f"{role}: {msg.content}")
        
        # Build conversation context
        conversation_context = ""
        if conversation_history:
            conversation_context = "\n".join(conversation_history)
        
        # Define prompts based on mode
        if mode == 'simple':
            personality = """You are a professional, fact-based assistant representing a job seeker.
Your goal is to provide clear, concise, and direct answers based strictly on the provided resume information.
Use bullet points for lists and keep paragraphs short.
Avoid conversational filler, small talk, or emotional language.
Focus on delivering the facts efficiently."""
        else:
            # Conversational mode (default)
            personality = settings.personality_prompt or """You are a helpful AI assistant representing a job seeker. 
Be friendly, professional, and enthusiastic about discussing your background and experience. 
Use natural, conversational language and share specific examples when relevant."""
        
        # Format the full prompt with conversation history
        if conversation_context:
            # Construct the prompt with persona and resume context
            full_prompt = f"""{personality}

## INSTRUCTIONS:
1. You are answering questions on behalf of the person described in the "Background Information" below.
2. Answer in the first person (using "I", "my", "me") as if you ARE this person, or as their dedicated assistant (depending on the persona defined above).
3. USE ONLY the information provided in the "Background Information" section to answer questions about background, skills, education, and experience.
4. If the answer is not in the text below, say "I don't have that specific detail in my current records" or "That information isn't listed in my resume."
5. DO NOT say "As an AI" or "I don't have a personal background." Pretend the background information is YOUR background.
6. If asked about school, work, or skills, look for the relevant section in the text below and summarize it naturally.

## Background Information (Resume/CV):
{resume_context if resume_context else "No resume information available yet."}

## Recent Conversation:
{conversation_context}

## Current Message:
User Question: {user_message}

Please respond to the user question strictly following the persona and instructions above."""
        else:
            # First message - no conversation history
            full_prompt = f"""{personality}

## INSTRUCTIONS:
1. You are answering questions on behalf of the person described in the "Background Information" below.
2. USE ONLY the information provided in the "Background Information" section.
3. DO NOT break character or say you are an AI unless explicitly asked about your technology.
4. If asked about education or experience, answer based strictly on the text below.

## Background Information (Resume/CV):
{resume_context if resume_context else "No resume information available yet."}

User Question: {user_message}

Please respond to the user question strictly following the persona and instructions above."""
        
        # Check if user is requesting resume download (handled separately from Gemini usually, but we check here)
        download_keywords = ['download', 'see resume', 'view resume', 'send resume', 
                            'share resume', 'resume file', 'resume pdf', 'get resume', 
                            'show resume', 'copy of resume', 'have your resume']
        is_resume_request = any(keyword in user_message.lower() for keyword in download_keywords)
        download_link_text = ""
        
        if is_resume_request:
            # Get the profile to check for primary resume
            if profile_id:
                profile = Profile.query.get(profile_id)
            else:
                profile = Profile.get_default_profile()
            
            if profile and profile.primary_resume_id:
                primary_resume = Resume.query.get(profile.primary_resume_id)
                if primary_resume:
                    download_url = url_for('uploaded_file', 
                                          filename=f'resumes/{primary_resume.filename}', 
                                          _external=True)
                    download_link_text = f"\n\nYou can download my resume here: {download_url}"

        # Generate response with Gemini
        if app.config['GEMINI_API_KEY']:
            model = genai.GenerativeModel(app.config['GEMINI_API_MODEL'])
            
            # Configure generation parameters for better responses
            generation_config = {
                'temperature': 0.3 if mode == 'simple' else 0.7,
                'top_p': 0.9,
                'top_k': 40,
                'max_output_tokens': 2048,
            }
            
            if stream:
                response = model.generate_content(
                    full_prompt,
                    generation_config=generation_config,
                    stream=True
                )
                
                # Generator function to yield chunks
                def stream_generator():
                    full_response = ""
                    try:
                        for chunk in response:
                            if chunk.text:
                                full_response += chunk.text
                                yield chunk.text
                    except Exception as e:
                        print(f"Error acting on stream: {e}")
                        yield " [Error generating response]"
                        
                    if download_link_text:
                        yield download_link_text
                        
                return stream_generator()
                
            else:
                # Non-streaming mode
                response = model.generate_content(
                    full_prompt,
                    generation_config=generation_config
                )
                
                try:
                    bot_response = response.text
                except (ValueError, AttributeError):
                    bot_response = str(response.candidates[0].content.parts[0].text) if response.candidates else "I apologize, but I'm having trouble generating a response right now."
                
                if download_link_text:
                    bot_response += download_link_text
                    
                return bot_response
        else:
            return "Gemini API key not configured. Please add your API key to use AI responses."
    
    except Exception as e:
        print(f"Error generating response: {e}")
        import traceback
        traceback.print_exc()
        return "I apologize, but I'm having trouble generating a response right now. Please try again in a moment."

# ============================================================================
# PUBLIC ROUTES
# ============================================================================

@app.route('/')
def index():
    """Main chat interface"""
    settings = Settings.get_settings()
    return render_template('chat.html', settings=settings)

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    """Serve uploaded files"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# ============================================================================
# ADMIN ROUTES
# ============================================================================

@app.route('/admin/login', methods=['GET', 'POST'])
@limiter.limit(RATE_LIMITS['login'])
def admin_login():
    """Admin login page with enhanced security"""
    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('Please provide both username and password', 'error')
            return render_template('admin/login.html')
        
        user = User.query.filter_by(username=username).first()
        
        if user:
            # Check if account is locked
            if user.is_locked():
                sec_log.log_failed_login(username, 'Account locked')
                flash('Account is temporarily locked due to too many failed login attempts. Please try again later.', 'error')
                return render_template('admin/login.html')
            
            # Check if account is active
            if not user.is_active:
                sec_log.log_failed_login(username, 'Account deactivated')
                flash('This account has been deactivated. Please contact an administrator.', 'error')
                return render_template('admin/login.html')
            
            # Verify password
            if user.check_password(password):
                # Successful login
                user.record_successful_login(ip_address=sec_log.get_client_ip())
                db.session.commit()
                
                login_user(user)
                sec_log.log_successful_login(username)
                flash('Login successful!', 'success')
                
                # Redirect to password change if required
                if user.must_change_password:
                    flash('You must change your password before continuing.', 'warning')
                    return redirect(url_for('change_password'))
                
                return redirect(url_for('admin_dashboard'))
            else:
                # Failed login - wrong password
                user.record_failed_login()
                db.session.commit()
                
                if user.is_locked():
                    sec_log.log_account_locked(username)
                    flash('Too many failed login attempts. Account has been locked for 30 minutes.', 'error')
                else:
                    remaining_attempts = 5 - user.failed_login_attempts
                    sec_log.log_failed_login(username, 'Invalid password')
                    flash(f'Invalid username or password. {remaining_attempts} attempts remaining.', 'error')
        else:
            # User not found
            sec_log.log_failed_login(username, 'User not found')
            flash('Invalid username or password', 'error')
    
    return render_template('admin/login.html')

@app.route('/admin/logout')
@admin_required
def admin_logout():
    """Admin logout"""
    username = current_user.username
    logout_user()
    sec_log.log_admin_action('Logout', username)
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/admin/change-password', methods=['GET', 'POST'])
@admin_required
def change_password():
    """Change password page"""
    if request.method == 'POST':
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validate current password
        if not current_user.check_password(current_password):
            flash('Current password is incorrect', 'error')
            return render_template('admin/change_password.html')
        
        # Validate new password matches confirmation
        if new_password != confirm_password:
            flash('New passwords do not match', 'error')
            return render_template('admin/change_password.html')
        
        # Validate password strength
        is_valid, errors = validate_new_password(new_password, current_user.username)
        if not is_valid:
            for error in errors:
                flash(error, 'error')
            return render_template('admin/change_password.html')
        
        # Update password
        current_user.set_password(new_password)
        current_user.must_change_password = False
        db.session.commit()
        
        sec_log.log_password_change(current_user.username)
        flash('Password changed successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    
    return render_template('admin/change_password.html')

# ============================================================================
# USER MANAGEMENT ROUTES
# ============================================================================

@app.route('/admin/users')
@admin_required
def admin_users():
    """User management page"""
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=users)

@app.route('/admin/users/create', methods=['GET', 'POST'])
@admin_required
@limiter.limit(RATE_LIMITS['admin_action'])
def create_user():
    """Create new user"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        must_change_password = request.form.get('must_change_password') == 'on'
        
        # Validate inputs
        if not username:
            flash('Username is required', 'error')
            return render_template('admin/user_edit.html', user=None)
        
        if not password:
            flash('Password is required', 'error')
            return render_template('admin/user_edit.html', user=None)
        
        # Check if username already exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return render_template('admin/user_edit.html', user=None)
        
        # Check if email already exists (if provided)
        if email and User.query.filter_by(email=email).first():
            flash('Email already exists', 'error')
            return render_template('admin/user_edit.html', user=None)
        
        # Validate password matches confirmation
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('admin/user_edit.html', user=None)
        
        # Validate password strength
        is_valid, errors = validate_new_password(password, username)
        if not is_valid:
            for error in errors:
                flash(error, 'error')
            return render_template('admin/user_edit.html', user=None)
        
        # Create user
        user = User(
            username=username,
            email=email if email else None,
            must_change_password=must_change_password
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        sec_log.log_user_created(username, current_user.username)
        flash(f'User {username} created successfully!', 'success')
        return redirect(url_for('admin_users'))
    
    return render_template('admin/user_edit.html', user=None)

@app.route('/admin/users/<int:user_id>/edit', methods=['GET', 'POST'])
@admin_required
@limiter.limit(RATE_LIMITS['admin_action'])
def edit_user(user_id):
    """Edit user"""
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        new_username = request.form.get('username', '').strip()
        new_email = request.form.get('email', '').strip()
        is_active = request.form.get('is_active') == 'on'
        new_password = request.form.get('new_password', '')
        
        fields_changed = []
        
        # Update username if changed
        if new_username and new_username != user.username:
            if User.query.filter_by(username=new_username).first():
                flash('Username already exists', 'error')
                return render_template('admin/user_edit.html', user=user)
            user.username = new_username
            fields_changed.append('username')
        
        # Update email if changed
        if new_email != (user.email or ''):
            if new_email and User.query.filter(User.email == new_email, User.id != user_id).first():
                flash('Email already exists', 'error')
                return render_template('admin/user_edit.html', user=user)
            user.email = new_email if new_email else None
            fields_changed.append('email')
        
        # Update active status
        if is_active != user.is_active:
            user.is_active = is_active
            fields_changed.append('is_active')
            if not is_active:
                user.unlock_account()  # Unlock if deactivating
        
        # Update password if provided
        if new_password:
            is_valid, errors = validate_new_password(new_password, user.username)
            if not is_valid:
                for error in errors:
                    flash(error, 'error')
                return render_template('admin/user_edit.html', user=user)
            
            user.set_password(new_password)
            user.must_change_password = request.form.get('must_change_password') == 'on'
            fields_changed.append('password')
        
        db.session.commit()
        
        if fields_changed:
            sec_log.log_user_updated(user.username, current_user.username, fields_changed)
        
        flash(f'User {user.username} updated successfully!', 'success')
        return redirect(url_for('admin_users'))
    
    return render_template('admin/user_edit.html', user=user)

@app.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@admin_required
@limiter.limit(RATE_LIMITS['admin_action'])
def delete_user(user_id):
    """Delete/deactivate user"""
    user = User.query.get_or_404(user_id)
    
    # Prevent deleting yourself
    if user.id == current_user.id:
        flash('You cannot delete your own account', 'error')
        return redirect(url_for('admin_users'))
    
    # Deactivate instead of delete to preserve audit trail
    user.is_active = False
    db.session.commit()
    
    sec_log.log_user_deleted(user.username, current_user.username)
    flash(f'User {user.username} has been deactivated', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/users/<int:user_id>/unlock', methods=['POST'])
@admin_required
def unlock_user(user_id):
    """Unlock a locked user account"""
    user = User.query.get_or_404(user_id)
    user.unlock_account()
    db.session.commit()
    
    sec_log.log_admin_action('Unlock account', current_user.username, f'Unlocked user: {user.username}')
    flash(f'User {user.username} has been unlocked', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin')
@admin_required
def admin_dashboard():
    """Admin dashboard"""
    # Get statistics
    total_sessions = ChatSession.query.count()
    total_messages = ChatMessage.query.count()
    recent_sessions = ChatSession.query.order_by(ChatSession.started_at.desc()).limit(10).all()
    
    return render_template('admin/dashboard.html',
                         total_sessions=total_sessions,
                         total_messages=total_messages,
                         recent_sessions=recent_sessions)

@app.route('/admin/analytics')
@admin_required
def admin_analytics():
    """Analytics dashboard"""
    sessions = ChatSession.query.order_by(ChatSession.started_at.desc()).all()
    return render_template('admin/analytics.html', sessions=sessions)

@app.route('/admin/settings', methods=['GET', 'POST'])
@admin_required
def admin_settings():
    """Admin settings page"""
    settings = Settings.get_settings()
    
    if request.method == 'POST':
        settings.chatbot_name = request.form.get('chatbot_name')
        settings.personality_prompt = request.form.get('personality_prompt')
        
        # Handle icon upload
        if 'chatbot_icon' in request.files:
            file = request.files['chatbot_icon']
            if file and file.filename:
                # In production, we'd use secure_filename and a proper storage
                filename = secure_filename(file.filename)
                # Ensure unique filename
                filename = f"{uuid.uuid4().hex}_{filename}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], 'icons', filename))
                settings.chatbot_icon = f"/uploads/icons/{filename}"
        
        db.session.commit()
        flash('Settings updated successfully', 'success')
        return redirect(url_for('admin_settings'))
    
    return render_template('admin/settings.html', settings=settings)

@app.route('/admin/artifacts')
@admin_required
def admin_artifacts():
    """Dedicated management page for resumes and artifacts"""
    resumes = Resume.query.order_by(Resume.uploaded_at.desc()).all()
    profiles = Profile.query.all()
    return render_template('admin/artifacts.html', resumes=resumes, profiles=profiles)

@app.route('/admin/upload-resume', methods=['POST'])
@admin_required
def upload_resume():
    """Upload resume file with automatic text extraction"""
    if 'resume' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['resume']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and allowed_file(file.filename, app.config['ALLOWED_RESUME_EXTENSIONS']):
        from app.utils import extract_text_from_file
        
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        file_path = os.path.join(app.config['RESUME_FOLDER'], unique_filename)
        file.save(file_path)
        
        # Extract text content from the file
        content = extract_text_from_file(file_path)
        
        if not content:
            print(f"Warning: No text extracted from {filename}")
        
        # Create resume record
        resume = Resume(
            filename=unique_filename,
            original_filename=filename,
            file_path=file_path,
            content=content
        )
        db.session.add(resume)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'Resume uploaded and processed successfully', 
            'id': resume.id,
            'extracted_chars': len(content) if content else 0
        })
    
    return jsonify({'error': 'Invalid file type'}), 400

@app.route('/admin/upload-resume-text', methods=['POST'])
@admin_required
def upload_resume_text():
    """Upload resume text artifact"""
    text_content = request.form.get('resume_text', '').strip()
    
    if not text_content:
        return jsonify({'error': 'No text content provided'}), 400
    
    try:
        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"text_artifact_{timestamp}.txt"
        unique_filename = f"{uuid.uuid4()}_{filename}"
        file_path = os.path.join(app.config['RESUME_FOLDER'], unique_filename)
        
        # Save text to file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(text_content)
        
        # Create resume record
        resume = Resume(
            filename=unique_filename,
            original_filename=filename,
            file_path=file_path,
            content=text_content
        )
        db.session.add(resume)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'Text artifact saved successfully', 
            'id': resume.id,
            'extracted_chars': len(text_content)
        })
        
    except Exception as e:
        print(f"Error saving text artifact: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/admin/resume/<int:resume_id>', methods=['GET'])
@admin_required
def get_resume(resume_id):
    """Get resume details and content"""
    resume = Resume.query.get_or_404(resume_id)
    return jsonify({
        'id': resume.id,
        'filename': resume.original_filename,
        'content': resume.content,
        'is_text': resume.original_filename.endswith('.txt')
    })

@app.route('/admin/resume/<int:resume_id>/update', methods=['POST'])
@admin_required
def update_resume(resume_id):
    """Update resume content, filename, and profile assignments"""
    resume = Resume.query.get_or_404(resume_id)
    content = request.form.get('content')
    filename = request.form.get('filename')
    profile_ids = request.form.getlist('profile_ids')
    
    if content is None:
        return jsonify({'error': 'No content provided'}), 400
        
    try:
        # Update database fields
        resume.content = content
        if filename:
            resume.original_filename = filename.strip()
        
        # Handle Profile assignments
        if profile_ids:
            # Sync assignments
            new_profiles = Profile.query.filter(Profile.id.in_([int(pid) for pid in profile_ids])).all()
            resume.profiles = new_profiles
        else:
            # If no profiles selected, clear assignments
            resume.profiles = []

        # Update physical file
        with open(resume.file_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        db.session.commit()
        
        sec_log.log_admin_action('Update artifact', current_user.username, 
                                f'Updated artifact: {resume.original_filename} (Profiles: {len(resume.profiles)})')
                                
        return jsonify({
            'success': True, 
            'message': 'Artifact synced and deployed successfully',
            'id': resume.id
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/admin/delete-resume/<int:resume_id>', methods=['POST'])
@admin_required
def delete_resume(resume_id):
    """Delete resume"""
    resume = Resume.query.get_or_404(resume_id)
    resume.is_active = False
    db.session.commit()
    flash('Resume deleted successfully!', 'success')
    return redirect(url_for('admin_settings'))

# ============================================================================
# PROFILE MANAGEMENT ROUTES
# ============================================================================

@app.route('/admin/profiles')
@admin_required
def admin_profiles():
    """Profile management page"""
    profiles = Profile.get_all_active()
    return render_template('admin/profiles.html', profiles=profiles)

@app.route('/admin/profiles/create', methods=['GET', 'POST'])
@admin_required
def create_profile():
    """Create new profile"""
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description', '')
        is_default = request.form.get('is_default') == 'on'
        
        if not name:
            flash('Profile name is required', 'error')
            return redirect(url_for('create_profile'))
        
        # If setting as default, unset other defaults
        if is_default:
            Profile.query.filter_by(is_default=True).update({'is_default': False})
        
        profile = Profile(name=name, description=description, is_default=is_default)
        db.session.add(profile)
        db.session.commit()
        
        flash('Profile created successfully!', 'success')
        return redirect(url_for('edit_profile', profile_id=profile.id))
    
    return render_template('admin/profile_edit.html', profile=None, resumes=Resume.get_active_resumes())

@app.route('/admin/profiles/<int:profile_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_profile(profile_id):
    """Edit profile"""
    profile = Profile.query.get_or_404(profile_id)
    
    if request.method == 'POST':
        profile.name = request.form.get('name', profile.name)
        profile.description = request.form.get('description', '')
        profile.display_name = request.form.get('display_name', '')
        profile.introduction = request.form.get('introduction', '')
        is_default = request.form.get('is_default') == 'on'
        
        # Handle primary resume selection
        primary_resume_id = request.form.get('primary_resume_id')
        if primary_resume_id:
            profile.primary_resume_id = int(primary_resume_id)
        else:
            profile.primary_resume_id = None
        
        # If setting as default, unset other defaults
        if is_default and not profile.is_default:
            Profile.query.filter_by(is_default=True).update({'is_default': False})
            profile.is_default = True
        elif not is_default and profile.is_default:
            # Can't unset the last default
            flash('At least one profile must be default', 'warning')
            is_default = True
        
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('admin_profiles'))
    
    all_resumes = Resume.get_active_resumes()
    assigned_resume_ids = [r.id for r in profile.resumes.all()]
    
    return render_template('admin/profile_edit.html', 
                         profile=profile, 
                         resumes=all_resumes,
                         assigned_resume_ids=assigned_resume_ids)

@app.route('/admin/profiles/<int:profile_id>/resumes', methods=['POST'])
@admin_required
def assign_resumes(profile_id):
    """Assign/unassign resumes to profile"""
    profile = Profile.query.get_or_404(profile_id)
    resume_ids = request.form.getlist('resume_ids[]')
    
    # Clear existing assignments
    profile.resumes = []
    
    # Add new assignments
    for resume_id in resume_ids:
        resume = Resume.query.get(int(resume_id))
        if resume:
            profile.resumes.append(resume)
    
    db.session.commit()
    return jsonify({'success': True, 'message': 'Resumes updated successfully'})

@app.route('/admin/profiles/<int:profile_id>/delete', methods=['POST'])
@admin_required
def delete_profile(profile_id):
    """Delete profile"""
    profile = Profile.query.get_or_404(profile_id)
    
    if profile.is_default:
        flash('Cannot delete the default profile', 'error')
        return redirect(url_for('admin_profiles'))
    
    db.session.delete(profile)
    db.session.commit()
    
    flash('Profile deleted successfully!', 'success')
    return redirect(url_for('admin_profiles'))

@app.route('/api/profiles')
def get_profiles():
    """Get all profiles for public selection"""
    profiles = Profile.get_all_active()
    return jsonify([{
        'id': p.id,
        'name': p.name,
        'description': p.description,
        'display_name': p.display_name,
        'introduction': p.introduction,
        'is_default': p.is_default
    } for p in profiles])

@app.route('/api/history/<session_id>/messages')
def get_session_messages(session_id):
    """Get messages for a specific session"""
    user_identifier = request.args.get('user_identifier')
    
    # Find session by public session_id string
    session = ChatSession.query.filter_by(session_id=session_id).first_or_404()
    
    # Optional: Verify ownership if user_identifier is used and set on session
    if user_identifier and session.user_identifier and session.user_identifier != user_identifier:
        return jsonify({'error': 'Unauthorized'}), 401
    
    # If session has no user_identifier but one was provided, maybe update it? 
    # For now, let's keep it simple. If session was anonymous, anyone with ID can view?
    # Ideally we should strictly enforce user_identifier for privacy if used.
    
    messages = ChatMessage.query.filter_by(session_id=session.id).order_by(ChatMessage.timestamp).all()
    
    return jsonify({
        'session_id': session.session_id,
        'title': session.title,
        'messages': [{
            'role': msg.role,
            'content': msg.content,
            'timestamp': msg.timestamp.isoformat()
        } for msg in messages]
    })

@app.route('/admin/session/<int:session_id>')
@admin_required
def view_session(session_id):
    """View session details"""
    session = ChatSession.query.get_or_404(session_id)
    messages = ChatMessage.query.filter_by(session_id=session.id).order_by(ChatMessage.timestamp).all()
    return jsonify({
        'session': {
            'id': session.id,
            'session_id': session.session_id,
            'ip_address': session.ip_address,
            'location': session.location,
            'started_at': session.started_at.isoformat(),
            'last_activity': session.last_activity.isoformat(),
            'message_count': session.message_count
        },
        'messages': [{
            'role': msg.role,
            'content': msg.content,
            'timestamp': msg.timestamp.isoformat()
        } for msg in messages]
    })

# ============================================================================
# SOCKET.IO EVENTS
# ============================================================================

@socketio.on('connect')
def handle_connect(auth=None):
    """
    Handle client connection with CSWSH protection.
    
    Security measures:
    1. Strict origin validation against whitelist
    2. Referer header validation
    3. Session validation for authenticated users
    """
    # Get origin from headers
    origin = request.headers.get('Origin')
    referer = request.headers.get('Referer')
    
    # Strict origin validation
    allowed_origins = app.config['CORS_ALLOWED_ORIGINS']
    
    # Check Origin header (primary check)
    if origin:
        if origin not in allowed_origins:
            sec_log.log_security_event(
                'websocket_rejected',
                f'Rejected WebSocket connection from unauthorized origin: {origin}',
                ip_address=request.remote_addr,
                severity='warning'
            )
            return False  # Reject connection
    
    # Fallback to Referer header check if no Origin
    elif referer:
        referer_origin = '/'.join(referer.split('/')[:3])  # Extract origin from referer
        if referer_origin not in allowed_origins:
            sec_log.log_security_event(
                'websocket_rejected',
                f'Rejected WebSocket connection from unauthorized referer: {referer}',
                ip_address=request.remote_addr,
                severity='warning'
            )
            return False  # Reject connection
    
    # If neither Origin nor Referer is present, reject (potential attack)
    else:
        sec_log.log_security_event(
            'websocket_rejected',
            'Rejected WebSocket connection with no Origin or Referer header',
            ip_address=request.remote_addr,
            severity='warning'
        )
        return False  # Reject connection
    
    # Generate or retrieve session ID
    session_id = request.args.get('session_id') or str(uuid.uuid4())
    join_room(session_id)
    
    # Get or create session
    session = ChatSession.query.filter_by(session_id=session_id).first()
    if not session:
        ip_address = request.remote_addr
        location = get_location_from_ip(ip_address)
        user_agent = request.headers.get('User-Agent', '')
        
        user_identifier = request.args.get('user_identifier') or request.headers.get('X-User-Identifier')
        
        session = ChatSession(
            session_id=session_id,
            ip_address=ip_address,
            location=location,
            user_agent=user_agent,
            user_identifier=user_identifier
        )
        db.session.add(session)
        db.session.commit()
        
        sec_log.log_security_event(
            'websocket_connected',
            f'New WebSocket session created',
            ip_address=ip_address,
            severity='info'
        )
    
    emit('connected', {'session_id': session_id})

@socketio.on('send_message')
def handle_message(data):
    """Handle incoming chat message"""
    session_id = data.get('session_id')
    user_message = data.get('message', '').strip()
    
    if not user_message:
        return
    
    # Get session
    session = ChatSession.query.filter_by(session_id=session_id).first()
    if not session:
        emit('error', {'message': 'Session not found'})
        return
    
    # Save user message
    user_msg = ChatMessage(
        session_id=session.id,
        role='user',
        content=user_message
    )
    db.session.add(user_msg)
    
    # Update session
    session.update_activity()
    session.message_count += 1
    db.session.commit()
    
    # Echo user message
    emit('message', {
        'role': 'user',
        'content': user_message,
        'timestamp': user_msg.timestamp.isoformat()
    }, room=session_id)
    
    # Notify client that bot is typing (or starting to stream)
    emit('typing', {'typing': True}, room=session_id)
    
    # Get mode and profile from data
    mode = data.get('mode', 'conversational')
    profile_id = data.get('profile_id')  # Will be None if not provided
    
    # Start bot response stream
    bot_timestamp = datetime.utcnow()
    emit('message_start', {
        'role': 'assistant',
        'timestamp': bot_timestamp.isoformat()
    }, room=session_id)
    
    full_response = ""
    try:
        # Get streaming generator
        stream_gen = generate_chatbot_response(user_message, session_id, mode, profile_id, stream=True)
        
        if isinstance(stream_gen, str):
            # Fallback if for some reason it returns string (e.g. error or API key missing)
            full_response = stream_gen
            emit('message_chunk', {'content': full_response}, room=session_id)
        else:
            # Iterate through stream
            for chunk in stream_gen:
                if chunk:
                    full_response += chunk
                    emit('message_chunk', {'content': chunk}, room=session_id)
                    
    except Exception as e:
        print(f"Error in stream handling: {e}")
        error_msg = "I encountered an error generating the response."
        emit('message_chunk', {'content': error_msg}, room=session_id)
        full_response += error_msg

    # Finalize
    emit('message_end', {}, room=session_id)
    emit('typing', {'typing': False}, room=session_id)
    
    # Save bot message to DB
    bot_msg = ChatMessage(
        session_id=session.id,
        role='assistant',
        content=full_response,
        timestamp=bot_timestamp
    )
    db.session.add(bot_msg)
    session.message_count += 1
    db.session.commit()
    
    # Update session title if first message
    if session.message_count <= 2 and not session.title:
        # Simple title generation from first message (truncated)
        title = user_message[:50] + "..." if len(user_message) > 50 else user_message
        session.title = title
        db.session.commit()

@app.route('/api/history', methods=['GET'])
def get_chat_history():
    """Get chat history for a user"""
    user_identifier = request.args.get('user_identifier')
    
    if not user_identifier:
        return jsonify([])
        
    sessions = ChatSession.query.filter_by(
        user_identifier=user_identifier
    ).order_by(
        ChatSession.last_activity.desc()
    ).limit(50).all()
    
    return jsonify([{
        'session_id': s.session_id,
        'title': s.title or "New Chat",
        'last_activity': s.last_activity.isoformat(),
        'message_count': s.message_count
    } for s in sessions])

@app.route('/api/history/<session_id>', methods=['DELETE'])
def delete_chat_session(session_id):
    """Delete a chat session"""
    # In a real app we'd verify ownership via user_identifier
    session = ChatSession.query.filter_by(session_id=session_id).first_or_404()
    db.session.delete(session)
    db.session.commit()
    return jsonify({'success': True})



if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=8080, debug=True)
