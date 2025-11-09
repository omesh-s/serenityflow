"""Stakeholder Agent - maps and tracks stakeholders from stories and meetings."""
from typing import Dict, List, Any, Optional
from datetime import datetime
from .base_agent import BaseAgent
import json
import uuid


class StakeholderAgent(BaseAgent):
    """Agent that maps stakeholders and tracks their actions."""
    
    def run(self, **kwargs) -> Dict[str, Any]:
        """Map stakeholders and identify actions needed.
        
        Returns:
            Dict with stakeholder data and checklist items
        """
        from database import Story, Stakeholder
        
        self.log_action("Starting stakeholder mapping")
        
        # Get all stories
        stories = self.db.query(Story).filter(
            Story.user_id == self.user_id,
            Story.status.in_(["pending", "approved"])
        ).all()
        
        # Extract stakeholders from stories
        stakeholders_map = {}
        
        for story in stories:
            if story.owner:
                owner_name = story.owner.strip()
                if owner_name not in stakeholders_map:
                    stakeholders_map[owner_name] = {
                        "name": owner_name,
                        "stories": [],
                        "open_actions": 0,
                        "overdue_actions": 0,
                        "blocked_actions": 0
                    }
                
                stakeholders_map[owner_name]["stories"].append(story.id)
                stakeholders_map[owner_name]["open_actions"] += 1
                
                # Check if story is overdue (created more than 7 days ago)
                if (datetime.utcnow() - story.created_at).days > 7:
                    stakeholders_map[owner_name]["overdue_actions"] += 1
        
        # Update or create stakeholder records
        checklist_item_ids = []
        
        for name, data in stakeholders_map.items():
            # Find existing stakeholder
            stakeholder = self.db.query(Stakeholder).filter(
                Stakeholder.name == name,
                Stakeholder.user_id == self.user_id
            ).first()
            
            if stakeholder:
                # Update existing
                stakeholder.open_actions = data["open_actions"]
                stakeholder.overdue_actions = data["overdue_actions"]
                stakeholder.blocked_actions = data["blocked_actions"]
                stakeholder.last_activity = datetime.utcnow()
                stakeholder.meta_data = json.dumps({"story_ids": data["stories"]})
            else:
                # Create new
                stakeholder = Stakeholder(
                    id=str(uuid.uuid4()),
                    name=name,
                    open_actions=data["open_actions"],
                    overdue_actions=data["overdue_actions"],
                    blocked_actions=data["blocked_actions"],
                    last_activity=datetime.utcnow(),
                    meta_data=json.dumps({"story_ids": data["stories"]}),
                    user_id=self.user_id
                )
                self.db.add(stakeholder)
            
            # Create checklist item if stakeholder needs attention
            if data["overdue_actions"] > 0 or data["blocked_actions"] > 0:
                checklist_id = self.create_checklist_item(
                    item_type="stakeholder_action",
                    title=f"{name} needs attention",
                    description=f"{name} has {data['overdue_actions']} overdue action(s) and {data['blocked_actions']} blocked action(s).",
                    priority="high" if data["overdue_actions"] > 3 else "medium",
                    action_type="review",
                    action_data={
                        "stakeholder_id": stakeholder.id,
                        "stakeholder_name": name,
                        "overdue_count": data["overdue_actions"],
                        "blocked_count": data["blocked_actions"]
                    }
                )
                checklist_item_ids.append(checklist_id)
        
        self.db.commit()
        
        self.log_action(f"Mapped {len(stakeholders_map)} stakeholders")
        
        return {
            "success": True,
            "stakeholders_count": len(stakeholders_map),
            "checklist_items": checklist_item_ids
        }

