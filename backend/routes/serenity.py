"""Serenity routes for break scheduling."""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from database import get_db
from utils.token_manager import get_token
from utils.google_calendar import get_upcoming_events
from utils.notion import get_notion_pages
from utils.gemini import generate_break_suggestions
from utils.wellness_analyzer import analyze_wellness
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

router = APIRouter()


class BreakSuggestion(BaseModel):
    """Break suggestion model."""
    id: Optional[str] = None
    time: str
    duration: int
    activity: str
    reason: str
    description: Optional[str] = None
    icon: Optional[str] = None
    custom: bool = False


class WellnessMetrics(BaseModel):
    """Wellness metrics model."""
    wellness_score: float
    completion_rate: float
    peak_productivity_hours: str
    insights: List[str]
    engagement_score: Optional[float] = 0.0
    active_days: Optional[int] = 0
    total_notes: Optional[int] = 0
    current_state: Optional[str] = "neutral"
    trend: Optional[str] = "stable"


class ScheduleResponse(BaseModel):
    """Schedule response model."""
    events: List[dict]
    pages: List[dict]
    break_suggestions: List[BreakSuggestion]
    wellness_metrics: Optional[WellnessMetrics] = None


@router.get("/schedule", response_model=ScheduleResponse)
async def get_schedule(
    max_events: int = 10,
    max_pages: int = 10,
    timezone: Optional[str] = None,  # User's timezone preference
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
                # Sort events by start time to ensure consistent ordering
                # This is critical for stable break generation
                events = sorted(events, key=lambda e: (e.get('start', ''), e.get('id', '')))
                
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
                # Fetch more pages for wellness analysis (up to 50)
                wellness_page_count = min(50, max(max_pages * 5, 20))
                pages = get_notion_pages(
                    access_token=notion_token.access_token,
                    page_size=wellness_page_count
                )
            except Exception as e:
                print(f"Error fetching Notion pages: {str(e)}")
                # Continue even if Notion fails
        
        # Generate break suggestions (always generate, cache is optional)
        break_suggestions = []
        if events:
            try:
                # Always generate breaks (caching happens inside generate_break_suggestions if needed)
                # Use user's timezone if provided, otherwise default to UTC
                user_tz = timezone or 'UTC'
                suggestions = generate_break_suggestions(events, pages, user_timezone=user_tz)
                
                # Enhance suggestions with break type metadata
                from utils.break_types import get_break_type
                enhanced_suggestions = []
                for s in suggestions:
                    break_type = get_break_type(s.get('activity', 'meditation'))
                    # Generate stable ID based on time
                    import hashlib
                    time_str = s.get('time', '')
                    break_id = hashlib.md5(time_str.encode()).hexdigest()[:8] if time_str else f"break_{len(enhanced_suggestions)}"
                    
                    enhanced_suggestions.append({
                        **s,
                        'id': s.get('id') or break_id,
                        'icon': break_type.get('icon', '🧘'),
                        'description': s.get('description') or break_type.get('description', ''),
                    })
                
                break_suggestions = [BreakSuggestion(**s) for s in enhanced_suggestions]
            except Exception as e:
                print(f"Error generating break suggestions: {str(e)}")
                import traceback
                traceback.print_exc()
                # Don't return empty - let automatic breaks work even if Gemini fails
        
        # Merge with user customizations (if any)
        # Note: In production, this should fetch from database
        # For now, customizations are stored in-memory in breaks route
        try:
            import sys
            breaks_module = sys.modules.get('routes.breaks')
            if breaks_module and hasattr(breaks_module, '_break_customizations'):
                user_id = "default"  # In production, get from auth
                custom_breaks = breaks_module._break_customizations.get(user_id, [])
                if custom_breaks:
                    # Replace or add custom breaks
                    for custom_break in custom_breaks:
                        # Find if this break already exists (by time proximity or ID)
                        existing_index = None
                        custom_id = custom_break.get('id')
                        custom_time_str = custom_break.get('time', '')
                        
                        if custom_id:
                            # Try to find by ID first
                            for i, existing in enumerate(break_suggestions):
                                if hasattr(existing, 'id') and existing.id == custom_id:
                                    existing_index = i
                                    break
                        
                        if existing_index is None and custom_time_str:
                            # Find by time proximity (within 5 minutes)
                            try:
                                custom_time = datetime.fromisoformat(custom_time_str.replace('Z', '+00:00'))
                                for i, existing in enumerate(break_suggestions):
                                    existing_time = datetime.fromisoformat(existing.time.replace('Z', '+00:00'))
                                    time_diff = abs((custom_time - existing_time).total_seconds())
                                    if time_diff < 300:  # Within 5 minutes
                                        existing_index = i
                                        break
                            except Exception:
                                pass
                        
                        if existing_index is not None:
                            # Replace existing break
                            break_suggestions[existing_index] = BreakSuggestion(**custom_break)
                        else:
                            # Add new custom break
                            break_suggestions.append(BreakSuggestion(**custom_break))
                    
                    # Remove duplicates before sorting
                    # Use a dict to track breaks by ID or time
                    unique_breaks_dict = {}
                    for break_item in break_suggestions:
                        break_id = break_item.id if hasattr(break_item, 'id') else None
                        break_time = break_item.time if hasattr(break_item, 'time') else ''
                        
                        # Use ID as primary key, or time as fallback
                        key = break_id or break_time
                        if key and key not in unique_breaks_dict:
                            unique_breaks_dict[key] = break_item
                    
                    # Convert back to list and sort by time
                    break_suggestions = list(unique_breaks_dict.values())
                    break_suggestions.sort(key=lambda x: x.time if hasattr(x, 'time') else '')
        except Exception as e:
            print(f"Error merging custom breaks: {str(e)}")
            import traceback
            traceback.print_exc()
            # Continue without customizations if merge fails
        
        # Analyze wellness metrics from Notion pages
        # Use cached wellness data if available to reduce Gemini API calls
        wellness_metrics = None
        if pages and notion_token:
            try:
                from utils.wellness_cache import get_cached_wellness, set_cached_wellness, get_notes_fingerprint
                
                # Generate fingerprint to check if notes changed
                notes_fingerprint = get_notes_fingerprint(pages)
                cache_key = f"wellness_{notion_token.id}"
                is_cached, cached_data = get_cached_wellness(cache_key, notes_fingerprint)
                
                if is_cached:
                    # Use cached data
                    wellness_data = cached_data
                else:
                    # Analyze wellness (will be cached by wellness route)
                    wellness_data = analyze_wellness(pages)
                    # Cache it with fingerprint
                    set_cached_wellness(cache_key, wellness_data, notes_fingerprint)
                
                wellness_metrics = WellnessMetrics(
                    wellness_score=wellness_data.get("wellness_score", 50.0),
                    completion_rate=wellness_data.get("completion_rate", 0.0),
                    peak_productivity_hours=wellness_data.get("peak_productivity_hours", "No data available"),
                    insights=wellness_data.get("insights", []),
                    engagement_score=wellness_data.get("engagement_score", 0.0),
                    active_days=wellness_data.get("active_days", 0),
                    total_notes=len(pages),
                    current_state=wellness_data.get("current_state", "neutral"),
                    trend=wellness_data.get("trend", "stable")
                )
            except Exception as e:
                print(f"Error analyzing wellness metrics: {str(e)}")
                import traceback
                traceback.print_exc()
                # Continue without wellness metrics if analysis fails
        
        return ScheduleResponse(
            events=events,
            pages=pages,
            break_suggestions=break_suggestions,
            wellness_metrics=wellness_metrics
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching schedule: {str(e)}")

