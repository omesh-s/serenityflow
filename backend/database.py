"""Database models and setup for Serenity backend."""
from sqlalchemy import create_engine, Column, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os
import json
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./serenity.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class OAuthToken(Base):
    """Store OAuth tokens for Google and Notion."""
    __tablename__ = "oauth_tokens"

    id = Column(String, primary_key=True)  # Format: "google" or "notion"
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=True)
    token_expiry = Column(DateTime, nullable=True)
    user_info = Column(Text, nullable=True)  # Store user info as JSON (first_name, email, etc.)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def init_db():
    """Initialize the database and create tables."""
    Base.metadata.create_all(bind=engine)
    
    # Migrate existing tables to add new columns if needed
    # This handles the case where user_info column was added after initial table creation
    try:
        from sqlalchemy import inspect, text
        inspector = inspect(engine)
        
        # Check if oauth_tokens table exists
        if 'oauth_tokens' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('oauth_tokens')]
            
            if 'user_info' not in columns:
                # Add user_info column to existing table
                with engine.connect() as conn:
                    conn.execute(text('ALTER TABLE oauth_tokens ADD COLUMN user_info TEXT'))
                    conn.commit()
                print("Added user_info column to oauth_tokens table")
    except Exception as e:
        # If migration fails, that's okay - the column might already exist or table might not exist yet
        # This is expected for new databases where the table doesn't exist yet
        pass


def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

