from app.api import app
from app.models import db
from sqlalchemy import text

with app.app_context():
    with db.engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE chat_sessions ADD COLUMN user_identifier VARCHAR(100)"))
            print("Added user_identifier")
        except Exception as e:
            print(f"user_identifier error (probably exists): {e}")
            
        try:
            conn.execute(text("ALTER TABLE chat_sessions ADD COLUMN title VARCHAR(255)"))
            print("Added title")
        except Exception as e:
            print(f"title error (probably exists): {e}")
        
        try:
            conn.execute(text("CREATE INDEX ix_chat_sessions_user_identifier ON chat_sessions (user_identifier)"))
            print("Added index")
        except Exception as e:
            print(f"index error (probably exists): {e}")
            
    db.session.commit()
