"""API routes for checklist and automation."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import json
from database import get_db, ChecklistItem, Story, ReleaseReport, Stakeholder, BacklogHealth
from utils.agents import StoryExtractionAgent, NoiseClearingAgent, ReleaseReportAgent, StakeholderAgent

router = APIRouter()


class ChecklistItemResponse(BaseModel):
    """Checklist item response model."""
    id: str
    type: str
    title: str
    description: Optional[str]
    status: str
    priority: str
    action_type: Optional[str]
    action_data: Optional[Dict[str, Any]]
    metadata: Optional[Dict[str, Any]]
    created_at: str
    resolved_at: Optional[str]




class StoryActionRequest(BaseModel):
    """Request model for story actions."""
    story_ids: List[str]
    action: str  # "approve", "reject", "archive"


class ChecklistActionRequest(BaseModel):
    """Request model for checklist actions."""
    action: str  # "resolve", "dismiss"
    action_data: Optional[Dict[str, Any]] = None


@router.get("", response_model=List[ChecklistItemResponse])
async def get_checklist(
    user_id: str = "default",
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get checklist items for the user.
    
    Args:
        user_id: User identifier
        status: Filter by status (pending, resolved, dismissed). If None, returns all items.
        db: Database session
    
    Returns:
        List of checklist items
    """
    query = db.query(ChecklistItem).filter(ChecklistItem.user_id == user_id)
    
    if status:
        query = query.filter(ChecklistItem.status == status)
    # If status is None, return all items (not just pending)
    
    items = query.order_by(ChecklistItem.created_at.desc()).limit(100).all()
    
    # Parse JSON fields
    checklist_items = []
    for item in items:
        action_data = None
        metadata = None
        
        if item.action_data:
            try:
                action_data = json.loads(item.action_data)
            except:
                pass
        
        if item.meta_data:
            try:
                metadata = json.loads(item.meta_data)
            except:
                pass
        
        checklist_items.append(ChecklistItemResponse(
            id=item.id,
            type=item.type,
            title=item.title,
            description=item.description,
            status=item.status,
            priority=item.priority,
            action_type=item.action_type,
            action_data=action_data,
            metadata=metadata,
            created_at=item.created_at.isoformat() if item.created_at else "",
            resolved_at=item.resolved_at.isoformat() if item.resolved_at else None
        ))
    
    return checklist_items


@router.post("/stories/action")
async def approve_stories(
    request: StoryActionRequest,
    user_id: str = "default",
    db: Session = Depends(get_db)
):
    """Approve, reject, or archive stories (batch action).
    
    Args:
        request: Story action request with story_ids and action (approve/reject/archive)
        user_id: User identifier
        db: Database session
    
    Returns:
        Action result with counts and details
    """
    if not request.story_ids:
        raise HTTPException(status_code=400, detail="No story IDs provided")
    
    if request.action == "approve":
        # Use story extraction agent to approve stories
        agent = StoryExtractionAgent(db, user_id)
        result = agent.approve_stories(request.story_ids, create_in_notion=True)
        
        # Resolve related checklist items
        checklist_items = db.query(ChecklistItem).filter(
            ChecklistItem.user_id == user_id,
            ChecklistItem.type == "story_approval",
            ChecklistItem.status == "pending"
        ).all()
        
        resolved_count = 0
        for item in checklist_items:
            if item.action_data:
                try:
                    action_data = json.loads(item.action_data)
                    item_story_ids = action_data.get("story_ids", [])
                    # Check if any of the approved stories are in this checklist item
                    if set(item_story_ids) & set(request.story_ids):
                        item.status = "resolved"
                        item.resolved_at = datetime.utcnow()
                        resolved_count += 1
                except:
                    pass
        
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Error committing changes: {str(e)}")
        
        return {
            "success": result.get("success", True),
            "approved": result.get("approved", 0),
            "created_in_notion": result.get("created_in_notion", []),
            "checklist_items_resolved": resolved_count,
            "errors": result.get("errors", []),
            "warning": result.get("warning")
        }
    
    elif request.action == "reject":
        # Mark stories as rejected
        stories = db.query(Story).filter(
            Story.id.in_(request.story_ids),
            Story.user_id == user_id
        ).all()
        
        for story in stories:
            story.status = "rejected"
            story.updated_at = datetime.utcnow()
        
        # Resolve related checklist items
        checklist_items = db.query(ChecklistItem).filter(
            ChecklistItem.user_id == user_id,
            ChecklistItem.type == "story_approval",
            ChecklistItem.status == "pending"
        ).all()
        
        resolved_count = 0
        for item in checklist_items:
            if item.action_data:
                try:
                    action_data = json.loads(item.action_data)
                    item_story_ids = action_data.get("story_ids", [])
                    if set(item_story_ids) & set(request.story_ids):
                        item.status = "resolved"
                        item.resolved_at = datetime.utcnow()
                        resolved_count += 1
                except:
                    pass
        
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Error committing changes: {str(e)}")
        
        return {
            "success": True,
            "rejected": len(stories),
            "checklist_items_resolved": resolved_count
        }
    
    elif request.action == "archive":
        # Mark stories as archived
        stories = db.query(Story).filter(
            Story.id.in_(request.story_ids),
            Story.user_id == user_id
        ).all()
        
        for story in stories:
            story.status = "archived"
            story.updated_at = datetime.utcnow()
        
        # Resolve related checklist items
        checklist_items = db.query(ChecklistItem).filter(
            ChecklistItem.user_id == user_id,
            ChecklistItem.type.in_(["story_approval", "backlog_cleanup"]),
            ChecklistItem.status == "pending"
        ).all()
        
        resolved_count = 0
        for item in checklist_items:
            if item.action_data:
                try:
                    action_data = json.loads(item.action_data)
                    item_story_ids = action_data.get("story_ids", [])
                    if set(item_story_ids) & set(request.story_ids):
                        item.status = "resolved"
                        item.resolved_at = datetime.utcnow()
                        resolved_count += 1
                except:
                    pass
        
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Error committing changes: {str(e)}")
        
        return {
            "success": True,
            "archived": len(stories),
            "checklist_items_resolved": resolved_count
        }
    
    else:
        raise HTTPException(status_code=400, detail=f"Invalid action: {request.action}. Must be 'approve', 'reject', or 'archive'")


