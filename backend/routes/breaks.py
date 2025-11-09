"""Break management routes for editing and customizing breaks."""
from fastapi import APIRouter, HTTPException, Depends, Body
from sqlalchemy.orm import Session
from database import get_db
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime
import json

router = APIRouter()

# In-memory store for user break customizations (in production, use database)
# This is a module-level variable that can be accessed by other modules
_break_customizations: Dict[str, List[Dict]] = {}


class BreakUpdate(BaseModel):
    """Model for updating a break."""
    id: Optional[str] = None
    time: str
    duration: int = Field(ge=3, le=60, default=10)
    activity: str
    reason: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    custom: bool = False


class BreakCreate(BaseModel):
    """Model for creating a new break."""
    time: str
    duration: int = Field(ge=3, le=60, default=10)
    activity: str
    reason: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None


class BreakDelete(BaseModel):
    """Model for deleting a break."""
    id: str
    time: str


@router.get("/types")
async def get_break_types():
    """Get all available break types."""
    from utils.break_types import get_all_break_types
    return {"break_types": get_all_break_types()}


@router.post("/customize")
async def customize_breaks(
    request_data: dict = Body(...),
    db: Session = Depends(get_db)
):
    """Save user's break customizations. Accepts breaks list and optional user_id in request body."""
    try:
        breaks_data = request_data.get("breaks", [])
        user_id = request_data.get("user_id", "default")  # In production, get from auth
        
        # Validate breaks
        validated_breaks = []
        for break_dict in breaks_data:
            # Handle both dict and BreakUpdate objects
            if isinstance(break_dict, dict):
                break_item = BreakUpdate(**break_dict)
            else:
                break_item = break_dict
            
            validated_breaks.append({
                "id": break_item.id or f"break_{datetime.utcnow().timestamp()}",
                "time": break_item.time,
                "duration": break_item.duration,
                "activity": break_item.activity,
                "reason": break_item.reason,
                "description": break_item.description,
                "icon": break_item.icon,
                "custom": break_item.custom,
            })
        
        # Store customizations (in production, save to database)
        _break_customizations[user_id] = validated_breaks
        
        return {
            "success": True,
            "message": "Breaks customized successfully",
            "breaks": validated_breaks
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error customizing breaks: {str(e)}")


@router.get("/customizations")
async def get_break_customizations(
    user_id: str = "default",  # In production, get from auth
    db: Session = Depends(get_db)
):
    """Get user's break customizations."""
    customizations = _break_customizations.get(user_id, [])
    return {"breaks": customizations}


@router.post("/add")
async def add_break(
    break_item: BreakCreate,
    user_id: str = Body(default="default"),  # In production, get from auth
    db: Session = Depends(get_db)
):
    """Add a new custom break."""
    try:
        new_break = {
            "id": f"break_{datetime.utcnow().timestamp()}",
            "time": break_item.time,
            "duration": break_item.duration,
            "activity": break_item.activity,
            "reason": break_item.reason,
            "description": break_item.description,
            "icon": break_item.icon,
            "custom": True,
        }
        
        # Add to customizations
        if user_id not in _break_customizations:
            _break_customizations[user_id] = []
        _break_customizations[user_id].append(new_break)
        
        return {
            "success": True,
            "message": "Break added successfully",
            "break": new_break
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding break: {str(e)}")


@router.delete("/{break_id}")
async def delete_break(
    break_id: str,
    user_id: str = "default",  # In production, get from auth
    db: Session = Depends(get_db)
):
    """Delete a break."""
    try:
        if user_id in _break_customizations:
            _break_customizations[user_id] = [
                b for b in _break_customizations[user_id]
                if b.get("id") != break_id
            ]
        
        return {
            "success": True,
            "message": "Break deleted successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting break: {str(e)}")


@router.post("/clear-cache")
async def clear_break_cache(
    user_id: str = Body(default="default"),
    db: Session = Depends(get_db)
):
    """Clear break cache to force regeneration of breaks."""
    try:
        from utils.break_cache import clear_break_cache
        clear_break_cache()
        
        return {
            "success": True,
            "message": "Break cache cleared successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing cache: {str(e)}")
