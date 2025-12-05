# Resume Chatbot Application

A professional AI-powered chatbot interface for showcasing a job seeker's background and experience. Built with Python Flask, TailwindCSS v4, and Google Gemini AI.

## Features

### 🤖 Chat Interface
- Clean, professional chat UI with real-time messaging
- Socket.IO for instant message delivery
- **Context-aware AI responses** with conversation history (last 10 messages)
- **Intelligent prompt engineering** for natural conversations
- Typing indicators and smooth animations
- Mobile-responsive design
- Automatic light/dark mode based on system preferences

### 📊 Analytics Dashboard
- Session tracking with IP and location data
- Conversation history viewer
- Search and filter capabilities
- Detailed session information

### ⚙️ Admin Panel
- Secure authentication with bcrypt password hashing
- Chatbot configuration (name, personality, icon)
- **Automatic text extraction** from PDF, DOCX, and TXT files
- Resume upload and management
- Real-time settings updates

### 🔒 Security
- Password salting and hashing with bcrypt
- Secure session management
- Input validation and sanitization
- Protected admin routes

## Technology Stack

- **Backend**: Python 3.x, Flask, Flask-SocketIO
- **Database**: SQLite with SQLAlchemy ORM
- **AI**: Google Gemini API with conversation history context
- **Document Processing**: PyPDF2, python-docx for text extraction
- **Frontend**: HTML5, TailwindCSS v4 (CDN), JavaScript
- **Icons**: Lucide Icons
- **Fonts**: Google Fonts (Inter, Outfit)
- **Real-time**: Socket.IO

## Setup Instructions

### Prerequisites
- Python 3.8 or higher
- Google Gemini API key

### Installation

1. **Clone or navigate to the project directory**
   ```bash
   cd /Users/dpw/Documents/Development/resume_chatbot
   ```

2. **Create a virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and add your Google Gemini API key:
   ```
   GEMINI_API_KEY=your-api-key-here
   SECRET_KEY=your-secret-key-here
   ```

5. **Initialize the database**
   The database will be automatically created on first run with default admin credentials.

6. **Run the application**
   ```bash
   python -m app
   ```

7. **Access the application**
   - Chat Interface: http://localhost:8080
   - Admin Login: http://localhost:8080/admin/login

## Default Credentials

**Username**: `admin`  
**Password**: `changeme123`

⚠️ **Important**: Change these credentials after your first login!

## Project Structure

```
resume_chatbot/
├── app/
│   ├── __init__.py
│   ├── __main__.py
│   ├── api.py              # Main Flask application and routes
│   ├── models.py           # Database models
│   ├── auth.py             # Authentication utilities
│   └── web/
│       ├── templates/
│       │   ├── base.html
│       │   ├── chat.html
│       │   └── admin/
│       │       ├── login.html
│       │       ├── dashboard.html
│       │       ├── analytics.html
│       │       └── settings.html
│       └── static/
│           └── images/
├── uploads/                # Uploaded files (created automatically)
├── config.py              # Application configuration
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables (create from .env.example)
└── README.md
```

## Usage Guide

### For End Users (Chat Interface)

1. Visit the homepage at http://localhost:8080
2. Start chatting with the AI assistant
3. Ask questions about the job seeker's background, experience, skills, etc.
4. The chatbot will respond based on uploaded resume data and personality configuration

### For Administrators

1. **Login**
   - Navigate to http://localhost:8080/admin/login
   - Use the default credentials (or your updated credentials)

2. **Configure Chatbot**
   - Go to Settings
   - Set the chatbot name
   - Upload a custom icon (optional)
   - Define the personality prompt

3. **Upload Resume**
   - In Settings, scroll to "Resume Artifacts"
   - Upload PDF, DOC, DOCX, or TXT files
   - Text is automatically extracted and processed
   - The chatbot will use this information to answer questions

4. **View Analytics**
   - Access the Analytics page to see all chat sessions
   - View conversation history
   - Track IP addresses and locations
   - Search and filter sessions

## Google Gemini AI Integration

The application features an **enhanced Gemini API integration** with:

- **Conversation History Context**: Maintains context of last 10 messages for natural, flowing conversations
- **Intelligent Prompt Engineering**: Structured prompts with personality, resume content, and conversation history
- **Configurable Parameters**: Fine-tuned temperature (0.7), top_p (0.9), and token limits for optimal responses
- **Automatic Document Processing**: Extracts text from PDF, DOCX, and TXT files automatically
- **Error Handling**: Robust error handling with detailed logging and graceful degradation

For detailed information about the Gemini integration, see [GEMINI_INTEGRATION.md](GEMINI_INTEGRATION.md).

## Chatbot Personality Configuration

The personality prompt defines how the chatbot behaves. Here's the recommended format:

```
## Your Personality:
- Friendly, approachable, and genuinely enthusiastic about your work
- Confident but humble about your achievements
- Use natural, conversational language

## How to Communicate:
- Start with warm, personal greetings
- Use natural transitions
- Share personal insights about your projects

## Response Style:
- Share specific stories and examples
- Be detailed and contextual
- Show enthusiasm about projects

## Background Information:
{Resume content will be automatically included}
```

## Customization

### Changing Colors
The application uses TailwindCSS v4 with a blue-purple gradient theme. To customize:
- Edit the `tailwind.config` in `base.html`
- Modify the color classes in templates

### Adding Features
- New routes: Add to `app/api.py`
- New models: Add to `app/models.py`
- New templates: Create in `app/web/templates/`

## Troubleshooting

### Database Issues
If you encounter database errors, delete `chatbot.db` and restart the application to recreate it.

### Socket.IO Connection Issues
Ensure no firewall is blocking port 8080 and that the Socket.IO client version matches the server version.

### Gemini API Errors
- Verify your API key is correct in `.env`
- Check your API quota and billing status
- Ensure you're using a supported model (`gemini-pro`)

## Development

To run in development mode with debug enabled:
```bash
python -m app
```

The application will automatically reload when you make changes to Python files.

## License

This project is provided as-is for portfolio and demonstration purposes.

## Support

For issues or questions, please refer to the documentation or create an issue in the project repository.
