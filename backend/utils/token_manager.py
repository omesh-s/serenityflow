"""Utility functions for managing OAuth tokens in database."""
from sqlalchemy.orm import Session
from database import OAuthToken
from datetime import datetime, timedelta
from typing import Optional, Dict
import json


def save_token(db: Session, service: str, access_token: str, refresh_token: Optional[str] = None, 
               expires_in: Optional[int] = None, user_info: Optional[Dict] = None):
    """Save OAuth token to database."""
    token_expiry = None
    if expires_in:
        token_expiry = datetime.utcnow() + timedelta(seconds=expires_in)
    
    # Serialize user_info to JSON if provided
    user_info_json = None
    if user_info:
        user_info_json = json.dumps(user_info)
    
    token = db.query(OAuthToken).filter(OAuthToken.id == service).first()
    
    if token:
        token.access_token = access_token
        token.refresh_token = refresh_token or token.refresh_token
        token.token_expiry = token_expiry
        if user_info_json is not None:
            token.user_info = user_info_json
        token.updated_at = datetime.utcnow()
    else:
        token = OAuthToken(
            id=service,
            access_token=access_token,
            refresh_token=refresh_token,
            token_expiry=token_expiry,
            user_info=user_info_json
        )
        db.add(token)
    
    db.commit()
    db.refresh(token)
    return token


def get_token(db: Session, service: str) -> Optional[OAuthToken]:
    """Get OAuth token from database."""
    return db.query(OAuthToken).filter(OAuthToken.id == service).first()


def delete_token(db: Session, service: str):
    """Delete OAuth token from database."""
    token = db.query(OAuthToken).filter(OAuthToken.id == service).first()
    if token:
        db.delete(token)
        db.commit()

