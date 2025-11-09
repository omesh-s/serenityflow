"""Customer & Market Research Agent - analyzes feedback, competitors, and market trends."""
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from .base_agent import BaseAgent
from utils.gemini import initialize_gemini
from utils.notion import get_notion_pages, get_page_content
import google.generativeai as genai
import traceback


class CustomerResearchAgent(BaseAgent):
    """Agent that analyzes customer feedback, competitor data, and market trends."""
    
    def __init__(self, db_session, user_id: str = "default"):
        """Initialize the customer research agent."""
        super().__init__(db_session, user_id)
        initialize_gemini()
        self.model = genai.GenerativeModel('gemini-2.5-flash')
    
    def run(self, notion_pages: Optional[List[Dict]] = None, events: Optional[List[Dict]] = None, **kwargs) -> Dict[str, Any]:
        """Analyze customer feedback, competitors, and market trends.
        
        Args:
            notion_pages: List of Notion pages to analyze
            events: List of calendar events (for context)
        
        Returns:
            Dict with customer themes, competitor analysis, market trends, and executive brief
        """
        from utils.token_manager import get_token
        
        self.log_action("Starting customer & market research analysis")
        
        # Get Notion token
        notion_token = get_token(self.db, "notion")
        if not notion_token:
            return {
                "success": False,
                "error": "Notion not connected",
                "customer_themes": [],
                "competitor_analysis": {},
                "market_trends": [],
                "executive_brief": ""
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
                    "customer_themes": [],
                    "competitor_analysis": {},
                    "market_trends": [],
                    "executive_brief": ""
                }
        
        # Extract text from pages
        all_text = self._extract_feedback_text(notion_pages, notion_token.access_token)
        
        if not all_text or len(all_text) < 100:
            # Return success with empty data instead of error, so frontend can display it
            self.log_action("Insufficient feedback data found, returning empty results")
            return {
                "success": True,
                "customer_themes": [],
                "competitor_analysis": {
                    "competitors": [],
                    "strengths": [],
                    "gaps": []
                },
                "market_trends": [],
                "executive_brief": "No customer feedback or market data found in meeting notes. Please add more meeting notes with customer feedback, competitor mentions, or market trends.",
                "product_bets": []
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
            
            # Create checklist item for executive brief
            if result.get("executive_brief"):
                self.create_checklist_item(
                    item_type="customer_research",
                    title="Customer Research & Market Analysis Complete",
                    description=result.get("executive_brief", "")[:200] + "...",
                    priority="high",
                    action_type="review",
                    metadata=result
                )
            
            return {
                "success": True,
                **result
            }
        except Exception as e:
            self.log_action(f"Error analyzing customer research: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "customer_themes": [],
                "competitor_analysis": {},
                "market_trends": [],
                "executive_brief": ""
            }
    
    def _extract_feedback_text(self, notion_pages: List[Dict], access_token: str) -> str:
        """Extract feedback, reviews, and market-related text from pages."""
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
        """Build prompt for customer research analysis."""
        prompt = f"""Analyze the following meeting notes, feedback, and discussions to extract customer insights, competitor analysis, and market trends.

Content:
{text[:8000]}

Extract and organize the following:

1. **Customer Themes**: Cluster feedback into core themes, identifying:
   - Pain points (what users complain about)
   - Delighters (what users love)
   - Frequency (how often each theme appears)

2. **Competitor Analysis**: Identify:
   - Competitors mentioned
   - Their strengths
   - Our product gaps compared to them

3. **Market Trends**: List trends, risks, and opportunities mentioned

4. **Executive Brief**: Synthesize 1-2 bold product bets with rationale

5. **Product Bets**: List 1-2 key product bets with justification

Return ONLY valid JSON in this format:
{{
  "customer_themes": [
    {{
      "theme": "Performance & Speed",
      "pain_points": ["Dashboard loads too slowly", "Search takes 3-5 seconds"],
      "delighters": ["Real-time collaboration cursors", "Instant sync"],
      "frequency": 15
    }}
  ],
  "competitor_analysis": {{
    "competitors": ["Linear", "Asana"],
    "strengths": ["Linear: Fast, keyboard shortcuts", "Asana: Mobile app"],
    "gaps": ["We lack mobile app", "Keyboard shortcuts missing"]
  }},
  "market_trends": ["AI-powered prioritization trending", "Teams want Slack integration"],
  "executive_brief": "Double down on performance optimization and ship mobile MVP by Q1. Market is moving toward AI-assisted PM tools—we need to differentiate with intelligent automation.",
  "product_bets": [
    "Bet 1: AI-powered story prioritization using meeting context",
    "Bet 2: Mobile-first experience for on-the-go PMs"
  ]
}}

Return ONLY JSON, no markdown formatting."""
        return prompt
    
    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """Parse Gemini response into structured data."""
        try:
            import re
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                response_text = json_match.group(0)
            
            data = json.loads(response_text)
            
            # Ensure all required fields exist
            return {
                "customer_themes": data.get("customer_themes", []),
                "competitor_analysis": data.get("competitor_analysis", {}),
                "market_trends": data.get("market_trends", []),
                "executive_brief": data.get("executive_brief", ""),
                "product_bets": data.get("product_bets", [])
            }
        except Exception as e:
            self.log_action(f"Error parsing response: {str(e)}")
            return {
                "customer_themes": [],
                "competitor_analysis": {},
                "market_trends": [],
                "executive_brief": "",
                "product_bets": []
            }

