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
        
        # Fetch user info from Google
        user_info = None
        try:
            from googleapiclient.discovery import build
            service = build('oauth2', 'v2', credentials=credentials)
            user_info = service.userinfo().get().execute()
            print(f"Successfully fetched user info: {user_info.get('given_name', 'N/A')} ({user_info.get('email', 'N/A')})")
        except Exception as e:
            print(f"Error fetching user info in callback: {str(e)}")
            import traceback
            traceback.print_exc()
            # Continue even if user info fetch fails - tokens are still saved
        
        # Save tokens to database
        save_token(
            db=db,
            service="google",
            access_token=credentials.token,
            refresh_token=credentials.refresh_token,
            expires_in=expires_in,
            user_info=user_info  # Pass user info to save_token
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
    import json
    from utils.google_calendar import get_credentials_from_token, refresh_credentials_if_needed
    from googleapiclient.discovery import build
    
    google_token = get_token(db, "google")
    notion_token = get_token(db, "notion")
    
    google_status = {"connected": google_token is not None}
    user_info = None
    
    # If Google is connected, fetch user info
    if google_token:
        try:
            # Try to get user info from database first
            if hasattr(google_token, 'user_info') and google_token.user_info:
                try:
                    user_info = json.loads(google_token.user_info)
                    print(f"Loaded user info from database: {user_info.get('given_name', 'N/A')}")
                except json.JSONDecodeError as e:
                    print(f"Error parsing user_info from database: {str(e)}")
                    user_info = None
            
            # If no user info in database, fetch from Google API
            if not user_info:
                print("User info not in database, fetching from Google API...")
                try:
                    creds = get_credentials_from_token(google_token.access_token, google_token.refresh_token)
                    creds, _ = refresh_credentials_if_needed(creds)
                    service = build('oauth2', 'v2', credentials=creds)
                    user_info = service.userinfo().get().execute()
                    print(f"Fetched user info from Google: {user_info.get('given_name', 'N/A')}")
                    
                    # Save user info to database
                    if user_info:
                        try:
                            from utils.token_manager import save_token
                            save_token(
                                db=db,
                                service="google",
                                access_token=google_token.access_token,
                                refresh_token=google_token.refresh_token,
                                expires_in=None,
                                user_info=user_info
                            )
                            print("Saved user info to database")
                        except Exception as save_error:
                            print(f"Error saving user info to database: {str(save_error)}")
                except Exception as api_error:
                    error_msg = str(api_error)
                    print(f"Error fetching user info from Google API: {error_msg}")
                    
                    # Check if error is due to insufficient scopes
                    if "insufficient" in error_msg.lower() or "scope" in error_msg.lower() or "403" in error_msg:
                        print("NOTE: Token doesn't have userinfo scopes. User needs to re-authenticate to get first name.")
                        print("This is normal if user authenticated before we added userinfo scopes.")
                    else:
                        import traceback
                        traceback.print_exc()
        except Exception as e:
            print(f"Error in auth_status: {str(e)}")
            import traceback
            traceback.print_exc()
        
        # Always include user info if we have it
        if user_info:
            google_status["user"] = {
                "name": user_info.get("name", ""),
                "given_name": user_info.get("given_name", ""),  # First name
                "family_name": user_info.get("family_name", ""),  # Last name
                "email": user_info.get("email", ""),
                "picture": user_info.get("picture", "")
            }
            print(f"✓ Returning user info: given_name='{google_status['user'].get('given_name')}', name='{google_status['user'].get('name')}'")
        else:
            print("⚠ No user info available - user may need to re-authenticate to get new scopes")
    
    return {
        "google": google_status,
        "notion": {"connected": notion_token is not None}
    }


@router.post("/disconnect/{service}")
async def disconnect_service(service: str, db: Session = Depends(get_db)):
    """Disconnect a service (Google or Notion)."""
    if service not in ["google", "notion"]:
        raise HTTPException(status_code=400, detail="Invalid service. Must be 'google' or 'notion'")
    
    delete_token(db, service)
    return {"message": f"{service} disconnected successfully"}

