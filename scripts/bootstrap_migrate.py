"""
Bootstrap migration script for SQLite databases.

This script:
- Adds missing columns to existing tables
- Creates indexes if they don't exist
- Works with both raw sqlite and SQLAlchemy
- Is SAFE to run repeatedly on container startup
"""

import os
import sys
import sqlite3
from sqlalchemy import text

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.api import app
from app.models import db

DEFAULT_DB_LOCATIONS = [
    "instance/chatbot.db",
    "chatbot.db",
    "app.db"
]

def find_database():
    """Locate SQLite DB file in common locations."""
    for path in DEFAULT_DB_LOCATIONS:
        if os.path.exists(path):
            return path
    return None


# =====================================================================================
# LOW-LEVEL SQLITE MIGRATION FUNCTIONS
# =====================================================================================

def add_sqlite_column(cursor, table, column, ddl):
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [c[1] for c in cursor.fetchall()]
    if column not in columns:
        print(f"✓ Adding column {column} to {table}")
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")
        return True
    else:
        print(f"○ {column} already exists in {table}")
        return False


# =====================================================================================
# SQLALCHEMY MIGRATION FUNCTIONS (chat_sessions, indexes, etc.)
# =====================================================================================

def safe_sqlalchemy_exec(engine, sql, label):
    """Safely run SQLAlchemy statements (SQLite compatible)."""
    try:
        engine.execute(text(sql))
        print(f"✓ {label}")
        return True
    except Exception:
        print(f"○ {label} already exists")
        return False


# =====================================================================================
# MIGRATION EXECUTION
# =====================================================================================

def run_sqlite_migrations(db_path):
    """Perform low-level migrations using sqlite3 directly."""
    print(f"\n--- Running SQLite-level migrations ---")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    changed = False

    # PROFILES TABLE
    changed |= add_sqlite_column(cur, "profiles", "display_name", "VARCHAR(100)")
    changed |= add_sqlite_column(cur, "profiles", "introduction", "TEXT")
    changed |= add_sqlite_column(cur, "profiles", "primary_resume_id", "INTEGER")

    # USERS TABLE
    changed |= add_sqlite_column(cur, "users", "email", "VARCHAR(120)")
    changed |= add_sqlite_column(cur, "users", "failed_login_attempts", "INTEGER DEFAULT 0")
    changed |= add_sqlite_column(cur, "users", "locked_until", "DATETIME")
    changed |= add_sqlite_column(cur, "users", "password_changed_at", "DATETIME")
    changed |= add_sqlite_column(cur, "users", "must_change_password", "BOOLEAN DEFAULT 0")
    changed |= add_sqlite_column(cur, "users", "last_login_at", "DATETIME")
    changed |= add_sqlite_column(cur, "users", "last_login_ip", "VARCHAR(45)")
    changed |= add_sqlite_column(cur, "users", "is_active", "BOOLEAN DEFAULT 1")

    changed |= add_sqlite_column(cur, "users", "is_active", "BOOLEAN DEFAULT 1")

    # Backfill default values for existing rows (critical for users table)
    # This logic comes from migrate_user_security.py
    if changed:
        print("   Performing data backfill for new columns...")
        cur.execute("UPDATE users SET failed_login_attempts = 0 WHERE failed_login_attempts IS NULL")
        cur.execute("UPDATE users SET is_active = 1 WHERE is_active IS NULL")
        cur.execute("UPDATE users SET must_change_password = 0 WHERE must_change_password IS NULL")
        cur.execute("UPDATE users SET password_changed_at = created_at WHERE password_changed_at IS NULL")

    conn.commit()
    conn.close()

    print("\nSQLite migrations completed." if changed else "\nSQLite already up to date.")
    return changed


def run_sqlalchemy_migrations():
    """Migrations requiring SQLAlchemy engine (e.g., indexes, chat_sessions)."""
    print("\n--- Running SQLAlchemy-powered migrations ---")
    with app.app_context():
        engine = db.engine
        changed = False

        changed |= safe_sqlalchemy_exec(
            engine,
            "ALTER TABLE chat_sessions ADD COLUMN user_identifier VARCHAR(100)",
            "chat_sessions.user_identifier",
        )

        changed |= safe_sqlalchemy_exec(
            engine,
            "ALTER TABLE chat_sessions ADD COLUMN title VARCHAR(255)",
            "chat_sessions.title",
        )

        changed |= safe_sqlalchemy_exec(
            engine,
            "CREATE INDEX ix_chat_sessions_user_identifier ON chat_sessions (user_identifier)",
            "index chat_sessions(user_identifier)"
        )

        db.session.commit()

    print("\nSQLAlchemy migrations completed.")
    return changed


# =====================================================================================
# ENTRY POINT
# =====================================================================================

def migrate():
    print("=== Starting Bootstrap Database Migration ===")

    db_path = find_database()
    if not db_path:
        print("No SQLite database found. Will be created automatically.")
        return

    print(f"Using database: {db_path}")

    run_sqlite_migrations(db_path)
    run_sqlalchemy_migrations()

    print("\n=== Bootstrap migration complete ===")


if __name__ == "__main__":
    migrate()
