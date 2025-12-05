"""
Simple database migration script to add security fields to User model.
This script uses direct SQL to avoid import issues.
"""
import sqlite3
import os

def migrate_database():
    """Add new security fields to User table"""
    
    # Find the database file
    db_path = 'instance/chatbot.db'
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        print("Looking for database...")
        # Try alternative locations
        alternatives = ['chatbot.db', 'instance/chatbot.db', 'app.db']
        for alt in alternatives:
            if os.path.exists(alt):
                db_path = alt
                break
        else:
            print("ERROR: Could not find database file")
            print("Please ensure the database exists before running migration")
            return
    
    print(f"Found database at: {db_path}")
    print("Starting migration...")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get current columns
    cursor.execute("PRAGMA table_info(users)")
    columns = [row[1] for row in cursor.fetchall()]
    print(f"Current columns: {columns}")
    
    # Define new columns to add
    new_columns = {
        'email': 'ALTER TABLE users ADD COLUMN email VARCHAR(120)',
        'failed_login_attempts': 'ALTER TABLE users ADD COLUMN failed_login_attempts INTEGER DEFAULT 0',
        'locked_until': 'ALTER TABLE users ADD COLUMN locked_until DATETIME',
        'password_changed_at': 'ALTER TABLE users ADD COLUMN password_changed_at DATETIME',
        'must_change_password': 'ALTER TABLE users ADD COLUMN must_change_password BOOLEAN DEFAULT 0',
        'last_login_at': 'ALTER TABLE users ADD COLUMN last_login_at DATETIME',
        'last_login_ip': 'ALTER TABLE users ADD COLUMN last_login_ip VARCHAR(45)',
        'is_active': 'ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT 1'
    }
    
    # Add missing columns
    for col_name, sql in new_columns.items():
        if col_name not in columns:
            try:
                print(f"Adding column: {col_name}")
                cursor.execute(sql)
                conn.commit()
                print(f"✓ Added column: {col_name}")
            except Exception as e:
                print(f"✗ Error adding {col_name}: {e}")
                conn.rollback()
        else:
            print(f"⊙ Column {col_name} already exists")
    
    # Update existing users to set default values
    print("\nUpdating existing users...")
    try:
        cursor.execute("""
            UPDATE users 
            SET failed_login_attempts = 0 
            WHERE failed_login_attempts IS NULL
        """)
        cursor.execute("""
            UPDATE users 
            SET is_active = 1 
            WHERE is_active IS NULL
        """)
        cursor.execute("""
            UPDATE users 
            SET must_change_password = 0 
            WHERE must_change_password IS NULL
        """)
        cursor.execute("""
            UPDATE users 
            SET password_changed_at = created_at 
            WHERE password_changed_at IS NULL
        """)
        conn.commit()
        
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        print(f"✓ Updated {count} existing users")
    except Exception as e:
        print(f"✗ Error updating users: {e}")
        conn.rollback()
    
    conn.close()
    
    print("\n✓ Migration completed successfully!")
    print("\nNext steps:")
    print("1. Restart your application")
    print("2. Test login functionality")
    print("3. Check security logs in logs/security.log")
    print("4. Review user management at /admin/users")

if __name__ == '__main__':
    migrate_database()
