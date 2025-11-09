"""Integration health monitoring for external services."""
from typing import Dict, List, Optional, Any
from database import get_db
from utils.token_manager import get_token
from utils.notion import get_notion_pages
from utils.google_calendar import get_upcoming_events
from utils.gemini import initialize_gemini
from config import settings
import requests


def check_integration_health(user_id: str = "default", db=None) -> Dict[str, Any]:
    """Check health status of all integrations.
    
    Args:
        user_id: User identifier
        db: Database session (if None, creates a new one)
    
    Returns:
        Dict with health status for each integration
    """
    if db is None:
        from database import SessionLocal
        db = SessionLocal()
        should_close = True
    else:
        should_close = False
    
    try:
        health = {
            "notion": check_notion_health(db),
            "google_calendar": check_google_calendar_health(db),
            "gemini": check_gemini_health(),
            "overall": "healthy"
        }
        
        # Determine overall health
        issues = []
        if not health["notion"]["connected"]:
            issues.append("notion")
        if not health["google_calendar"]["connected"]:
            issues.append("google_calendar")
        if not health["gemini"]["available"]:
            issues.append("gemini")
        
        if issues:
            health["overall"] = "degraded"
            health["issues"] = issues
        
        return health
    
    finally:
        if should_close:
            db.close()


def check_notion_health(db) -> Dict[str, Any]:
    """Check Notion integration health.
    
    Args:
        db: Database session
    
    Returns:
        Dict with Notion health status
    """
    notion_token = get_token(db, "notion")
    
    if not notion_token:
        return {
            "connected": False,
            "status": "not_connected",
            "message": "Notion not connected. Please connect your Notion account.",
            "action_required": "re_authenticate"
        }
    
    # Test API access
    try:
        pages = get_notion_pages(notion_token.access_token, page_size=100)
        total_pages = len(pages)
        
        # Check if we might be missing pages due to permissions
        warning = None
        if total_pages < 10:
            warning = f"Only {total_pages} pages accessible. Make sure all pages are shared with the integration."
        
        return {
            "connected": True,
            "status": "healthy",
            "message": "Notion connected and accessible",
            "pages_accessible": total_pages,
            "warning": warning
        }
    except Exception as e:
        return {
            "connected": True,
            "status": "error",
            "message": f"Notion API error: {str(e)}",
            "action_required": "re_authenticate"
        }


def check_google_calendar_health(db) -> Dict[str, Any]:
    """Check Google Calendar integration health.
    
    Args:
        db: Database session
    
    Returns:
        Dict with Google Calendar health status
    """
    google_token = get_token(db, "google")
    
    if not google_token:
        return {
            "connected": False,
            "status": "not_connected",
            "message": "Google Calendar not connected. Please connect your Google account.",
            "action_required": "re_authenticate"
        }
    
    # Test API access
    try:
        events, _ = get_upcoming_events(google_token.access_token, google_token.refresh_token, max_results=1)
        return {
            "connected": True,
            "status": "healthy",
            "message": "Google Calendar connected and accessible",
            "events_accessible": len(events) > 0
        }
    except Exception as e:
        return {
            "connected": True,
            "status": "error",
            "message": f"Google Calendar API error: {str(e)}",
            "action_required": "re_authenticate"
        }


def check_gemini_health() -> Dict[str, Any]:
    """Check Gemini API health.
    
    Returns:
        Dict with Gemini health status
    """
    if not settings.gemini_api_key:
        return {
            "available": False,
            "status": "not_configured",
            "message": "Gemini API key not configured",
            "action_required": "configure_api_key"
        }
    
    try:
        initialize_gemini()
        # Simple test - try to create a model instance
        import google.generativeai as genai
        # Use gemini-2.5-flash for good balance of speed and quality
        model = genai.GenerativeModel('gemini-2.5-flash')
        return {
            "available": True,
            "status": "healthy",
            "message": "Gemini API available"
        }
    except Exception as e:
        return {
            "available": False,
            "status": "error",
            "message": f"Gemini API error: {str(e)}",
            "action_required": "check_api_key"
        }


def create_integration_checklist_items(db, user_id: str = "default"):
    """Create checklist items for integration health issues.
    
    Only creates new items if there isn't already a pending item for the same issue.
    This prevents duplicate checklist items on every health check.
    
    Args:
        db: Database session
        user_id: User identifier
    
    Returns:
        List of created checklist item IDs
    """
    from database import ChecklistItem
    import uuid
    from datetime import datetime
    import json
    
    health = check_integration_health(user_id, db)
    checklist_item_ids = []
    
    # Check Notion
    if not health["notion"]["connected"] or health["notion"]["status"] == "error":
        # Check if there's already a pending item for Notion
        existing = db.query(ChecklistItem).filter(
            ChecklistItem.user_id == user_id,
            ChecklistItem.type == "integration_status",
            ChecklistItem.status == "pending",
            ChecklistItem.action_data.like('%notion%')
        ).first()
        
        if not existing:
            item = ChecklistItem(
                id=str(uuid.uuid4()),
                type="integration_status",
                title="Notion Integration Issue",
                description=health["notion"]["message"],
                status="pending",
                priority="high",
                action_type="re_authenticate",
                action_data=json.dumps({"service": "notion"}),
                meta_data=None,
                user_id=user_id,
                created_at=datetime.utcnow()
            )
            db.add(item)
            checklist_item_ids.append(item.id)
    
    # Check Google Calendar
    if not health["google_calendar"]["connected"] or health["google_calendar"]["status"] == "error":
        # Check if there's already a pending item for Google Calendar
        existing = db.query(ChecklistItem).filter(
            ChecklistItem.user_id == user_id,
            ChecklistItem.type == "integration_status",
            ChecklistItem.status == "pending",
            ChecklistItem.action_data.like('%google%')
        ).first()
        
        if not existing:
            item = ChecklistItem(
                id=str(uuid.uuid4()),
                type="integration_status",
                title="Google Calendar Integration Issue",
                description=health["google_calendar"]["message"],
                status="pending",
                priority="high",
                action_type="re_authenticate",
                action_data=json.dumps({"service": "google"}),
                meta_data=None,
                user_id=user_id,
                created_at=datetime.utcnow()
            )
            db.add(item)
            checklist_item_ids.append(item.id)
    
    # Check Gemini
    if not health["gemini"]["available"]:
        # Check if there's already a pending item for Gemini
        existing = db.query(ChecklistItem).filter(
            ChecklistItem.user_id == user_id,
            ChecklistItem.type == "integration_status",
            ChecklistItem.status == "pending",
            ChecklistItem.action_data.like('%gemini%')
        ).first()
        
        if not existing:
            item = ChecklistItem(
                id=str(uuid.uuid4()),
                type="integration_status",
                title="Gemini API Issue",
                description=health["gemini"]["message"],
                status="pending",
                priority="medium",
                action_type="configure_api_key",
                action_data=json.dumps({"service": "gemini"}),
                meta_data=None,
                user_id=user_id,
                created_at=datetime.utcnow()
            )
            db.add(item)
            checklist_item_ids.append(item.id)
    
    if checklist_item_ids:
        try:
            db.commit()
        except Exception as e:
            print(f"Error creating integration checklist items: {str(e)}")
            db.rollback()
    
    return checklist_item_ids

