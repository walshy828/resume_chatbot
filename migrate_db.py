"""
Manual migration script for adding new columns to existing databases.
Run this if you have an existing database without Flask-Migrate.

Usage:
    python migrate_db.py
"""
import sqlite3
import os

DB_PATH = 'instance/chatbot.db'

def add_column_if_not_exists(cursor, table, column, column_type):
    """Add column if it doesn't exist"""
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [col[1] for col in cursor.fetchall()]
    
    if column not in columns:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")
        print(f"✓ Added {column} to {table}")
        return True
    else:
        print(f"○ {column} already exists in {table}")
        return False

def migrate():
    """Run migration"""
    if not os.path.exists(DB_PATH):
        print("No existing database found. Will be created on first run.")
        return
    
    print("Running database migration...")
    print(f"Database: {DB_PATH}\n")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    changes_made = False
    
    try:
        # Add new Profile columns
        print("Migrating 'profiles' table:")
        changes_made |= add_column_if_not_exists(cursor, 'profiles', 'display_name', 'VARCHAR(100)')
        changes_made |= add_column_if_not_exists(cursor, 'profiles', 'introduction', 'TEXT')
        changes_made |= add_column_if_not_exists(cursor, 'profiles', 'primary_resume_id', 'INTEGER')
        
        conn.commit()
        
        if changes_made:
            print("\n✓ Migration completed successfully!")
        else:
            print("\n○ Database is already up to date.")
        
    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()
