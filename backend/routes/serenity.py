"""Serenity routes for break scheduling."""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from database import get_db
from utils.token_manager import get_token
from utils.google_calendar import get_upcoming_events
from utils.notion import get_notion_pages
from utils.gemini import generate_break_suggestions
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter()


class BreakSuggestion(BaseModel):
    """Break suggestion model."""
    time: str
    duration: int
    activity: str
    reason: str


class ScheduleResponse(BaseModel):
    """Schedule response model."""
    events: List[dict]
    pages: List[dict]
    break_suggestions: List[BreakSuggestion]


@router.get("/schedule", response_model=ScheduleResponse)
async def get_schedule(
    max_events: int = 10,
    max_pages: int = 10,
    db: Session = Depends(get_db)
):
    """Get schedule with break suggestions."""
    try:
        # Get tokens
        google_token = get_token(db, "google")
        notion_token = get_token(db, "notion")
        
        events = []
        pages = []
        
        # Fetch Google Calendar events
        if google_token:
            try:
                events, new_access_token = get_upcoming_events(
                    access_token=google_token.access_token,
                    refresh_token=google_token.refresh_token,
                    max_results=max_events
                )
                # Update token if it was refreshed
                if new_access_token:
                    from utils.token_manager import save_token
                    save_token(
                        db=db,
                        service="google",
                        access_token=new_access_token,
                        refresh_token=google_token.refresh_token,
                        expires_in=None  # Token expiry handled by Google
                    )
            except Exception as e:
                print(f"Error fetching Google Calendar events: {str(e)}")
                # Continue even if Google Calendar fails
        
        # Fetch Notion pages
        if notion_token:
            try:
                pages = get_notion_pages(
                    access_token=notion_token.access_token,
                    page_size=max_pages
                )
            except Exception as e:
                print(f"Error fetching Notion pages: {str(e)}")
                # Continue even if Notion fails
        
        # Generate break suggestions using Gemini
        break_suggestions = []
        if events or pages:
            try:
                suggestions = generate_break_suggestions(events, pages)
                break_suggestions = [BreakSuggestion(**s) for s in suggestions]
            except Exception as e:
                print(f"Error generating break suggestions: {str(e)}")
                # Return empty suggestions if Gemini fails
        
        return ScheduleResponse(
            events=events,
            pages=pages,
            break_suggestions=break_suggestions
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching schedule: {str(e)}")

