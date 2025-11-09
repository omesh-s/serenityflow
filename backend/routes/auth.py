"""OAuth routes for Google and Notion."""
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from database import get_db
from utils.google_calendar import get_google_oauth_flow
from utils.token_manager import save_token, get_token, delete_token
from config import settings
import requests
from urllib.parse import urlencode
from datetime import datetime

router = APIRouter()


@router.get("/google")
async def google_auth(request: Request):
    """Initiate Google OAuth flow."""
    try:
        flow = get_google_oauth_flow()
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        # Store state in session or return it to frontend
        return {"authorization_url": authorization_url, "state": state}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error initiating Google OAuth: {str(e)}")


@router.get("/google/callback")
async def google_callback(request: Request, code: str = None, state: str = None, db: Session = Depends(get_db)):
    """Handle Google OAuth callback."""
    if not code:
        raise HTTPException(status_code=400, detail="Authorization code not provided")
    
    try:
        flow = get_google_oauth_flow(state)
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        # Calculate expires_in in seconds
        expires_in = None
        if credentials.expiry:
            expires_in = int((credentials.expiry - datetime.utcnow()).total_seconds())
        
        # Save tokens to database
        save_token(
            db=db,
            service="google",
            access_token=credentials.token,
            refresh_token=credentials.refresh_token,
            expires_in=expires_in
        )
        
        # Redirect to frontend with success
        return RedirectResponse(url=f"http://localhost:3000/auth/callback?service=google&success=true")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error completing Google OAuth: {str(e)}")


@router.get("/notion")
async def notion_auth(request: Request):
    """Initiate Notion OAuth flow."""
    try:
        params = {
            "client_id": settings.notion_client_id,
            "redirect_uri": settings.notion_redirect_uri,
            "response_type": "code",
            "owner": "user",
        }
        authorization_url = f"https://api.notion.com/v1/oauth/authorize?{urlencode(params)}"
        return {"authorization_url": authorization_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error initiating Notion OAuth: {str(e)}")


@router.get("/notion/callback")
async def notion_callback(request: Request, code: str = None, error: str = None, db: Session = Depends(get_db)):
    """Handle Notion OAuth callback."""
    if error:
        raise HTTPException(status_code=400, detail=f"OAuth error: {error}")
    
    if not code:
        raise HTTPException(status_code=400, detail="Authorization code not provided")
    
    try:
        # Exchange code for access token
        token_url = "https://api.notion.com/v1/oauth/token"
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": settings.notion_redirect_uri,
        }
        auth = (settings.notion_client_id, settings.notion_client_secret)
        
        response = requests.post(token_url, data=data, auth=auth)
        response.raise_for_status()
        
        token_data = response.json()
        access_token = token_data.get("access_token")
        
        # Save token to database
        save_token(
            db=db,
            service="notion",
            access_token=access_token,
            refresh_token=None,  # Notion doesn't provide refresh tokens in the same way
            expires_in=None
        )
        
        # Redirect to frontend with success
        return RedirectResponse(url=f"http://localhost:3000/auth/callback?service=notion&success=true")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error completing Notion OAuth: {str(e)}")


@router.get("/status")
async def auth_status(db: Session = Depends(get_db)):
    """Check OAuth connection status for Google and Notion."""
    google_token = get_token(db, "google")
    notion_token = get_token(db, "notion")
    
    return {
        "google": {"connected": google_token is not None},
        "notion": {"connected": notion_token is not None}
    }


@router.post("/disconnect/{service}")
async def disconnect_service(service: str, db: Session = Depends(get_db)):
    """Disconnect a service (Google or Notion)."""
    if service not in ["google", "notion"]:
        raise HTTPException(status_code=400, detail="Invalid service. Must be 'google' or 'notion'")
    
    delete_token(db, service)
    return {"message": f"{service} disconnected successfully"}

