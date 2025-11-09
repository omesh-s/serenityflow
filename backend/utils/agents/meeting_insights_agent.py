"""Meeting Insights Agent - extracts key insights, decisions, and action items from meetings."""
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from .base_agent import BaseAgent
from utils.gemini import initialize_gemini
from utils.notion import get_notion_pages, get_page_content
import google.generativeai as genai


class MeetingInsightsAgent(BaseAgent):
    """Agent that extracts insights, decisions, and action items from meeting notes."""
    
    def __init__(self, db_session, user_id: str = "default"):
        """Initialize the meeting insights agent."""
        super().__init__(db_session, user_id)
        initialize_gemini()
        self.model = genai.GenerativeModel('gemini-2.5-flash')
    
    def run(self, notion_pages: Optional[List[Dict]] = None, events: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """Extract meeting insights, decisions, and action items.
        
        Args:
            notion_pages: List of Notion pages to analyze
            events: List of calendar events (for context)
        
        Returns:
            Dict with meeting summary, decisions, action items, and open questions
        """
        from utils.token_manager import get_token
        
        self.log_action("Starting meeting insights extraction")
        
        # Get Notion token
        notion_token = get_token(self.db, "notion")
        if not notion_token:
            return {
                "success": False,
                "error": "Notion not connected",
                "meetings": []
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
                    "meetings": []
                }
        
        # Process each page as a potential meeting
        meetings = []
        for page in notion_pages[:10]:  # Process most recent 10 pages
            try:
                page_content = get_page_content(notion_token.access_token, page.get("id"))
                page_text = self._extract_text_from_content(page_content)
                
                if not page_text or len(page_text) < 50:
                    continue
                
                # Analyze meeting
                meeting_insights = self._analyze_meeting(page, page_text, events)
                if meeting_insights:
                    meetings.append(meeting_insights)
            except Exception as e:
                self.log_action(f"Error processing page {page.get('id')}: {str(e)}")
                continue
        
        # Create checklist items for action items
        total_action_items = sum(len(m.get("action_items", [])) for m in meetings)
        if total_action_items > 0:
            self.create_checklist_item(
                item_type="meeting_insights",
                title=f"Meeting Insights: {len(meetings)} meeting(s) analyzed",
                description=f"Found {total_action_items} action items across {len(meetings)} meetings",
                priority="high",
                action_type="review",
                metadata={"meetings": meetings}
            )
        
        return {
            "success": True,
            "meetings": meetings,
            "total_meetings": len(meetings),
            "total_action_items": total_action_items
        }
    
    def _extract_text_from_content(self, page_content: Dict) -> str:
        """Extract plain text from page content."""
        text_parts = []
        content = page_content.get("content", [])
        for block in content:
            block_text = block.get("text", "")
            if block_text:
                text_parts.append(block_text)
        return "\n".join(text_parts)
    
    def _analyze_meeting(self, page: Dict, page_text: str, events: Optional[List[Dict]] = None) -> Optional[Dict]:
        """Analyze a single meeting page."""
        try:
            prompt = self._build_analysis_prompt(page, page_text, events)
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.2,
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
                return None
            
            if not response_text:
                return None
            
            result = self._parse_response(response_text, page)
            return result
        except Exception as e:
            self.log_action(f"Error analyzing meeting: {str(e)}")
            return None
    
    def _build_analysis_prompt(self, page: Dict, page_text: str, events: Optional[List[Dict]] = None) -> str:
        """Build prompt for meeting analysis."""
        prompt = f"""Analyze the following meeting notes and extract key insights, decisions, action items, and open questions.

Meeting Title: {page.get('title', 'Untitled')}
Date: {page.get('created_time', 'Unknown')}

Content:
{page_text[:6000]}

Extract and organize the following:

1. **Summary**: 3-5 bullet point meeting summary
2. **Decisions**: List of key decisions made
3. **Action Items**: List of action items with owner and due date (if detected)
4. **Open Questions**: Unresolved questions that need follow-up

Return ONLY valid JSON in this format:
{{
  "meeting_title": "Sprint Planning - Sprint 23",
  "summary": [
    "Focus on authentication and dashboard performance",
    "Coupon field redesign postponed to next sprint",
    "Alex to spike pricing service cleanup"
  ],
  "decisions": [
    "Ship OAuth and performance improvements this sprint",
    "Defer coupon UI redesign to Sprint 24"
  ],
  "action_items": [
    {{
      "description": "Create spike for pricing service cleanup",
      "owner": "Alex",
      "due": "This sprint"
    }},
    {{
      "description": "Share design mockups with engineering",
      "owner": "Alice",
      "due": "EOD"
    }}
  ],
  "open_questions": [
    "What's the timeline for mobile app?",
    "Do we need legal approval for new privacy feature?"
  ]
}}

Return ONLY JSON, no markdown formatting."""
        return prompt
    
    def _parse_response(self, response_text: str, page: Dict) -> Dict[str, Any]:
        """Parse Gemini response into structured data."""
        try:
            import re
            # Remove markdown code blocks if present
            json_match = re.search(r'```(?:json)?\s*(\{.*\})\s*```', response_text, re.DOTALL)
            if json_match:
                response_text = json_match.group(1)
            else:
                # Try to find JSON object directly
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    response_text = json_match.group(0)
                else:
                    self.log_action(f"Could not find JSON in response. Response: {response_text[:200]}")
                    raise ValueError("No JSON found in response")
            
            data = json.loads(response_text)
            
            # Ensure all required fields exist
            return {
                "meeting_title": data.get("meeting_title", page.get("title", "Untitled")),
                "meeting_date": page.get("created_time", ""),
                "summary": data.get("summary", []),
                "decisions": data.get("decisions", []),
                "action_items": data.get("action_items", []),
                "open_questions": data.get("open_questions", [])
            }
        except json.JSONDecodeError as e:
            self.log_action(f"JSON decode error: {str(e)}")
            self.log_action(f"Response text (first 500 chars): {response_text[:500]}")
            return {
                "meeting_title": page.get("title", "Untitled"),
                "meeting_date": page.get("created_time", ""),
                "summary": [],
                "decisions": [],
                "action_items": [],
                "open_questions": []
            }
        except Exception as e:
            self.log_action(f"Error parsing response: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "meeting_title": page.get("title", "Untitled"),
                "meeting_date": page.get("created_time", ""),
                "summary": [],
                "decisions": [],
                "action_items": [],
                "open_questions": []
            }

