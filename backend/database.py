"""Database models and setup for Serenity backend."""
from sqlalchemy import create_engine, Column, String, DateTime, Text, Integer, Boolean, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os
import json
from dotenv import load_dotenv
from typing import Optional

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


class Story(Base):
    """Extracted stories/backlog items from meetings and notes."""
    __tablename__ = "stories"
    
    id = Column(String, primary_key=True)  # UUID or Notion page ID
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    priority = Column(String, nullable=True)  # "high", "medium", "low"
    status = Column(String, default="pending")  # "pending", "approved", "rejected", "archived"
    tags = Column(Text, nullable=True)  # JSON array of tags
    owner = Column(String, nullable=True)  # Owner/stakeholder name
    source_type = Column(String, nullable=False)  # "meeting", "notion", "calendar"
    source_id = Column(String, nullable=True)  # ID of source (meeting ID, Notion page ID, etc.)
    notion_page_id = Column(String, nullable=True)  # Notion page ID if created in Notion
    extracted_at = Column(DateTime, default=datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = Column(String, default="default")  # User identifier
    confidence = Column(Float, nullable=True)  # Confidence score (0-100) for auto-approval
    story_points = Column(Integer, nullable=True)  # Estimated story points
    product = Column(String, nullable=True)  # Product name (e.g., "SerenityFlow")
    sort_ranking = Column(Integer, nullable=True)  # Sort ranking for Notion database


class ChecklistItem(Base):
    """Items displayed in the frontend checklist."""
    __tablename__ = "checklist_items"
    
    id = Column(String, primary_key=True)  # UUID
    type = Column(String, nullable=False)  # "story_approval", "backlog_cleanup", "release_report", "stakeholder_action", "integration_status"
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String, default="pending")  # "pending", "resolved", "dismissed"
    priority = Column(String, default="medium")  # "high", "medium", "low"
    action_type = Column(String, nullable=True)  # "approve", "archive", "review", "re_authenticate", etc.
    action_data = Column(Text, nullable=True)  # JSON data for actions (e.g., story IDs, report URLs) - stored as JSON string
    meta_data = Column(Text, nullable=True)  # Additional metadata - stored as JSON string (renamed from metadata to avoid SQLAlchemy conflict)
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    user_id = Column(String, default="default")


class ReleaseReport(Base):
    """Automatically generated release reports."""
    __tablename__ = "release_reports"
    
    id = Column(String, primary_key=True)  # UUID
    title = Column(Text, nullable=False)
    content = Column(Text, nullable=False)  # Markdown content
    format = Column(String, default="markdown")  # "markdown", "pdf"
    status = Column(String, default="draft")  # "draft", "ready", "shared"
    story_ids = Column(Text, nullable=True)  # JSON array of story IDs included
    generated_at = Column(DateTime, default=datetime.utcnow)
    shared_at = Column(DateTime, nullable=True)
    file_path = Column(Text, nullable=True)  # Path to saved file if exported
    user_id = Column(String, default="default")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Stakeholder(Base):
    """Stakeholders mapped from stories and meetings."""
    __tablename__ = "stakeholders"
    
    id = Column(String, primary_key=True)  # UUID
    name = Column(String, nullable=False)
    email = Column(String, nullable=True)
    role = Column(String, nullable=True)
    open_actions = Column(Integer, default=0)
    overdue_actions = Column(Integer, default=0)
    blocked_actions = Column(Integer, default=0)
    last_activity = Column(DateTime, nullable=True)
    meta_data = Column(Text, nullable=True)  # Additional stakeholder data - stored as JSON string (renamed from metadata to avoid SQLAlchemy conflict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = Column(String, default="default")