@router.post("/items/{item_id}/action")
async def handle_checklist_action(
    item_id: str,
    request: ChecklistActionRequest,
    user_id: str = "default",
    db: Session = Depends(get_db)
):
    """Handle checklist item actions (resolve, dismiss, or perform action).
    
    Args:
        item_id: Checklist item ID
        request: Action request with action type and optional action_data
        user_id: User identifier
        db: Database session
    
    Returns:
        Action result
    """
    item = db.query(ChecklistItem).filter(
        ChecklistItem.id == item_id,
        ChecklistItem.user_id == user_id
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Checklist item not found")
    
    if request.action == "resolve":
        item.status = "resolved"
        item.resolved_at = datetime.utcnow()
        
        # If this is a story approval item and action_data contains story_ids, approve them
        if item.type == "story_approval" and item.action_data:
            try:
                action_data = json.loads(item.action_data)
                story_ids = action_data.get("story_ids", [])
                if story_ids and request.action_data and request.action_data.get("auto_approve_stories"):
                    # Auto-approve stories when resolving
                    agent = StoryExtractionAgent(db, user_id)
                    agent.approve_stories(story_ids, create_in_notion=True)
            except Exception as e:
                # Log error but don't fail the resolve action
                print(f"Error auto-approving stories: {str(e)}")
        
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Error committing changes: {str(e)}")
        
        return {
            "success": True,
            "message": "Checklist item resolved",
            "item_id": item_id
        }
    
    elif request.action == "dismiss":
        item.status = "dismissed"
        item.resolved_at = datetime.utcnow()
        
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Error committing changes: {str(e)}")
        
        return {
            "success": True,
            "message": "Checklist item dismissed",
            "item_id": item_id
        }
    
    else:
        raise HTTPException(status_code=400, detail=f"Invalid action: {request.action}. Must be 'resolve' or 'dismiss'")


@router.post("/clear-all")
async def clear_all_checklist_items(
    user_id: str = "default",
    db: Session = Depends(get_db)
):
    """Clear all pending checklist items for the user.
    
    Args:
        user_id: User identifier
        db: Database session
    
    Returns:
        Result with count of cleared items
    """
    try:
        # Mark all pending items as dismissed
        items = db.query(ChecklistItem).filter(
            ChecklistItem.user_id == user_id,
            ChecklistItem.status == "pending"
        ).all()
        
        cleared_count = 0
        for item in items:
            item.status = "dismissed"
            item.resolved_at = datetime.utcnow()
            cleared_count += 1
        
        db.commit()
        
        return {
            "success": True,
            "message": f"Cleared {cleared_count} checklist items",
            "cleared_count": cleared_count
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error clearing checklist items: {str(e)}")


@router.get("/summary")
async def get_checklist_summary(
    user_id: str = "default",
    db: Session = Depends(get_db)
):
    """Get checklist summary with counts and health metrics.
    
    Args:
        user_id: User identifier
        db: Database session
    
    Returns:
        Summary data with pending items, backlog health, stakeholders, and reports
    """
    # Get pending checklist items
    pending_items = db.query(ChecklistItem).filter(
        ChecklistItem.user_id == user_id,
        ChecklistItem.status == "pending"
    ).count()
    
    # Get backlog health
    latest_health = db.query(BacklogHealth).filter(
        BacklogHealth.user_id == user_id
    ).order_by(BacklogHealth.audit_date.desc()).first()
    
    # Get stakeholder counts
    stakeholders = db.query(Stakeholder).filter(
        Stakeholder.user_id == user_id
    ).all()
    
    total_open_actions = sum(s.open_actions for s in stakeholders)
    total_overdue = sum(s.overdue_actions for s in stakeholders)
    total_blocked = sum(s.blocked_actions for s in stakeholders)
    stakeholders_needing_attention = len([s for s in stakeholders if s.overdue_actions > 0 or s.blocked_actions > 0])
    
    # Get release reports
    ready_reports = db.query(ReleaseReport).filter(
        ReleaseReport.user_id == user_id,
        ReleaseReport.status == "ready"
    ).count()
    
    return {
        "pending_items": pending_items,
        "backlog_health_score": float(latest_health.health_score) if latest_health else 100.0,
        "stakeholders_needing_attention": stakeholders_needing_attention,
        "total_open_actions": total_open_actions,
        "total_overdue_actions": total_overdue,
        "total_blocked_actions": total_blocked,
        "ready_reports": ready_reports
    }


@router.post("/agents/run/{agent_name}")
async def run_agent_manually(
    agent_name: str,
    force_reprocess: bool = Query(False, description="Force reprocess pages even if already processed"),
    user_id: str = "default",
    db: Session = Depends(get_db)
):
    """Manually trigger an agent to run.
    
    Args:
        agent_name: Name of the agent to run
        force_reprocess: If True, re-process pages even if already processed (for story_extraction)
        user_id: User identifier
        db: Database session
    
    Returns:
        Agent execution result
    """
    if agent_name == "story_extraction":
        try:
            agent = StoryExtractionAgent(db, user_id)
            result = agent.run(force_reprocess=force_reprocess)
            # Ensure we always return a proper response
            if result is None:
                result = {
                    "success": False,
                    "error": "Agent returned no result",
                    "stories": [],
                    "checklist_items": []
                }
            return result
        except Exception as e:
            import traceback
            error_msg = str(e)
            traceback.print_exc()
            raise HTTPException(
                status_code=500,
                detail=f"Error running story extraction agent: {error_msg}"
            )
    
    elif agent_name == "noise_clearing":
        agent = NoiseClearingAgent(db, user_id)
        result = agent.run()
        return result
    
    elif agent_name == "release_report":
        agent = ReleaseReportAgent(db, user_id)
        result = agent.run()
        return result
    
    elif agent_name == "stakeholder_mapping":
        agent = StakeholderAgent(db, user_id)
        result = agent.run()
        return result
    
    elif agent_name == "integration_health":
        # Trigger integration health check
        from utils.integration_health import check_integration_health, create_integration_checklist_items
        health = check_integration_health(user_id, db)
        checklist_item_ids = create_integration_checklist_items(db, user_id)
        return {
            "success": True,
            "health": health,
            "checklist_items_created": len(checklist_item_ids)
        }
    
    else:
        raise HTTPException(status_code=400, detail=f"Invalid agent name: {agent_name}. Must be one of: story_extraction, noise_clearing, release_report, stakeholder_mapping, integration_health")


@router.get("/integration-health")
async def get_integration_health(
    user_id: str = "default",
    db: Session = Depends(get_db)
):
    """Get integration health status.
    
    Args:
        user_id: User identifier
        db: Database session
    
    Returns:
        Integration health status for all services
    """
    from utils.integration_health import check_integration_health
    
    health = check_integration_health(user_id, db)
    return health


@router.post("/integration-health/check")
async def trigger_integration_health_check(
    user_id: str = "default",
    db: Session = Depends(get_db)
):
    """Manually trigger integration health check and create checklist items for issues.
    
    Args:
        user_id: User identifier
        db: Database session
    
    Returns:
        Integration health status and created checklist items
    """
    from utils.integration_health import check_integration_health, create_integration_checklist_items
    
    health = check_integration_health(user_id, db)
    checklist_item_ids = create_integration_checklist_items(db, user_id)
    
    return {
        "health": health,
        "checklist_items_created": len(checklist_item_ids),
        "checklist_item_ids": checklist_item_ids
    }

