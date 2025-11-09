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
        self.model = genai.GenerativeModel('gemini-2.5-flash-lite')
    
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
        
        self.log_action(f"Extracted {len(all_text) if all_text else 0} characters from {len(notion_pages)} pages")
        
        # Lower threshold and always try to analyze if we have any text
        if not all_text or len(all_text) < 20:
            # Return success with empty data instead of error, so frontend can display it
            self.log_action(f"Insufficient feedback data found ({len(all_text) if all_text else 0} chars), returning empty results")
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
                    max_output_tokens=8192,  # Increased to handle larger responses
                )
            )
            # Get response text safely (avoid accessing finish_message)
            response_text = ""
            finish_reason = None
            try:
                # First try the standard .text property (this usually works even with MAX_TOKENS)
                if hasattr(response, 'text'):
                    try:
                        response_text = response.text
                        if response_text:
                            self.log_action(f"Extracted {len(response_text)} characters using response.text")
                    except Exception as e:
                        self.log_action(f"Error accessing response.text: {str(e)}")
                
                # If that didn't work, try extracting from candidates
                if not response_text and hasattr(response, 'candidates') and response.candidates:
                    candidate = response.candidates[0]
                    if hasattr(candidate, 'finish_reason'):
                        finish_reason = candidate.finish_reason
                        self.log_action(f"Response finish_reason: {finish_reason}")
                    
                    # Extract text from candidate
                    if hasattr(candidate, 'content'):
                        content = candidate.content
                        if hasattr(content, 'parts') and content.parts:
                            # Extract text from parts
                            text_parts = []
                            for part in content.parts:
                                if hasattr(part, 'text'):
                                    text_parts.append(part.text)
                            response_text = "".join(text_parts)
                            if response_text:
                                self.log_action(f"Extracted {len(response_text)} characters from candidate.content.parts")
                        elif hasattr(content, 'text'):
                            response_text = content.text
                            if response_text:
                                self.log_action(f"Extracted {len(response_text)} characters from candidate.content.text")
                
                # Last resort: try to convert to string (but this won't give us the actual text)
                if not response_text:
                    self.log_action("Warning: Could not extract text from response. Response structure:")
                    self.log_action(f"Response type: {type(response)}")
                    if hasattr(response, 'candidates') and response.candidates:
                        candidate = response.candidates[0]
                        self.log_action(f"Candidate type: {type(candidate)}")
                        self.log_action(f"Candidate attributes: {dir(candidate)}")
                    raise Exception("Could not extract text from response - no text content found")
                    
            except Exception as e:
                self.log_action(f"Error extracting response text: {str(e)}")
                raise Exception(f"Could not extract response text: {str(e)}")
            
            if not response_text:
                raise Exception("Empty response from Gemini")
            
            # Log warning if response was truncated
            if finish_reason == "MAX_TOKENS":
                self.log_action(f"Warning: Response was truncated (MAX_TOKENS). Extracted {len(response_text)} characters. Will try to parse partial JSON.")
            
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
        pages_processed = 0
        pages_with_content = 0
        
        for page in notion_pages[:20]:  # Limit to recent 20 pages
            try:
                pages_processed += 1
                page_content = get_page_content(access_token, page.get("id"))
                page_text = self._extract_text_from_content(page_content)
                if page_text:
                    pages_with_content += 1
                    text_parts.append(f"Page: {page.get('title', 'Untitled')}\n{page_text}")
                    self.log_action(f"Extracted {len(page_text)} chars from page: {page.get('title', 'Untitled')}")
            except Exception as e:
                self.log_action(f"Error extracting content from page {page.get('id')}: {str(e)}")
                continue
        
        total_text = "\n\n".join(text_parts)
        self.log_action(f"Extracted text from {pages_with_content}/{pages_processed} pages, total {len(total_text)} characters")
        return total_text
    
    def _extract_text_from_content(self, page_content: Dict) -> str:
        """Extract plain text from page content."""
        text_parts = []
        content = page_content.get("content", [])
        for block in content:
            # Try different block text extraction methods
            block_text = ""
            if isinstance(block, dict):
                # Try common text fields
                if "text" in block:
                    block_text = block["text"]
                elif "rich_text" in block:
                    # Extract from rich_text array
                    rich_text = block.get("rich_text", [])
                    if isinstance(rich_text, list):
                        block_text = " ".join([item.get("plain_text", "") for item in rich_text if isinstance(item, dict)])
                elif "paragraph" in block:
                    rich_text = block["paragraph"].get("rich_text", [])
                    block_text = " ".join([item.get("plain_text", "") for item in rich_text if isinstance(item, dict)])
                elif "heading_1" in block or "heading_2" in block or "heading_3" in block:
                    heading_type = "heading_1" if "heading_1" in block else ("heading_2" if "heading_2" in block else "heading_3")
                    rich_text = block[heading_type].get("rich_text", [])
                    block_text = " ".join([item.get("plain_text", "") for item in rich_text if isinstance(item, dict)])
                elif "bulleted_list_item" in block:
                    rich_text = block["bulleted_list_item"].get("rich_text", [])
                    block_text = " ".join([item.get("plain_text", "") for item in rich_text if isinstance(item, dict)])
                elif "numbered_list_item" in block:
                    rich_text = block["numbered_list_item"].get("rich_text", [])
                    block_text = " ".join([item.get("plain_text", "") for item in rich_text if isinstance(item, dict)])
            
            if block_text:
                text_parts.append(block_text)
        return "\n".join(text_parts)
    
    def _build_analysis_prompt(self, text: str, events: Optional[List[Dict]] = None) -> str:
        """Build prompt for customer research analysis."""
        # Reduce input size to leave more room for output
        prompt = f"""Analyze the following meeting notes, feedback, and discussions to extract customer insights, competitor analysis, and market trends.

Content:
{text[:6000]}

Extract and organize the following (be concise):

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

Return ONLY valid JSON in this format (limit to top 5 themes, 3 competitors, 3 trends):
{{
  "customer_themes": [
    {{
      "theme": "Performance & Speed",
      "pain_points": ["Dashboard loads too slowly"],
      "delighters": ["Real-time collaboration"],
      "frequency": 15
    }}
  ],
  "competitor_analysis": {{
    "competitors": ["Linear", "Asana"],
    "strengths": ["Linear: Fast", "Asana: Mobile app"],
    "gaps": ["We lack mobile app"]
  }},
  "market_trends": ["AI-powered prioritization", "Slack integration"],
  "executive_brief": "Focus on performance optimization and mobile MVP. Market moving toward AI-assisted PM tools.",
  "product_bets": [
    "AI-powered story prioritization",
    "Mobile-first experience"
  ]
}}

Return ONLY JSON, no markdown formatting. Keep responses concise."""
        return prompt
    
    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """Parse Gemini response into structured data."""
        try:
            import re
            # Extract JSON from response (handle markdown code blocks)
            json_match = re.search(r'```(?:json)?\s*(\{.*\})\s*```', response_text, re.DOTALL)
            if json_match:
                response_text = json_match.group(1)
            else:
                # Try to find JSON object directly
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    response_text = json_match.group(0)
            
            # Try to fix truncated JSON by finding balanced braces and brackets
            if response_text:
                # Find the start of the JSON object
                start_pos = response_text.find('{')
                if start_pos == -1:
                    self.log_action("No JSON object found in response")
                    raise ValueError("No JSON found in response")
                
                # Track braces and brackets to find the end of valid JSON
                brace_count = 0
                bracket_count = 0
                in_string = False
                escape_next = False
                last_valid_pos = start_pos
                
                for i in range(start_pos, len(response_text)):
                    char = response_text[i]
                    
                    if escape_next:
                        escape_next = False
                        continue
                    
                    if char == '\\':
                        escape_next = True
                        continue
                    
                    if char == '"' and not escape_next:
                        in_string = not in_string
                        continue
                    
                    if not in_string:
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0 and bracket_count == 0:
                                last_valid_pos = i + 1
                                break
                        elif char == '[':
                            bracket_count += 1
                        elif char == ']':
                            bracket_count -= 1
                            if brace_count == 0 and bracket_count == 0:
                                last_valid_pos = i + 1
                                break
                
                if last_valid_pos > start_pos:
                    response_text = response_text[start_pos:last_valid_pos]
                else:
                    # If we couldn't find balanced braces, try to extract just the customer_themes array
                    themes_match = re.search(r'"customer_themes"\s*:\s*\[(.*?)\]', response_text, re.DOTALL)
                    if themes_match:
                        # Try to parse just the themes array
                        try:
                            themes_json = '[' + themes_match.group(1) + ']'
                            # Find balanced brackets for the array
                            bracket_count = 0
                            last_valid_pos = 0
                            for i, char in enumerate(themes_json):
                                if char == '[':
                                    bracket_count += 1
                                elif char == ']':
                                    bracket_count -= 1
                                    if bracket_count == 0:
                                        last_valid_pos = i + 1
                                        break
                            if last_valid_pos > 0:
                                themes_json = themes_json[:last_valid_pos]
                                themes_list = json.loads(themes_json)
                                # Return partial data
                                self.log_action(f"Extracted {len(themes_list)} themes from partial JSON")
                                return {
                                    "customer_themes": themes_list,
                                    "competitor_analysis": {},
                                    "market_trends": [],
                                    "executive_brief": "",
                                    "product_bets": []
                                }
                        except:
                            pass
            
            data = json.loads(response_text)
            
            # Ensure all required fields exist
            result = {
                "customer_themes": data.get("customer_themes", []),
                "competitor_analysis": data.get("competitor_analysis", {}),
                "market_trends": data.get("market_trends", []),
                "executive_brief": data.get("executive_brief", ""),
                "product_bets": data.get("product_bets", [])
            }
            
            # Log results for debugging
            if not result["customer_themes"]:
                self.log_action(f"No customer themes found. Response keys: {list(data.keys()) if isinstance(data, dict) else 'not a dict'}")
                self.log_action(f"Full response (first 1000 chars): {response_text[:1000]}")
            else:
                self.log_action(f"Parsed {len(result['customer_themes'])} customer themes")
            
            return result
        except json.JSONDecodeError as e:
            self.log_action(f"JSON decode error: {str(e)}")
            self.log_action(f"Response text (first 1000 chars): {response_text[:1000]}")
            return {
                "customer_themes": [],
                "competitor_analysis": {},
                "market_trends": [],
                "executive_brief": "",
                "product_bets": []
            }
        except Exception as e:
            self.log_action(f"Error parsing response: {str(e)}")
            import traceback
            self.log_action(f"Traceback: {traceback.format_exc()}")
            # Log first 1000 chars of response for debugging
            if response_text:
                self.log_action(f"Response text (first 1000 chars): {response_text[:1000]}")
            return {
                "customer_themes": [],
                "competitor_analysis": {},
                "market_trends": [],
                "executive_brief": "",
                "product_bets": []
            }

