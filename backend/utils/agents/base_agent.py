"""Base agent class for all automation agents."""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid
import json


class BaseAgent(ABC):
    """Base class for all automation agents.
    
    All agents should inherit from this class and implement the required methods.
    Agents are responsible for:
    1. Processing data (meetings, notes, stories, etc.)
    2. Generating insights/recommendations
    3. Creating checklist items for user review
    4. Performing automated actions (when approved)
    """
    
    def __init__(self, db_session, user_id: str = "default"):
        """Initialize the agent.
        
        Args:
            db_session: SQLAlchemy database session
            user_id: User identifier
        """
        self.db = db_session
        self.user_id = user_id
        self.agent_name = self.__class__.__name__
    
    @abstractmethod
    def run(self, **kwargs) -> Dict[str, Any]:
        """Run the agent's main logic.
        
        Returns:
            Dict with results, checklist items, and metadata
        """
        pass
    
    def create_checklist_item(
        self,
        item_type: str,
        title: str,
        description: Optional[str] = None,
        priority: str = "medium",
        action_type: Optional[str] = None,
        action_data: Optional[Dict] = None,
        metadata: Optional[Dict] = None
    ) -> str:
        """Create a checklist item for user review.
        
        Args:
            item_type: Type of checklist item (e.g., "story_approval")
            title: Title of the checklist item
            description: Optional description
            priority: Priority level ("high", "medium", "low")
            action_type: Type of action required (e.g., "approve", "review")
            action_data: Data needed for the action (e.g., story IDs)
            metadata: Additional metadata
        
        Returns:
            Checklist item ID
        """
        from database import ChecklistItem
        
        checklist_item = ChecklistItem(
            id=str(uuid.uuid4()),
            type=item_type,
            title=title,
            description=description,
            status="pending",
            priority=priority,
            action_type=action_type,
            action_data=json.dumps(action_data) if action_data else None,
            meta_data=json.dumps(metadata) if metadata else None,
            user_id=self.user_id,
            created_at=datetime.utcnow()
        )
        
        self.db.add(checklist_item)
        self.db.commit()
        self.db.refresh(checklist_item)
        
        return checklist_item.id
    
    def log_action(self, action: str, details: Optional[Dict] = None):
        """Log an action for debugging and auditing.
        
        Args:
            action: Action description
            details: Optional details dictionary
        """
        print(f"[{self.agent_name}] {action}")
        if details:
            print(f"  Details: {details}")

