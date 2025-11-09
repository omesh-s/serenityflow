"""Sprint Planning Agent - generates sprint scope, goals, and risk analysis."""
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from .base_agent import BaseAgent
from utils.gemini import initialize_gemini
import google.generativeai as genai
import traceback


class SprintPlanningAgent(BaseAgent):
    """Agent that generates sprint plans based on backlog items and team velocity."""
    
    def __init__(self, db_session, user_id: str = "default"):
        """Initialize the sprint planning agent."""
        super().__init__(db_session, user_id)
        initialize_gemini()
        self.model = genai.GenerativeModel('gemini-2.5-flash')
    
    def run(self, stories: Optional[List[Dict]] = None, velocity: int = 13) -> Dict[str, Any]:
        """Generate sprint plan based on backlog items.
        
        Args:
            stories: List of stories with points/priority
            velocity: Team velocity (default 13)
        
        Returns:
            Dict with sprint scope, goal, rationale, risks, and stretch item
        """
        from database import Story
        
        self.log_action("Starting sprint planning")
        
        # Get stories from database if not provided
        if stories is None:
            stories = self.db.query(Story).filter(
                Story.user_id == self.user_id,
                Story.status.in_(["pending", "approved"])
            ).all()
            
            # Sort by Priority (High → Medium → Low) then by story points (descending)
            priority_order = {"high": 1, "medium": 2, "low": 3}
            stories_sorted = sorted(
                stories,
                key=lambda s: (
                    priority_order.get(s.priority, 2),
                    -(s.story_points if s.story_points else self._estimate_points(s))
                )
            )
            
            stories = [
                {
                    "id": s.id,
                    "title": s.title,
                    "description": s.description,
                    "priority": s.priority,
                    "points": self._estimate_points(s),
                    "story_points": s.story_points,
                    "owner": s.owner,
                    "tags": json.loads(s.tags) if s.tags else []
                }
                for s in stories_sorted
            ]
        
        if not stories:
            self.log_action("No stories found for sprint planning")
            return {
                "success": True,  # Return success with empty data so frontend can display it
                "sprint_scope": [],
                "total_points": 0,
                "velocity": velocity,
                "sprint_goal": "No stories available for sprint planning. Please extract stories from meeting notes first.",
                "rationale": [],
                "major_risks": [],
                "stretch_item": None
            }
        
        # Analyze with Gemini
        try:
            prompt = self._build_planning_prompt(stories, velocity)
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=2048,
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
            
            result = self._parse_response(response_text, stories, velocity)
            
            # Create checklist item for sprint plan
            if result.get("sprint_goal"):
                self.create_checklist_item(
                    item_type="sprint_planning",
                    title=f"Sprint Plan Generated: {result.get('sprint_goal', '')[:50]}...",
                    description=f"Planned {len(result.get('sprint_scope', []))} items ({result.get('total_points', 0)} points)",
                    priority="high",
                    action_type="review",
                    metadata=result
                )
            
            return {
                "success": True,
                **result
            }
        except Exception as e:
            self.log_action(f"Error generating sprint plan: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "sprint_scope": [],
                "sprint_goal": "",
                "rationale": [],
                "major_risks": [],
                "stretch_item": None
            }
    
    def _estimate_points(self, story) -> int:
        """Estimate story points based on priority and description."""
        # Use story_points if available, otherwise estimate based on priority
        if story.story_points:
            return story.story_points
        # Fallback estimation: high=8, medium=5, low=3
        if story.priority == "high":
            return 8
        elif story.priority == "medium":
            return 5
        else:
            return 3
    
    def _build_planning_prompt(self, stories: List[Dict], velocity: int) -> str:
        """Build prompt for sprint planning."""
        # Stories are already sorted by Priority (High → Medium → Low) then by story points
        stories_text = "\n".join([
            f"- {s.get('id', '')}: {s.get('title', '')} (Priority: {s.get('priority', 'medium')}, Points: {s.get('points', 5)}, Owner: {s.get('owner', 'Unassigned')})"
            for s in stories
        ])
        
        prompt = f"""Plan a sprint based on the following backlog items. Team velocity is {velocity} points.

Backlog Items (sorted by Priority: High → Medium → Low, then by Story Points):
{stories_text}

Instructions:
1. Select stories starting from the TOP of the list (highest priority first)
2. Fill the sprint by adding stories until you reach or approach the velocity ({velocity} points)
3. Prioritize High priority stories first, then Medium, then Low
4. Try to fit as many High priority stories as possible
5. Create a coherent sprint goal that ties the selected stories together
6. Identify one stretch item (if team finishes early)

Return ONLY valid JSON in this format:
{{
  "sprint_scope": [
    {{"id": "F3", "title": "Improve checkout latency", "points": 8, "priority": "High"}},
    {{"id": "F1", "title": "Fix coupon bug", "points": 5, "priority": "High"}}
  ],
  "total_points": 13,
  "velocity": {velocity},
  "sprint_goal": "Reduce checkout friction and lift conversion by fixing the coupon bug and improving checkout performance",
  "rationale": [
    "Both items target checkout flow and directly affect conversion",
    "Fixing coupon bug and reducing latency both improve user trust",
    "Work can be coordinated and validated end-to-end"
  ],
  "major_risks": [
    "Third-party payment API changes could block verification",
    "Performance improvements may require infrastructure changes",
    "Regression risk in pricing logic requires thorough testing"
  ],
  "stretch_item": {{
    "id": "F2",
    "title": "Add automated checkout tests",
    "points": 3,
    "priority": "Medium"
  }}
}}

Return ONLY JSON, no markdown formatting."""
        return prompt
    
    def _parse_response(self, response_text: str, stories: List[Dict], velocity: int) -> Dict[str, Any]:
        """Parse Gemini response into structured data."""
        try:
            import re
            # Remove markdown code blocks if present
            json_match = re.search(r'```(?:json)?\s*(\{.*\})\s*```', response_text, re.DOTALL)
            if json_match:
                response_text = json_match.group(1)
            else:
                # Try to find JSON object directly - use balanced braces to handle nested JSON
                # Find the first { and then find the matching closing }
                brace_count = 0
                start_idx = response_text.find('{')
                if start_idx == -1:
                    self.log_action(f"Could not find JSON in response. Response: {response_text[:200]}")
                    raise ValueError("No JSON found in response")
                
                end_idx = start_idx
                for i in range(start_idx, len(response_text)):
                    if response_text[i] == '{':
                        brace_count += 1
                    elif response_text[i] == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end_idx = i + 1
                            break
                
                if brace_count == 0:
                    response_text = response_text[start_idx:end_idx]
                else:
                    # JSON might be truncated, try to fix it
                    self.log_action(f"Warning: JSON might be truncated. Attempting to fix.")
                    # Try to close unclosed structures
                    open_braces = response_text[start_idx:].count('{') - response_text[start_idx:].count('}')
                    open_brackets = response_text[start_idx:].count('[') - response_text[start_idx:].count(']')
                    
                    # Find last complete object/array
                    last_complete = start_idx
                    temp_brace_count = 0
                    temp_bracket_count = 0
                    for i in range(start_idx, len(response_text)):
                        if response_text[i] == '{':
                            temp_brace_count += 1
                        elif response_text[i] == '}':
                            temp_brace_count -= 1
                            if temp_brace_count == 0 and temp_bracket_count == 0:
                                last_complete = i + 1
                        elif response_text[i] == '[':
                            temp_bracket_count += 1
                        elif response_text[i] == ']':
                            temp_bracket_count -= 1
                            if temp_brace_count == 0 and temp_bracket_count == 0:
                                last_complete = i + 1
                    
                    if last_complete > start_idx:
                        response_text = response_text[start_idx:last_complete]
                    else:
                        # Last resort: try to close structures manually
                        response_text = response_text[start_idx:] + '}' * open_braces + ']' * open_brackets
            
            data = json.loads(response_text)
            
            # Ensure all required fields exist
            result = {
                "sprint_scope": data.get("sprint_scope", []),
                "total_points": data.get("total_points", 0),
                "velocity": velocity,
                "sprint_goal": data.get("sprint_goal", ""),
                "rationale": data.get("rationale", []),
                "major_risks": data.get("major_risks", []),
                "stretch_item": data.get("stretch_item")
            }
            
            # Log results for debugging
            if not result["sprint_scope"]:
                self.log_action(f"No sprint scope found. Response keys: {list(data.keys()) if isinstance(data, dict) else 'not a dict'}")
                self.log_action(f"Full response (first 1000 chars): {response_text[:1000]}")
            else:
                self.log_action(f"Generated sprint plan with {len(result['sprint_scope'])} items, {result['total_points']} points")
            
            return result
        except json.JSONDecodeError as e:
            self.log_action(f"JSON decode error: {str(e)}")
            self.log_action(f"Response text (first 500 chars): {response_text[:500]}")
            return {
                "sprint_scope": [],
                "total_points": 0,
                "velocity": velocity,
                "sprint_goal": "",
                "rationale": [],
                "major_risks": [],
                "stretch_item": None
            }
        except Exception as e:
            self.log_action(f"Error parsing response: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "sprint_scope": [],
                "total_points": 0,
                "velocity": velocity,
                "sprint_goal": "",
                "rationale": [],
                "major_risks": [],
                "stretch_item": None
            }

