import sys
import os
from datetime import datetime

# Add the project root to sys.path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.api import app
from app.models import db, User

def reset_admin_password(username, new_password):
    """Reset the password for an admin user and unlock their account."""
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        
        if not user:
            print(f"[-] Error: User '{username}' not found in the database.")
            print("[*] Available users:")
            users = User.query.all()
            for u in users:
                print(f"    - {u.username}")
            return False
        
        try:
            # Update password
            user.set_password(new_password)
            
            # Reset security flags
            user.must_change_password = False
            user.unlock_account()
            user.failed_login_attempts = 0
            user.is_active = True
            
            db.session.commit()
            print(f"[+] Success: Password for '{username}' has been reset.")
            print(f"[*] Account unlocked and activated.")
            return True
        except Exception as e:
            print(f"[-] Error: Could not update password. {e}")
            db.session.rollback()
            return False

def create_admin(username, password):
    """Create a new admin user if they don't exist."""
    with app.app_context():
        existing = User.query.filter_by(username=username).first()
        if existing:
            print(f"[-] Error: User '{username}' already exists. Use reset instead.")
            return False
        
        try:
            new_user = User(
                username=username,
                is_active=True,
                must_change_password=False
            )
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            print(f"[+] Success: Admin user '{username}' created.")
            return True
        except Exception as e:
            print(f"[-] Error: Could not create user. {e}")
            db.session.rollback()
            return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Reset Password: python scripts/reset_admin.py reset <username> <new_password>")
        print("  Create Admin:   python scripts/reset_admin.py create <username> <new_password>")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "reset":
        if len(sys.argv) != 4:
            print("Usage: python scripts/reset_admin.py reset <username> <new_password>")
            sys.exit(1)
        reset_admin_password(sys.argv[2], sys.argv[3])
        
    elif command == "create":
        if len(sys.argv) != 4:
            print("Usage: python scripts/reset_admin.py create <username> <new_password>")
            sys.exit(1)
        create_admin(sys.argv[2], sys.argv[3])
        
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
