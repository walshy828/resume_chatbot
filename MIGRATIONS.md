# Database Migrations Guide

This project uses both manual migrations and Flask-Migrate for database schema changes.

## For Existing Installations (Manual Migration)

If you have an existing database and want to add new columns without losing data:

```bash
python migrate_db.py
```

This will safely add:
- `display_name` to profiles table
- `introduction` to profiles table  
- `primary_resume_id` to profiles table

## For New Installations (Flask-Migrate)

### Initial Setup

1. Install Flask-Migrate:
```bash
pip install Flask-Migrate
```

2. Initialize migrations (first time only):
```bash
flask db init
```

3. Create initial migration:
```bash
flask db migrate -m "Initial migration"
```

4. Apply migration:
```bash
flask db upgrade
```

### Adding New Fields

When you add new columns to models:

1. Update the model in `app/models.py`
2. Create migration:
```bash
flask db migrate -m "Add new field description"
```
3. Review the generated migration in `migrations/versions/`
4. Apply migration:
```bash
flask db upgrade
```

## Environment Variables

### Admin Credentials

Set these in your `.env` file:

```bash
ADMIN_USERNAME=your_admin_username
ADMIN_PASSWORD=your_secure_password
```

If not set, defaults to `admin`/`admin`.

### Required Variables

```bash
GEMINI_API_KEY=your_api_key
SECRET_KEY=your_secret_key
ADMIN_USERNAME=admin
ADMIN_PASSWORD=change_me_in_production
```

## Docker Deployment

### Build and Run

```bash
# Build image
docker-compose build

# Start service
docker-compose up -d

# View logs
docker-compose logs -f

# Stop service
docker-compose down
```

### Environment Variables with Docker

Create a `.env` file in the project root:

```bash
GEMINI_API_KEY=your_key_here
SECRET_KEY=your_secret_key_here
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your_secure_password
```

Docker Compose will automatically load these.

### Data Persistence

The following directories are mounted as volumes:
- `./instance` - Database and instance data
- `./uploads` - Uploaded resume files and icons

Data persists across container restarts.

## Production Checklist

- [ ] Set strong `SECRET_KEY`
- [ ] Set secure `ADMIN_PASSWORD`
- [ ] Configure `GEMINI_API_KEY`
- [ ] Backup `instance/` directory regularly
- [ ] Backup `uploads/` directory regularly
- [ ] Use HTTPS in production
- [ ] Set appropriate file permissions on `.env`

## Troubleshooting

### Database locked error
If you get "database is locked" errors:
```bash
# Stop all instances
docker-compose down
# or kill local python process

# Restart
docker-compose up -d
```

### Migration conflicts
If migrations conflict:
```bash
# Downgrade one version
flask db downgrade

# Or reset (WARNING: loses data)
rm -rf migrations/
flask db init
flask db migrate -m "Fresh start"
flask db upgrade
```

### Reset admin password
```python
# In Python shell
from app.models import db, User
from app.api import app

with app.app_context():
    admin = User.query.filter_by(username='admin').first()
    admin.set_password('new_password')
    db.session.commit()
```
