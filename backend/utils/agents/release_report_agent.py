"""Release Report Agent - generates release reports from ready stories."""
from typing import Dict, List, Any, Optional
from datetime import datetime
from .base_agent import BaseAgent
import json
import uuid
import google.generativeai as genai
import traceback


class ReleaseReportAgent(BaseAgent):
    """Agent that generates weekly updates, team updates, and release notes."""
    
    def __init__(self, db_session, user_id: str = "default"):
        """Initialize the reporting agent."""
        super().__init__(db_session, user_id)
        from utils.gemini import initialize_gemini
        initialize_gemini()
        self.model = genai.GenerativeModel('gemini-2.5-flash-lite')
    
    def run(self, **kwargs) -> Dict[str, Any]:
        """Generate weekly updates, team updates, and release notes.
        
        Returns:
            Dict with weekly executive update, team update, and release notes
        """
        from database import Story, ReleaseReport
        
        self.log_action("Starting report generation")
        
        # Get completed/approved stories from recent period
        ready_stories = self.db.query(Story).filter(
            Story.user_id == self.user_id,
            Story.status == "approved"
        ).limit(20).all()  # Limit to 20 most recent
        
        if not ready_stories:
            return {
                "success": True,
                "weekly_executive_update": "No stories completed this week.",
                "weekly_team_update": {
                    "shipped": [],
                    "metrics": {},
                    "blockers": []
                },
                "release_notes": {
                    "version": "v2.1",
                    "date": datetime.utcnow().strftime("%B %d, %Y"),
                    "summary": "No updates this week.",
                    "highlights": []
                },
                "checklist_items": []
            }
        
        # Generate reports using Gemini
        try:
            # Build stories content
            stories_text = "\n".join([
                f"- {s.title}: {s.description or 'No description'}"
                for s in ready_stories
            ])
            
            # Generate weekly updates and release notes
            prompt = self._build_reporting_prompt(stories_text, ready_stories)
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=4096,
                )
            )
            
            # Get response text safely (avoid accessing finish_message)
            response_text = ""
            try:
                # First try the standard .text property
                if hasattr(response, 'text'):
                    response_text = response.text
                elif hasattr(response, 'candidates') and response.candidates:
                    # Extract from candidates if .text doesn't work
                    candidate = response.candidates[0]
                    if hasattr(candidate, 'content'):
                        content = candidate.content
                        if hasattr(content, 'parts') and content.parts:
                            # Extract text from parts
                            text_parts = []
                            for part in content.parts:
                                if hasattr(part, 'text'):
                                    text_parts.append(part.text)
                            response_text = "".join(text_parts)
                        elif hasattr(content, 'text'):
                            response_text = content.text
                
                # Fallback: try to convert to string
                if not response_text:
                    response_text = str(response)
            except Exception as e:
                self.log_action(f"Error extracting response text: {str(e)}")
                raise Exception(f"Could not extract response text: {str(e)}")
            
            if not response_text:
                raise Exception("Empty response from Gemini")
            
            result = self._parse_response(response_text, ready_stories)
            
            # Create checklist item
            checklist_id = self.create_checklist_item(
                item_type="reporting",
                title="Weekly Reports & Release Notes Ready",
                description=f"Generated weekly updates and release notes for {len(ready_stories)} stories",
                priority="medium",
                action_type="review",
                metadata=result
            )
            
            self.log_action(f"Generated reports for {len(ready_stories)} stories")
            
            return {
                "success": True,
                **result,
                "checklist_items": [checklist_id]
            }
            
        except Exception as e:
            self.log_action(f"Error generating reports: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e),
                "weekly_executive_update": "",
                "weekly_team_update": {},
                "release_notes": {},
                "checklist_items": []
            }
    
    def _build_reporting_prompt(self, stories_text: str, stories: List) -> str:
        """Build prompt for generating weekly updates and release notes."""
        prompt = f"""Generate weekly updates and release notes for the following completed stories/features.

**Stories/Features Shipped:**
{stories_text}

Generate three types of updates:

1. **Weekly Executive Update** (1-2 sentences): High-level summary for executives
2. **Weekly Team Update** (structured): Detailed update with metrics and blockers
3. **Release Notes** (user-facing): Summary and highlights for users

Return ONLY valid JSON in this format:
{{
  "weekly_executive_update": "Sprint 23: Shipped OAuth and 2x dashboard performance. 820 weekly active users (+15%). 2 items pushed to next sprint.",
  "weekly_team_update": {{
    "shipped": ["Google OAuth", "Dashboard performance improvements", "Mood tracking charts"],
    "metrics": {{
      "weekly_active_users": 820,
      "growth": "+15%",
      "retention_d7": "62%"
    }},
    "blockers": ["Spotify API approval pending", "SSO needs security audit"]
  }},
  "release_notes": {{
    "version": "v2.1",
    "date": "November 15, 2025",
    "summary": "SerenityFlow 2.1 brings faster sign-in with Google OAuth, 2x faster dashboard loading, and beautiful mood tracking visualizations.",
    "highlights": [
      "Google OAuth - Sign in with one click",
      "Lightning-fast dashboard - Now 2x faster",
      "Mood tracking charts - Visualize your wellness journey"
    ]
  }}
}}

Return ONLY JSON, no markdown formatting."""
        return prompt
    
    def _parse_response(self, response_text: str, stories: List) -> Dict[str, Any]:
        """Parse Gemini response into structured data."""
        try:
            import re
            # Extract JSON from response (handle markdown code blocks)
            json_match = re.search(r'```(?:json)?\s*(\{.*\})\s*```', response_text, re.DOTALL)
            if json_match:
                response_text = json_match.group(1)
            else:
                # Try to find JSON object
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    response_text = json_match.group(0)
            
            # Try to fix truncated JSON by finding balanced braces
            if response_text:
                brace_count = 0
                last_valid_pos = 0
                for i, char in enumerate(response_text):
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            last_valid_pos = i + 1
                            break
                
                if last_valid_pos > 0 and last_valid_pos < len(response_text):
                    response_text = response_text[:last_valid_pos]
            
            data = json.loads(response_text)
            
            # Ensure all required fields exist
            return {
                "weekly_executive_update": data.get("weekly_executive_update", ""),
                "weekly_team_update": data.get("weekly_team_update", {
                    "shipped": [],
                    "metrics": {},
                    "blockers": []
                }),
                "release_notes": data.get("release_notes", {
                    "version": "v2.1",
                    "date": datetime.utcnow().strftime("%B %d, %Y"),
                    "summary": "",
                    "highlights": []
                })
            }
        except Exception as e:
            self.log_action(f"Error parsing response: {str(e)}")
            # Log first 500 chars of response for debugging
            if response_text:
                self.log_action(f"Response text (first 500 chars): {response_text[:500]}")
            return {
                "weekly_executive_update": "",
                "weekly_team_update": {
                    "shipped": [],
                    "metrics": {},
                    "blockers": []
                },
                "release_notes": {
                    "version": "v2.1",
                    "date": datetime.utcnow().strftime("%B %d, %Y"),
                    "summary": "",
                    "highlights": []
                }
            }

