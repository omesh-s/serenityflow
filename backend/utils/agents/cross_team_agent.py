"""Cross-Team Updates Agent - analyzes team status, dependencies, and risks."""
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from .base_agent import BaseAgent
from utils.gemini import initialize_gemini
from utils.notion import get_notion_pages, get_page_content
import google.generativeai as genai
import traceback


class CrossTeamAgent(BaseAgent):
    """Agent that analyzes cross-team status, dependencies, and risks."""
    
    def __init__(self, db_session, user_id: str = "default"):
        """Initialize the cross-team agent."""
        super().__init__(db_session, user_id)
        initialize_gemini()
        self.model = genai.GenerativeModel('gemini-2.5-flash')
    
    def run(self, notion_pages: Optional[List[Dict]] = None, events: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """Analyze cross-team updates, dependencies, and risks.
        
        Args:
            notion_pages: List of Notion pages to analyze
            events: List of calendar events (for context)
        
        Returns:
            Dict with team highlights, dependencies, risks, and recommended actions
        """
        from utils.token_manager import get_token
        
        self.log_action("Starting cross-team updates analysis")
        
        # Get Notion token
        notion_token = get_token(self.db, "notion")
        if not notion_token:
            return {
                "success": False,
                "error": "Notion not connected",
                "overall_status": "",
                "team_highlights": [],
                "dependencies": [],
                "risks": [],
                "recommended_actions": []
            }
        
        # Fetch recent Notion pages if not provided
        if notion_pages is None:
            try:
                notion_pages = get_notion_pages(notion_token.access_token, page_size=100, include_archived=False)
            except Exception as e:
                self.log_action(f"Error fetching Notion pages: {str(e)}")
                return {
                    "success": False,
                    "error": f"Failed to fetch Notion pages: {str(e)}",
                    "overall_status": "",
                    "team_highlights": [],
                    "dependencies": [],
                    "risks": [],
                    "recommended_actions": []
                }
        
        # Extract text from pages
        all_text = self._extract_team_text(notion_pages, notion_token.access_token)
        
        if not all_text or len(all_text) < 100:
            return {
                "success": False,
                "error": "Insufficient team data found",
                "overall_status": "",
                "team_highlights": [],
                "dependencies": [],
                "risks": [],
                "recommended_actions": []
            }
        
        # Analyze with Gemini
        try:
            prompt = self._build_analysis_prompt(all_text, events)
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
            
            result = self._parse_response(response_text)
            
            # Create checklist item for dependencies/risks
            if result.get("dependencies") or result.get("risks"):
                self.create_checklist_item(
                    item_type="cross_team_updates",
                    title="Cross-Team Dependencies & Risks Identified",
                    description=f"Found {len(result.get('dependencies', []))} dependencies and {len(result.get('risks', []))} risks",
                    priority="high" if result.get("risks") else "medium",
                    action_type="review",
                    metadata=result
                )
            
            return {
                "success": True,
                **result
            }
        except Exception as e:
            self.log_action(f"Error analyzing cross-team updates: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "overall_status": "",
                "team_highlights": [],
                "dependencies": [],
                "risks": [],
                "recommended_actions": []
            }
    
    def _extract_team_text(self, notion_pages: List[Dict], access_token: str) -> str:
        """Extract team-related text from pages."""
        text_parts = []
        
        for page in notion_pages[:20]:  # Limit to recent 20 pages
            try:
                page_content = get_page_content(access_token, page.get("id"))
                page_text = self._extract_text_from_content(page_content)
                if page_text:
                    text_parts.append(f"Page: {page.get('title', 'Untitled')}\n{page_text}")
            except Exception as e:
                self.log_action(f"Error extracting content from page {page.get('id')}: {str(e)}")
                continue
        
        return "\n\n".join(text_parts)
    
    def _extract_text_from_content(self, page_content: Dict) -> str:
        """Extract plain text from page content."""
        text_parts = []
        content = page_content.get("content", [])
        for block in content:
            block_text = block.get("text", "")
            if block_text:
                text_parts.append(block_text)
        return "\n".join(text_parts)
    
    def _build_analysis_prompt(self, text: str, events: Optional[List[Dict]] = None) -> str:
        """Build prompt for cross-team analysis."""
        # Limit text to prevent token limits and ensure complete JSON responses
        text_limit = 6000  # Reduced from 8000 to ensure response fits in token limit
        
        prompt = f"""Analyze the following meeting notes and team updates to extract cross-team status, dependencies, and risks.

Content:
{text[:text_limit]}

Extract and organize the following:

1. **Overall Status**: High-level summary of team health and progress (1-2 sentences)

2. **Team Highlights**: For each team mentioned, identify:
   - Team name
   - Key wins (max 3 per team)
   - Blockers (max 3 per team)

3. **Dependencies**: List cross-team dependencies (who is blocked on whom) - max 5 items

4. **Risks**: Identify risks that could impact delivery - max 5 items

5. **Recommended Actions**: Suggest actions to address dependencies and risks - max 5 items

IMPORTANT: Keep responses concise. Limit arrays to prevent JSON truncation.

Return ONLY valid JSON in this format:
{{
  "overall_status": "Sprint on track. 2 blockers need immediate attention.",
  "team_highlights": [
    {{
      "team": "Engineering",
      "wins": ["OAuth shipped", "Dashboard performance 2x faster"],
      "blockers": ["Waiting on design specs for new feature"]
    }},
    {{
      "team": "Design",
      "wins": ["Completed 5 user interviews", "Finalized break UI"],
      "blockers": ["Need eng support for prototype"]
    }}
  ],
  "dependencies": [
    "Engineering blocked on design specs (Alice → Bob)",
    "Design needs eng prototype support (Sam → Alex)"
  ],
  "risks": [
    "API rate limits may cause delays in sync feature",
    "Mobile app launch at risk if we don't prioritize by next sprint"
  ],
  "recommended_actions": [
    "Alice to share design specs with Bob by EOD",
    "Schedule eng-design pairing session for prototype",
    "Escalate API rate limit issue to infra team"
  ]
}}

Return ONLY JSON, no markdown formatting. Keep it concise to fit within token limits."""
        return prompt
    
    def _parse_response(self, response_text: str) -> Dict[str, Any]:
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
                    # JSON might be truncated, try to parse what we have
                    # Find the last complete object/array
                    self.log_action(f"Warning: JSON might be truncated. Attempting to parse partial JSON.")
                    # Try to fix common truncation issues by closing unclosed structures
                    # Count unclosed brackets/braces
                    open_braces = response_text[start_idx:].count('{') - response_text[start_idx:].count('}')
                    open_brackets = response_text[start_idx:].count('[') - response_text[start_idx:].count(']')
                    # Try to close them
                    if open_braces > 0 or open_brackets > 0:
                        # Find last valid position before truncation
                        # Look for last complete array/object
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
                    else:
                        response_text = response_text[start_idx:]
            
            data = json.loads(response_text)
            
            # Ensure all required fields exist and limit array sizes to prevent issues
            team_highlights = data.get("team_highlights", [])
            if isinstance(team_highlights, list):
                team_highlights = team_highlights[:10]  # Limit to 10 teams
            
            dependencies = data.get("dependencies", [])
            if isinstance(dependencies, list):
                dependencies = dependencies[:10]  # Limit to 10 dependencies
            
            risks = data.get("risks", [])
            if isinstance(risks, list):
                risks = risks[:10]  # Limit to 10 risks
            
            recommended_actions = data.get("recommended_actions", [])
            if isinstance(recommended_actions, list):
                recommended_actions = recommended_actions[:10]  # Limit to 10 actions
            
            return {
                "overall_status": data.get("overall_status", ""),
                "team_highlights": team_highlights,
                "dependencies": dependencies,
                "risks": risks,
                "recommended_actions": recommended_actions
            }
        except json.JSONDecodeError as e:
            self.log_action(f"JSON decode error: {str(e)}")
            self.log_action(f"Response text length: {len(response_text)} chars")
            self.log_action(f"Response text (first 500 chars): {response_text[:500]}")
            self.log_action(f"Response text (last 500 chars): {response_text[-500:]}")
            # Try to extract partial data if possible
            try:
                # Try to extract just the overall_status if JSON is malformed
                status_match = re.search(r'"overall_status"\s*:\s*"([^"]*)"', response_text)
                overall_status = status_match.group(1) if status_match else ""
            except:
                overall_status = ""
            
            return {
                "overall_status": overall_status or "Error parsing response. Check logs for details.",
                "team_highlights": [],
                "dependencies": [],
                "risks": [],
                "recommended_actions": []
            }
        except Exception as e:
            self.log_action(f"Error parsing response: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "overall_status": f"Error: {str(e)}",
                "team_highlights": [],
                "dependencies": [],
                "risks": [],
                "recommended_actions": []
            }

