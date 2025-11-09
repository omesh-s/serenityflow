"""Story Extraction Agent - extracts stories/backlog items from meetings and notes."""
import json
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from .base_agent import BaseAgent
from utils.gemini import initialize_gemini
from utils.notion import get_notion_pages, get_page_content, create_notion_page, find_notion_database
import google.generativeai as genai
from config import settings


class StoryExtractionAgent(BaseAgent):
    """Agent that extracts stories/backlog items from meeting notes and Notion pages."""
    
    def __init__(self, db_session, user_id: str = "default"):
        """Initialize the story extraction agent."""
        super().__init__(db_session, user_id)
        initialize_gemini()
        # Use gemini-2.5-flash-lite for faster extraction (it's faster and cheaper for this task)
        self.model = genai.GenerativeModel('gemini-2.5-flash-lite')
    
    def run(self, notion_pages: Optional[List[Dict]] = None, events: Optional[List[Dict]] = None, force_reprocess: bool = False) -> Dict[str, Any]:
        """Run story extraction on new/updated meeting notes and Notion pages.
        
        Args:
            notion_pages: List of Notion pages to process (if None, fetches recent pages)
            events: List of calendar events (for context)
        
        Returns:
            Dict with extracted stories, checklist items, and metadata
        """
        from database import Story
        from utils.token_manager import get_token
        
        self.log_action("Starting story extraction")
        
        # Get Notion token
        notion_token = get_token(self.db, "notion")
        if not notion_token:
            self.log_action("Notion not connected, skipping story extraction")
            return {
                "success": False,
                "error": "Notion not connected",
                "stories": [],
                "checklist_items": []
            }
        
        # Fetch recent Notion pages if not provided
        if notion_pages is None:
            try:
                self.log_action("Fetching Notion pages...")
                # Fetch ALL pages with pagination (no limit, but will stop if API doesn't return more)
                notion_pages = get_notion_pages(notion_token.access_token, page_size=100, include_archived=False)
                self.log_action(f"Fetched {len(notion_pages)} Notion pages (all available pages)")
                
                if len(notion_pages) == 0:
                    return {
                        "success": False,
                        "error": "No Notion pages found. Make sure you have pages in your workspace and the integration has access to them.",
                        "stories": [],
                        "checklist_items": []
                    }
            except Exception as e:
                error_msg = str(e)
                self.log_action(f"Error fetching Notion pages: {error_msg}")
                import traceback
                traceback.print_exc()
                return {
                    "success": False,
                    "error": f"Failed to fetch Notion pages: {error_msg}",
                    "stories": [],
                    "checklist_items": []
                }
        
        # Get existing stories to avoid duplicates WITHIN THIS RUN
        # Only check for stories created in the current session/run (last few minutes)
        # This prevents accumulation across multiple automation runs
        from datetime import timedelta
        recent_cutoff = datetime.utcnow() - timedelta(minutes=5)
        
        # Only check for stories created very recently (in current run) to avoid duplicates within the same run
        # Stories from previous runs should have been archived by clear_automation_states()
        existing_stories = self.db.query(Story).filter(
            Story.user_id == self.user_id,
            Story.status.in_(["pending", "approved"]),
            Story.created_at >= recent_cutoff  # Only check stories from current run (last 5 minutes)
        ).all()
        
        # Build sets for duplicate detection within current run only
        existing_source_ids = {s.source_id for s in existing_stories if s.source_id} if not force_reprocess else set()
        existing_story_titles = {(s.title.lower().strip(), s.source_id) for s in existing_stories if s.title and s.source_id} if not force_reprocess else set()
        
        if force_reprocess:
            self.log_action("Force reprocess mode: Will re-process all pages even if already processed")
            self.log_action(f"Existing stories in current run (last 5 min): {len(existing_stories)}")
        else:
            self.log_action(f"Checking against {len(existing_stories)} existing stories from current run to avoid duplicates")
        
        # Process each page that hasn't been processed yet
        extracted_stories = []
        checklist_item_ids = []
        
        # Process pages from the last 30 days (increased from 7 to catch more pages)
        # For manual triggers, we'll process all pages regardless of date
        from datetime import timezone
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=30)
        
        self.log_action(f"Processing {len(notion_pages)} Notion pages in parallel (cutoff: {cutoff_date}, force_reprocess: {force_reprocess})")
        processed_count = 0
        skipped_already_processed = 0
        skipped_too_old = 0
        
        # Filter pages first (fast operations)
        pages_to_process = []
        for page in notion_pages:
            page_id = page.get("id")
            if not force_reprocess and page_id in existing_source_ids:
                skipped_already_processed += 1
                self.log_action(f"Skipping page {page_id} - already processed (use force_reprocess=True to re-process)")
                continue
            
            # Check date (skip date check if force_reprocess is True to allow processing old test data)
            if not force_reprocess:
                page_edited = page.get("last_edited_time")
                if page_edited:
                    try:
                        from dateutil import parser as date_parser
                        from datetime import timezone
                        edited_date = date_parser.isoparse(page_edited)
                        if edited_date.tzinfo is None:
                            edited_date = edited_date.replace(tzinfo=timezone.utc)
                        else:
                            edited_date = edited_date.astimezone(timezone.utc)
                        
                        if cutoff_date.tzinfo is None:
                            cutoff_date_local = cutoff_date.replace(tzinfo=timezone.utc)
                        else:
                            cutoff_date_local = cutoff_date
                        
                        if edited_date < cutoff_date_local:
                            skipped_too_old += 1
                            continue
                    except:
                        pass  # Continue if date parsing fails
            
            pages_to_process.append(page)
        
        # Process pages in parallel for faster extraction
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        def extract_from_page(page):
            """Extract stories from a single page (thread-safe, no DB operations).
            
            Creates its own model instance to avoid thread-safety issues.
            """
            try:
                # Create a new model instance for this thread (Gemini models are not thread-safe)
                initialize_gemini()
                thread_model = genai.GenerativeModel('gemini-2.5-flash-lite')
                
                page_id = page.get("id")
                page_title = page.get("title", "Untitled")
                stories = self._extract_stories_from_page(page, notion_token.access_token, events, model=thread_model)
                return {
                    "page_id": page_id,
                    "page_title": page_title,
                    "stories": stories,
                    "success": True
                }
            except Exception as e:
                return {
                    "page_id": page.get("id"),
                    "error": str(e),
                    "success": False
                }
        
        # Process up to 5 pages in parallel (to avoid rate limits)
        page_results = []
        if pages_to_process:
            self.log_action(f"Extracting stories from {len(pages_to_process)} pages in parallel...")
            with ThreadPoolExecutor(max_workers=5) as executor:
                future_to_page = {executor.submit(extract_from_page, page): page for page in pages_to_process}
                for future in as_completed(future_to_page):
                    result = future.result()
                    page_results.append(result)
                    if result.get("success"):
                        self.log_action(f"Extracted {len(result.get('stories', []))} stories from: {result.get('page_title')}")
        
        # Now create story records (sequential for DB safety)
        for result in page_results:
            if not result.get("success"):
                continue
            
            page_id = result.get("page_id")
            stories = result.get("stories", [])
            processed_count += 1
            
            for story_data in stories:
                # Skip if story already exists in CURRENT RUN (unless force_reprocess is True)
                # Check both by query and by in-memory set for efficiency
                story_title = story_data.get("title", "Untitled Story")
                title_key = (story_title.lower().strip(), page_id)
                
                if not force_reprocess:
                    # Check in-memory set first (fast)
                    if title_key in existing_story_titles:
                        self.log_action(f"Skipping duplicate story: {story_title} (already exists in current run)")
                        continue
                    
                    # Also check database for safety (in case story was just created)
                    existing_story = self.db.query(Story).filter(
                        Story.title == story_title,
                        Story.source_id == page_id,
                        Story.user_id == self.user_id,
                        Story.status.in_(["pending", "approved"]),
                        Story.created_at >= recent_cutoff  # Only check current run
                    ).first()
                    
                    if existing_story:
                        # Add to set to prevent future duplicates in this run
                        existing_story_titles.add(title_key)
                        continue
                
                # Auto-approve if confidence ≥ 80%
                confidence = story_data.get("confidence", 70)
                status = "approved" if confidence >= 80 else "pending"
                approved_at = datetime.utcnow() if status == "approved" else None
                
                # Create story record
                story = Story(
                    id=str(uuid.uuid4()),
                    title=story_data.get("title", "Untitled Story"),
                    description=story_data.get("description"),
                    priority=story_data.get("priority", "medium"),
                    status=status,
                    tags=json.dumps(story_data.get("tags", [])),
                    owner=story_data.get("owner"),
                    source_type="notion",
                    source_id=page_id,
                    user_id=self.user_id,
                    extracted_at=datetime.utcnow(),
                    approved_at=approved_at,
                    confidence=confidence,
                    story_points=story_data.get("story_points", 5),
                    product=story_data.get("product", "SerenityFlow")
                )
                
                self.db.add(story)
                extracted_stories.append(story)
                
                # Add to existing_story_titles set to prevent duplicates within this run
                if not force_reprocess:
                    existing_story_titles.add(title_key)
        
        # Commit all stories
        if extracted_stories:
            try:
                self.db.commit()
                
                # Auto-approve high-confidence stories
                auto_approved = [s for s in extracted_stories if s.status == "approved"]
                pending_review = [s for s in extracted_stories if s.status == "pending"]
                
                # Update sort rankings in database (for report page display)
                priority_order = {"high": 1, "medium": 2, "low": 3}
                all_stories = auto_approved + pending_review
                all_stories.sort(
                    key=lambda s: (
                        priority_order.get(s.priority, 2),
                        -(s.story_points if s.story_points else 0)
                    )
                )
                
                for idx, story in enumerate(all_stories):
                    story.sort_ranking = idx + 1
                
                # Don't create Notion pages here - will be created in comprehensive report
                # Just update the database
                self.db.commit()
                
                self.log_action(f"✅ Extracted {len(extracted_stories)} stories: {len(auto_approved)} auto-approved, {len(pending_review)} pending review")
                
                # Store stories in result for report generation
                result["stories"] = extracted_stories
                result["auto_approved_stories"] = auto_approved
                result["pending_review_stories"] = pending_review
                
                # Store story IDs in result for report generation
                result["story_ids"] = [s.id for s in extracted_stories]
                
                # Create checklist item for story approvals (only for pending stories)
                if pending_review:
                    story_ids = [s.id for s in pending_review]
                    checklist_id = self.create_checklist_item(
                        item_type="story_approval",
                        title=f"{len(pending_review)} story(s) need review",
                        description=f"Review and approve {len(pending_review)} story(s) extracted from meeting notes. {len(auto_approved)} story(s) were auto-approved (confidence ≥ 80%).",
                        priority="high" if len(pending_review) > 5 else "medium",
                        action_type="approve",
                        action_data={
                            "story_ids": story_ids,
                            "count": len(pending_review),
                            "auto_approved_count": len(auto_approved)
                        },
                        metadata={
                            "source": "story_extraction_agent",
                            "extracted_at": datetime.utcnow().isoformat(),
                            "auto_approved": len(auto_approved),
                            "pending_review": len(pending_review)
                        }
                    )
                    checklist_item_ids.append(checklist_id)
            except Exception as e:
                self.log_action(f"Error committing stories: {str(e)}")
                self.db.rollback()
                return {
                    "success": False,
                    "error": f"Database error: {str(e)}",
                    "stories": [],
                    "checklist_items": []
                }
        
        self.log_action(f"Extracted {len(extracted_stories)} stories from {processed_count} pages (skipped: {skipped_already_processed} already processed, {skipped_too_old} too old)")
        
        result = {
            "success": True,
            "stories": [
                {
                    "id": s.id,
                    "title": s.title,
                    "description": s.description,
                    "priority": s.priority,
                    "status": s.status
                }
                for s in extracted_stories
            ],
            "checklist_items": checklist_item_ids,
            "count": len(extracted_stories),
            "stories_extracted": len(extracted_stories),  # Add this for summary
            "auto_approved_count": len(auto_approved) if isinstance(auto_approved, list) else 0,
            "pending_review_count": len(pending_review) if isinstance(pending_review, list) else 0,
            "pages_processed": processed_count,
            "pages_skipped_already_processed": skipped_already_processed,
            "pages_skipped_too_old": skipped_too_old,
            "total_pages": len(notion_pages),
            "stats": {
                "total_pages": len(notion_pages),
                "pages_processed": processed_count,
                "pages_skipped_already_processed": skipped_already_processed,
                "pages_skipped_too_old": skipped_too_old,
                "stories_extracted": len(extracted_stories)
            }
        }
        
        # If no stories extracted, provide helpful message
        if len(extracted_stories) == 0:
            if processed_count == 0:
                if skipped_already_processed > 0:
                    result["message"] = f"All {skipped_already_processed} page(s) have already been processed. No new stories to extract. Use 'Force Reprocess' to re-process pages."
                elif skipped_too_old > 0:
                    result["message"] = f"All {skipped_too_old} page(s) are older than 30 days. No recent pages to process."
                elif len(notion_pages) == 0:
                    result["message"] = "No Notion pages found. Make sure you have pages in your workspace."
                else:
                    result["message"] = f"Processed {processed_count} pages but found no extractable stories. Make sure your pages contain meeting notes with action items."
            else:
                result["message"] = f"Processed {processed_count} pages but found no extractable stories. Make sure your pages contain meeting notes with action items."
        else:
            # Success message with stats
            result["message"] = f"Successfully extracted {len(extracted_stories)} stories from {processed_count} page(s)."
            if skipped_already_processed > 0:
                result["message"] += f" {skipped_already_processed} page(s) were skipped (already processed)."
        
        return result
    
    def _extract_stories_from_page(self, page: Dict, access_token: str, events: Optional[List[Dict]] = None, model=None) -> List[Dict]:
        """Extract stories from a Notion page using Gemini.
        
        Args:
            page: Notion page data
            access_token: Notion API access token
            events: Optional calendar events for context
        
        Returns:
            List of extracted story dictionaries
        """
        try:
            # Get full page content (this is the main time consumer, but necessary)
            page_content = get_page_content(access_token, page.get("id"))
            page_text = self._extract_text_from_page_content(page_content)
            
            if not page_text or len(page_text) < 50:
                return []
            
            # Build prompt with enhanced metadata extraction
            page_title = page.get('title', 'Untitled')
            prompt = self._build_extraction_prompt(page_text, {'title': page_title}, events)
            
            # Use provided model or fall back to instance model
            model_to_use = model if model is not None else self.model
            
            # Call Gemini API with optimized settings for speed
            try:
                response = model_to_use.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.1,  # Lower temperature = faster, more deterministic
                        max_output_tokens=2048,  # Limit output to speed up
                        top_p=0.8,  # Reduced for faster generation
                    )
                )
                response_text = response.text
            except Exception as e:
                self.log_action(f"Error calling Gemini API: {str(e)}")
                return []
            
            # Parse response
            stories = self._parse_extraction_response(response_text)
            return stories
            
        except Exception as e:
            self.log_action(f"Error extracting stories from page: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
    
    def _extract_text_from_page_content(self, page_content: Dict) -> str:
        """Extract plain text from Notion page content.
        
        Args:
            page_content: Notion page content dictionary
        
        Returns:
            Plain text content
        """
        text_parts = []
        
        # Add title
        title = page_content.get("title", "")
        if title:
            text_parts.append(f"Title: {title}")
        
        # Add content blocks
        content = page_content.get("content", [])
        for block in content:
            block_text = block.get("text", "")
            if block_text:
                text_parts.append(block_text)
        
        return "\n".join(text_parts)
    
    def _build_extraction_prompt(self, page_text: str, page: Dict, events: Optional[List[Dict]] = None) -> str:
        """Build optimized prompt for faster story extraction.
        
        Args:
            page_text: Plain text content of the page
            page: Notion page metadata
            events: Optional calendar events for context
        
        Returns:
            Prompt string for Gemini (optimized for speed)
        """
        page_title = page.get('title', 'Untitled') if isinstance(page, dict) else str(page)
        
        prompt = f"""You are a product manager extracting actionable stories/backlog items from meeting notes.

Meeting Notes:
Title: {page_title}

Content:
{page_text[:4000]}

Extract all actionable stories/backlog items from this meeting. Look for:
- Action items with owners
- Feature requests
- Bug fixes
- Improvements
- Tasks assigned to specific people

For each story, extract:
1. Title (clear, actionable)
2. Description (what needs to be done)
3. Priority (High, Medium, Low) - based on urgency and importance
4. Owner (who is responsible, if mentioned)
5. Tags (relevant keywords like "feature", "bug", "performance", etc.)
6. Product (product name, e.g., "SerenityFlow" if mentioned, otherwise infer from context)
7. Story Points (estimate: 1, 2, 3, 5, 8, 13, 21 using Fibonacci sequence)
8. Confidence (0-100, how confident you are this is a valid, complete story)

Confidence scoring:
- 90-100: Clear, complete story with owner, priority, and description
- 80-89: Good story with most details, minor ambiguity
- 70-79: Story exists but missing some details (owner, priority, etc.)
- 60-69: Vague or incomplete story
- Below 60: Not a valid story, skip it

Return ONLY valid JSON in this format:
{{
  "stories": [
    {{
      "title": "Implement Google OAuth login",
      "description": "Add Google OAuth authentication to allow users to sign in with their Google accounts",
      "priority": "High",
      "owner": "Alice",
      "tags": ["authentication", "feature", "oauth"],
      "product": "SerenityFlow",
      "story_points": 5,
      "confidence": 92
    }}
  ]
}}

Return ONLY JSON, no markdown formatting."""
        
        return prompt
    
    def _parse_extraction_response(self, response_text: str) -> List[Dict]:
        """Parse Gemini's response into story dictionaries.
        
        Args:
            response_text: Response text from Gemini
        
        Returns:
            List of story dictionaries
        """
        try:
            if not response_text:
                self.log_action("Empty response from Gemini")
                return []
            
            # Try to extract JSON from response
            # Gemini might wrap JSON in markdown code blocks
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
                    # Only log if we can't find JSON (error case)
                    self.log_action(f"Could not find JSON in response. Response: {response_text[:200]}")
                    return []
            
            # Parse JSON
            data = json.loads(response_text)
            stories = data.get("stories", [])
            
            if not stories:
                return []
            
            # Validate and normalize stories
            validated_stories = []
            for story in stories:
                if not story.get("title"):
                    continue
                
                # Normalize priority
                priority = story.get("priority", "medium").lower()
                if priority not in ["high", "medium", "low"]:
                    priority = "medium"
                
                # Validate confidence (default to 70 if not provided)
                confidence = story.get("confidence", 70)
                if not isinstance(confidence, (int, float)) or confidence < 0:
                    confidence = 70
                confidence = min(100, max(0, float(confidence)))
                
                # Validate story points (default to 5 if not provided)
                story_points = story.get("story_points", 5)
                if not isinstance(story_points, int) or story_points < 1:
                    story_points = 5
                
                validated_story = {
                    "title": story.get("title", "Untitled Story"),
                    "description": story.get("description", ""),
                    "priority": priority,
                    "owner": story.get("owner"),
                    "tags": story.get("tags", []),
                    "product": story.get("product", "SerenityFlow"),
                    "story_points": story_points,
                    "confidence": confidence
                }
                
                validated_stories.append(validated_story)
            
            return validated_stories
            
        except json.JSONDecodeError as e:
            self.log_action(f"JSON decode error: {str(e)}")
            self.log_action(f"Response text (first 500 chars): {response_text[:500]}")
            return []
        except Exception as e:
            self.log_action(f"Error parsing extraction response: {str(e)}")
            self.log_action(f"Response text (first 500 chars): {response_text[:500]}")
            import traceback
            traceback.print_exc()
            return []
    
    def approve_stories(self, story_ids: List[str], create_in_notion: bool = True, database_id: Optional[str] = None) -> Dict[str, Any]:
        """Approve stories and optionally create them in Notion.
        
        Args:
            story_ids: List of story IDs to approve
            create_in_notion: Whether to create stories in Notion workspace
            database_id: Optional Notion database ID (if None, will try to find one)
        
        Returns:
            Dict with approval results
        """
        from database import Story
        from utils.token_manager import get_token
        import json
        
        self.log_action(f"Approving {len(story_ids)} stories (create_in_notion={create_in_notion})")
        
        # Get stories
        stories = self.db.query(Story).filter(
            Story.id.in_(story_ids),
            Story.user_id == self.user_id
        ).all()
        
        if not stories:
            return {
                "success": False,
                "error": "No stories found",
                "approved": 0,
                "created_in_notion": []
            }
        
        # Get Notion token
        notion_token = get_token(self.db, "notion")
        if not notion_token and create_in_notion:
            self.log_action("Notion not connected, approving stories without creating in Notion")
            create_in_notion = False
        
        approved_count = 0
        created_in_notion = []
        errors = []
        
        # Find database if not provided
        if create_in_notion and notion_token and not database_id:
            try:
                database_id = find_notion_database(notion_token.access_token, "Backlog")
                if database_id:
                    self.log_action(f"Found Notion database: {database_id}")
                else:
                    self.log_action("No Notion database found, will create standalone pages")
            except Exception as e:
                self.log_action(f"Error finding Notion database: {str(e)}")
        
        for story in stories:
            try:
                # Update story status
                story.status = "approved"
                story.approved_at = datetime.utcnow()
                
                # Create in Notion if requested
                if create_in_notion and notion_token:
                    try:
                        # Parse tags
                        tags = []
                        if story.tags:
                            try:
                                tags = json.loads(story.tags) if isinstance(story.tags, str) else story.tags
                            except:
                                tags = []
                        
                        # Build properties
                        properties = {
                            "priority": story.priority or "medium",
                            "status": "approved",
                            "owner": story.owner,
                            "tags": tags
                        }
                        
                        # Create Notion page
                        notion_page = create_notion_page(
                            access_token=notion_token.access_token,
                            database_id=database_id,
                            title=story.title,
                            description=story.description or "",
                            properties=properties
                        )
                        
                        # Store Notion page ID
                        story.notion_page_id = notion_page.get("id")
                        created_in_notion.append({
                            "story_id": story.id,
                            "notion_page_id": story.notion_page_id,
                            "url": notion_page.get("url", "")
                        })
                        
                        self.log_action(f"Created Notion page for story: {story.title} (ID: {story.notion_page_id})")
                        
                    except Exception as e:
                        error_msg = f"Error creating story '{story.title}' in Notion: {str(e)}"
                        self.log_action(error_msg)
                        errors.append(error_msg)
                        # Still approve the story even if Notion creation fails
                
                approved_count += 1
                
            except Exception as e:
                error_msg = f"Error approving story {story.id}: {str(e)}"
                self.log_action(error_msg)
                errors.append(error_msg)
                continue
        
        # Commit changes
        try:
            self.db.commit()
        except Exception as e:
            self.log_action(f"Error committing changes: {str(e)}")
            self.db.rollback()
            return {
                "success": False,
                "error": f"Database error: {str(e)}",
                "approved": 0,
                "created_in_notion": []
            }
        
        self.log_action(f"Approved {approved_count} stories (created_in_notion: {len(created_in_notion)}, errors: {len(errors)})")
        
        result = {
            "success": True,
            "approved": approved_count,
            "created_in_notion": created_in_notion
        }
        
        if errors:
            result["errors"] = errors
            result["warning"] = f"Some stories were approved but {len(errors)} error(s) occurred"
        
        return result

