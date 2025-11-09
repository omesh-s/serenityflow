"""Wellness analytics routes."""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from database import get_db
from utils.token_manager import get_token
from utils.notion import get_notion_pages
from utils.wellness_analyzer import analyze_wellness
from pydantic import BaseModel
from typing import List, Optional
from utils.wellness_cache import get_cached_wellness, set_cached_wellness

router = APIRouter()


class WellnessResponse(BaseModel):
    """Wellness response model."""
    wellness_score: float
    completion_rate: float
    peak_productivity_hours: str
    insights: List[str]
    total_notes: int
    analyzed_notes: int
    engagement_score: float
    active_days: int
    current_state: str
    trend: str


@router.get("", response_model=WellnessResponse)
async def get_wellness_metrics(
    max_notes: int = 50,
    db: Session = Depends(get_db)
):
    """Get wellness metrics from Notion notes with caching to reduce API calls."""
    try:
        # Get Notion token
        notion_token = get_token(db, "notion")
        
        if not notion_token:
            raise HTTPException(
                status_code=401, 
                detail="Notion not connected. Please connect your Notion account first."
            )
        
        # Fetch Notion pages first to get fingerprint
        try:
            pages = get_notion_pages(
                access_token=notion_token.access_token,
                page_size=max_notes
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error fetching Notion pages: {str(e)}"
            )
        
        # Generate fingerprint based on notes (so cache invalidates when notes change)
        from utils.wellness_cache import get_notes_fingerprint
        try:
            notes_fingerprint = get_notes_fingerprint(pages)
        except Exception as e:
            print(f"Error generating fingerprint: {str(e)}")
            notes_fingerprint = None  # Fallback if fingerprint generation fails
        
        # Check cache with fingerprint
        cache_key = f"wellness_{notion_token.id}"
        is_cached, cached_data = get_cached_wellness(cache_key, notes_fingerprint)
        if is_cached:
            # Return cached result
            return WellnessResponse(**cached_data)
        
        if not pages:
            # Return default metrics if no pages
            result = WellnessResponse(
                wellness_score=50.0,
                completion_rate=0.0,
                peak_productivity_hours="No data available",
                insights=["No notes found. Start tracking tasks in Notion to get wellness insights."],
                total_notes=0,
                analyzed_notes=0,
                engagement_score=0.0,
                active_days=0,
                current_state="neutral",
                trend="stable"
            )
            # Cache the result with fingerprint
            set_cached_wellness(cache_key, result.dict(), notes_fingerprint)
            return result
        
        # Analyze wellness
        try:
            wellness_data = analyze_wellness(pages)
            result = WellnessResponse(
                wellness_score=wellness_data.get("wellness_score", 50.0),
                completion_rate=wellness_data.get("completion_rate", 0.0),
                peak_productivity_hours=wellness_data.get("peak_productivity_hours", "No data available"),
                insights=wellness_data.get("insights", []),
                total_notes=len(pages),
                analyzed_notes=len(pages),
                engagement_score=wellness_data.get("engagement_score", 0.0),
                active_days=wellness_data.get("active_days", 0),
                current_state=wellness_data.get("current_state", "neutral"),
                trend=wellness_data.get("trend", "stable")
            )
            # Cache the result with fingerprint (so it only changes when notes change)
            set_cached_wellness(cache_key, result.dict(), notes_fingerprint)
            return result
        except Exception as e:
            print(f"Error in wellness analysis: {str(e)}")
            import traceback
            traceback.print_exc()
            # Return default result instead of raising error, so frontend doesn't break
            result = WellnessResponse(
                wellness_score=50.0,
                completion_rate=0.0,
                peak_productivity_hours="No data available",
                insights=["Unable to analyze wellness metrics at this time"],
                total_notes=len(pages) if pages else 0,
                analyzed_notes=0,
                engagement_score=0.0,
                active_days=0,
                current_state="neutral",
                trend="stable"
            )
            return result
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching wellness metrics: {str(e)}")