class BacklogHealth(Base):
    """Backlog health metrics and audit results."""
    __tablename__ = "backlog_health"
    
    id = Column(String, primary_key=True)  # UUID
    health_score = Column(Float, nullable=False)  # 0-100 score
    total_stories = Column(Integer, default=0)
    duplicate_count = Column(Integer, default=0)
    low_priority_count = Column(Integer, default=0)
    outdated_count = Column(Integer, default=0)
    recommendations = Column(Text, nullable=True)  # JSON array of recommendations - stored as JSON string
    audit_date = Column(DateTime, default=datetime.utcnow)
    user_id = Column(String, default="default")
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    """Initialize the database and create tables.
    
    Handles migrations for:
    - Adding user_info column to oauth_tokens
    - Renaming metadata to meta_data (if needed)
    - Creating new automation tables
    """
    Base.metadata.create_all(bind=engine)
    
    # Migrate existing tables to add new columns if needed
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
                print("✓ Added user_info column to oauth_tokens table")
        
        # Handle metadata -> meta_data migration for existing tables
        # Check checklist_items table
        if 'checklist_items' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('checklist_items')]
            if 'metadata' in columns and 'meta_data' not in columns:
                # Rename metadata to meta_data
                with engine.connect() as conn:
                    # SQLite doesn't support RENAME COLUMN directly, so we need to recreate
                    # For now, just add meta_data column and copy data
                    conn.execute(text('ALTER TABLE checklist_items ADD COLUMN meta_data TEXT'))
                    conn.execute(text('UPDATE checklist_items SET meta_data = metadata'))
                    conn.commit()
                print("✓ Migrated metadata to meta_data in checklist_items table")
        
        # Check stakeholders table
        if 'stakeholders' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('stakeholders')]
            if 'metadata' in columns and 'meta_data' not in columns:
                with engine.connect() as conn:
                    conn.execute(text('ALTER TABLE stakeholders ADD COLUMN meta_data TEXT'))
                    conn.execute(text('UPDATE stakeholders SET meta_data = metadata'))
                    conn.commit()
                print("✓ Migrated metadata to meta_data in stakeholders table")
        
        # Ensure all new tables are created
        tables_to_create = ['stories', 'checklist_items', 'release_reports', 'stakeholders', 'backlog_health']
        existing_tables = inspector.get_table_names()
        
        for table_name in tables_to_create:
            if table_name not in existing_tables:
                print(f"Creating table: {table_name}")
        
        # Migrate stories table to add new columns if they don't exist
        if 'stories' in existing_tables:
            stories_columns = [col['name'] for col in inspector.get_columns('stories')]
            
            # Add confidence column
            if 'confidence' not in stories_columns:
                try:
                    with engine.connect() as conn:
                        conn.execute(text('ALTER TABLE stories ADD COLUMN confidence REAL'))
                        conn.commit()
                    print("✓ Added confidence column to stories table")
                except Exception as e:
                    print(f"⚠ Could not add confidence column: {str(e)}")
            
            # Add story_points column
            if 'story_points' not in stories_columns:
                try:
                    with engine.connect() as conn:
                        conn.execute(text('ALTER TABLE stories ADD COLUMN story_points INTEGER'))
                        conn.commit()
                    print("✓ Added story_points column to stories table")
                except Exception as e:
                    print(f"⚠ Could not add story_points column: {str(e)}")
            
            # Add product column
            if 'product' not in stories_columns:
                try:
                    with engine.connect() as conn:
                        conn.execute(text('ALTER TABLE stories ADD COLUMN product TEXT'))
                        conn.commit()
                    print("✓ Added product column to stories table")
                except Exception as e:
                    print(f"⚠ Could not add product column: {str(e)}")
            
            # Add sort_ranking column
            if 'sort_ranking' not in stories_columns:
                try:
                    with engine.connect() as conn:
                        conn.execute(text('ALTER TABLE stories ADD COLUMN sort_ranking INTEGER'))
                        conn.commit()
                    print("✓ Added sort_ranking column to stories table")
                except Exception as e:
                    print(f"⚠ Could not add sort_ranking column: {str(e)}")
        
        print("✓ Database initialization complete")
        
    except Exception as e:
        # If migration fails, that's okay - the column might already exist or table might not exist yet
        print(f"⚠ Migration check completed with warnings: {str(e)}")
        print("  This is normal for new databases. If you see errors, you may need to recreate the database.")
        import traceback
        traceback.print_exc()


def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

