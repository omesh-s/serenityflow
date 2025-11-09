"""Utility functions for Google Calendar API."""
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
import os
from config import settings


SCOPES = [
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/userinfo.profile',
    'https://www.googleapis.com/auth/userinfo.email'
]


def get_google_oauth_flow(state: Optional[str] = None) -> Flow:
    """Create Google OAuth flow."""
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [settings.google_redirect_uri],
            }
        },
        scopes=SCOPES,
        redirect_uri=settings.google_redirect_uri
    )
    if state:
        flow.state = state
    return flow


def get_credentials_from_token(access_token: str, refresh_token: Optional[str] = None) -> Credentials:
    """Create Credentials object from stored tokens."""
    creds = Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        scopes=SCOPES
    )
    return creds


def refresh_credentials_if_needed(creds: Credentials) -> Tuple[Credentials, bool]:
    """Refresh credentials if they are expired.
    
    Returns:
        tuple: (Credentials, was_refreshed) - Updated credentials and whether they were refreshed
    """
    was_refreshed = False
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        was_refreshed = True
    return creds, was_refreshed


def get_upcoming_events(access_token: str, refresh_token: Optional[str] = None, max_results: int = 10) -> Tuple[List[Dict], Optional[str]]:
    """Fetch upcoming events from Google Calendar.
    
    Returns:
        tuple: (events, new_access_token) - List of events and new access token if refreshed
    """
    try:
        creds = get_credentials_from_token(access_token, refresh_token)
        creds, was_refreshed = refresh_credentials_if_needed(creds)
        new_access_token = creds.token if was_refreshed else None
        
        service = build('calendar', 'v3', credentials=creds)
        
        # Get events for the next 7 days
        now = datetime.utcnow()
        time_min = now.isoformat() + 'Z'
        time_max = (now + timedelta(days=7)).isoformat() + 'Z'
        
        events_result = service.events().list(
            calendarId='primary',
            timeMin=time_min,
            timeMax=time_max,
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        formatted_events = []
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            end = event['end'].get('dateTime', event['end'].get('date'))
            
            formatted_events.append({
                'id': event.get('id'),
                'summary': event.get('summary', 'No Title'),
                'description': event.get('description', ''),
                'start': start,
                'end': end,
                'location': event.get('location', ''),
                'attendees': len(event.get('attendees', [])),
                'htmlLink': event.get('htmlLink', ''),
            })
        
        return formatted_events, new_access_token
    except Exception as e:
        print(f"Error fetching Google Calendar events: {str(e)}")
        raise


def get_calendar_service(access_token: str, refresh_token: Optional[str] = None) -> Tuple[Any, Optional[str]]:
    """Get a Google Calendar service instance.
    
    Returns:
        tuple: (service, new_access_token) - Calendar service and new access token if refreshed
    """
    creds = get_credentials_from_token(access_token, refresh_token)
    creds, was_refreshed = refresh_credentials_if_needed(creds)
    new_access_token = creds.token if was_refreshed else None
    service = build('calendar', 'v3', credentials=creds)
    return service, new_access_token

