"""Configuration settings for Serenity backend."""
import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Load .env from backend directory or parent directory
backend_dir = Path(__file__).parent
env_file = backend_dir / ".env"
parent_env_file = backend_dir.parent / ".env"

if env_file.exists():
    load_dotenv(env_file)
elif parent_env_file.exists():
    load_dotenv(parent_env_file)
else:
    load_dotenv()  # Try default locations


class Settings(BaseSettings):
    """Application settings."""
    
    # Google OAuth
    google_client_id: str = os.getenv("GOOGLE_CLIENT_ID", "")
    google_client_secret: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    google_redirect_uri: str = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback")
    
    # Notion OAuth
    notion_client_id: str = os.getenv("NOTION_CLIENT_ID", "")
    notion_client_secret: str = os.getenv("NOTION_CLIENT_SECRET", "")
    notion_redirect_uri: str = os.getenv("NOTION_REDIRECT_URI", "http://localhost:8000/auth/notion/callback")
    
    # API Keys
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    elevenlabs_api_key: str = os.getenv("ELEVENLABS_API_KEY", "")
    
    # Database
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./serenity.db")
    
    # Security
    secret_key: str = os.getenv("SECRET_KEY", "change-this-in-production")
    algorithm: str = os.getenv("ALGORITHM", "HS256")
    
    class Config:
        env_file = ".env"


settings = Settings()

