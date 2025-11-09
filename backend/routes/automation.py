"""Automation routes for triggering the complete PM workflow pipeline."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any
import time
import json
from datetime import datetime
from database import get_db
from utils.token_manager import get_token
from utils.notion import get_notion_pages
from utils.google_calendar import get_upcoming_events
from utils.agents import (
    StoryExtractionAgent,
    CustomerResearchAgent,
    NoiseClearingAgent,
    CrossTeamAgent,
    MeetingInsightsAgent,
    ReleaseReportAgent,
    SprintPlanningAgent
)

router = APIRouter()


def clear_automation_states(db: Session, user_id: str = "default"):
    """Clear automation states before starting a new automation run.
    
    This ensures we don't have duplicate processing or stale state.
    States cleared:
    - Stories from previous automation runs (archived to prevent accumulation)
    - Processing flags (handled by force_reprocess=True in agents)
    - Cache mechanisms are invalidated automatically via fingerprints when data changes
    
    Args:
        db: Database session
        user_id: User identifier
    """
    from database import Story, ChecklistItem
    from datetime import datetime, timedelta
    
    print("[Meeting Ended Pipeline] Clearing automation states...")
    
    # Archive or delete stories from previous automation runs to prevent accumulation
    # This ensures each automation run starts fresh and doesn't accumulate stories across runs
    try:
        # Archive stories that are pending or approved (from previous runs)
        # We'll archive them so they're not considered in duplicate detection
        stories_to_archive = db.query(Story).filter(
            Story.user_id == user_id,
            Story.status.in_(["pending", "approved"])
        ).all()
        
        if stories_to_archive:
            archived_count = 0
            for story in stories_to_archive:
                # Archive the story so it's not considered in new runs
                story.status = "archived"
                archived_count += 1
            
            db.commit()
            print(f"[Meeting Ended Pipeline] Archived {archived_count} stories from previous runs")
        else:
            print("[Meeting Ended Pipeline] No stories to archive")
            
    except Exception as e:
        print(f"[Meeting Ended Pipeline] Error archiving stories: {str(e)}")
        db.rollback()
        # Continue even if archiving fails
    
    # Clear any pending checklist items from previous automation runs
    # Keep resolved items for history, but clear pending ones to avoid confusion
    try:
        old_pending_items = db.query(ChecklistItem).filter(
            ChecklistItem.user_id == user_id,
            ChecklistItem.status == "pending",
            ChecklistItem.type.in_(["story_approval", "backlog_cleanup", "release_report"])
        ).all()
        
        if old_pending_items:
            for item in old_pending_items:
                db.delete(item)
            db.commit()
            print(f"[Meeting Ended Pipeline] Cleared {len(old_pending_items)} old pending checklist items")
    except Exception as e:
        print(f"[Meeting Ended Pipeline] Error clearing checklist items: {str(e)}")
        db.rollback()
    
    print("[Meeting Ended Pipeline] State clearing complete - ready for fresh automation run")


@router.post("/trigger-meeting-ended")
async def trigger_meeting_ended(
    user_id: str = "default",
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Trigger the complete PM workflow pipeline after a meeting ends.
    
    This endpoint:
    1. Clears automation states to avoid duplicates
    2. Fetches all recent data (Notion pages, meeting notes, backlog items)
    3. Runs all 6 agents sequentially
    4. Collects outputs and creates checklist items
    5. Returns comprehensive summary to frontend
    
    Note: In production, user_id should come from authentication token.
    For now, using "default" as the user_id.
    
    Returns:
        Dict with outputs from all 6 agents and summary statistics
    """
    start_time = time.time()
    
    try:
        # Clear automation states before starting
        clear_automation_states(db, user_id)
        
        # Get tokens
        notion_token = get_token(db, "notion")
        google_token = get_token(db, "google")
        
        if not notion_token:
            raise HTTPException(
                status_code=400,
                detail="Notion not connected. Please connect your Notion account first."
            )
        
        # Fetch recent data
        print("[Meeting Ended Pipeline] Fetching data...")
        notion_pages = get_notion_pages(notion_token.access_token, page_size=100, include_archived=False)
        
        events = None
        if google_token:
            try:
                events, _ = get_upcoming_events(
                    google_token.access_token,
                    google_token.refresh_token,
                    max_results=50
                )
            except Exception as e:
                print(f"Warning: Could not fetch Google Calendar events: {str(e)}")
                events = None
        
        print(f"[Meeting Ended Pipeline] Fetched {len(notion_pages)} pages and {len(events) if events else 0} events")
        
        # Initialize all agents
        story_extraction_agent = StoryExtractionAgent(db, user_id)
        customer_research_agent = CustomerResearchAgent(db, user_id)
        backlog_grooming_agent = NoiseClearingAgent(db, user_id)
        cross_team_agent = CrossTeamAgent(db, user_id)
        meeting_insights_agent = MeetingInsightsAgent(db, user_id)
        reporting_agent = ReleaseReportAgent(db, user_id)
        sprint_planning_agent = SprintPlanningAgent(db, user_id)
        
        # Run all agents (sequentially for now to avoid DB conflicts)
        # TODO: Consider running in parallel with proper DB session handling
        print("[Meeting Ended Pipeline] Running agents...")
        
        outputs = {}
        
        # 0. Story Extraction (must run first to extract stories from meeting notes)
        # Use force_reprocess=True so we can re-process test data and extract new stories
        print("[Meeting Ended Pipeline] Running Story Extraction Agent...")
        try:
            story_extraction = story_extraction_agent.run(
                notion_pages=notion_pages,
                events=events,
                force_reprocess=True  # Always re-process to extract new stories from meeting notes
            )
            outputs["story_extraction"] = story_extraction
            print(f"[Meeting Ended Pipeline] Story Extraction: {story_extraction.get('stories_extracted', 0)} stories extracted")
            if story_extraction.get("notion_page_url"):
                print(f"[Meeting Ended Pipeline] ✅ Notion page created: {story_extraction.get('notion_page_url')}")
            elif story_extraction.get("notion_error"):
                print(f"[Meeting Ended Pipeline] ❌ Notion page creation failed: {story_extraction.get('notion_error')}")
        except Exception as e:
            print(f"Error in story extraction agent: {str(e)}")
            import traceback
            traceback.print_exc()
            outputs["story_extraction"] = {"success": False, "error": str(e)}
        
        # 1. Customer & Market Research
        print("[Meeting Ended Pipeline] Running Customer Research Agent...")
        try:
            customer_research = customer_research_agent.run(notion_pages=notion_pages, events=events)
            outputs["customer_research"] = customer_research
            if customer_research.get("success"):
                print(f"[Meeting Ended Pipeline] Customer Research: {len(customer_research.get('customer_themes', []))} themes found")
            else:
                print(f"[Meeting Ended Pipeline] Customer Research: {customer_research.get('error', 'Unknown error')}")
        except Exception as e:
            print(f"Error in customer research agent: {str(e)}")
            import traceback
            traceback.print_exc()
            outputs["customer_research"] = {"success": False, "error": str(e)}
        
        # 2. Backlog Grooming
        print("[Meeting Ended Pipeline] Running Backlog Grooming Agent...")
        try:
            backlog_grooming = backlog_grooming_agent.run()
            outputs["backlog_grooming"] = backlog_grooming
        except Exception as e:
            print(f"Error in backlog grooming agent: {str(e)}")
            outputs["backlog_grooming"] = {"success": False, "error": str(e)}
        
        # 3. Cross-Team Updates
        print("[Meeting Ended Pipeline] Running Cross-Team Agent...")
        try:
            cross_team = cross_team_agent.run(notion_pages=notion_pages, events=events)
            outputs["cross_team_updates"] = cross_team
            if cross_team.get("success"):
                print(f"[Meeting Ended Pipeline] Cross-Team: {len(cross_team.get('team_highlights', []))} teams, {len(cross_team.get('dependencies', []))} dependencies")
            else:
                print(f"[Meeting Ended Pipeline] Cross-Team: {cross_team.get('error', 'Unknown error')}")
        except Exception as e:
            print(f"Error in cross-team agent: {str(e)}")
            import traceback
            traceback.print_exc()
            outputs["cross_team_updates"] = {"success": False, "error": str(e)}
        
        # 4. Meeting Insights
        print("[Meeting Ended Pipeline] Running Meeting Insights Agent...")
        try:
            meeting_insights = meeting_insights_agent.run(notion_pages=notion_pages, events=events)
            outputs["meeting_insights"] = meeting_insights
            if meeting_insights.get("success"):
                print(f"[Meeting Ended Pipeline] Meeting Insights: {meeting_insights.get('total_meetings', 0)} meetings, {meeting_insights.get('total_action_items', 0)} action items")
            else:
                print(f"[Meeting Ended Pipeline] Meeting Insights: {meeting_insights.get('error', 'Unknown error')}")
        except Exception as e:
            print(f"Error in meeting insights agent: {str(e)}")
            import traceback
            traceback.print_exc()
            outputs["meeting_insights"] = {"success": False, "error": str(e)}
        
        # 5. Reporting & Release Notes
        print("[Meeting Ended Pipeline] Running Reporting Agent...")
        try:
            reporting = reporting_agent.run()
            outputs["reporting"] = reporting
        except Exception as e:
            print(f"Error in reporting agent: {str(e)}")
            outputs["reporting"] = {"success": False, "error": str(e)}
        
        # 6. Sprint Planning
        print("[Meeting Ended Pipeline] Running Sprint Planning Agent...")
        try:
            # Get stories from story extraction output or database
            # Only use stories from the CURRENT run (from story extraction output)
            stories_for_sprint = None
            if outputs.get("story_extraction", {}).get("success"):
                story_data = outputs["story_extraction"]
                # Get Story objects from database - ONLY from current run
                from database import Story
                story_ids = story_data.get("story_ids", [])
                if story_ids:
                    # Only query stories from the current run (by ID list from story extraction)
                    stories_from_db = db.query(Story).filter(
                        Story.id.in_(story_ids),
                        Story.user_id == user_id,
                        Story.status.in_(["pending", "approved"])  # Only active stories
                    ).all()
                    # Convert to dict format
                    priority_order = {"high": 1, "medium": 2, "low": 3}
                    stories_sorted = sorted(
                        stories_from_db,
                        key=lambda s: (
                            priority_order.get(s.priority, 2),
                            -(s.story_points if s.story_points else 0)
                        )
                    )
                    stories_for_sprint = [
                        {
                            "id": s.id,
                            "title": s.title,
                            "description": s.description,
                            "priority": s.priority,
                            "points": s.story_points or (8 if s.priority == "high" else (5 if s.priority == "medium" else 3)),
                            "story_points": s.story_points,
                            "owner": s.owner,
                            "tags": json.loads(s.tags) if s.tags else []
                        }
                        for s in stories_sorted
                    ]
                else:
                    # Fallback: get stories from current run only (last 5 minutes)
                    from datetime import timedelta
                    recent_cutoff = datetime.utcnow() - timedelta(minutes=5)
                    stories_from_db = db.query(Story).filter(
                        Story.user_id == user_id,
                        Story.status.in_(["pending", "approved"]),
                        Story.created_at >= recent_cutoff  # Only current run
                    ).all()
                    if stories_from_db:
                        priority_order = {"high": 1, "medium": 2, "low": 3}
                        stories_sorted = sorted(
                            stories_from_db,
                            key=lambda s: (
                                priority_order.get(s.priority, 2),
                                -(s.story_points if s.story_points else 0)
                            )
                        )
                        stories_for_sprint = [
                            {
                                "id": s.id,
                                "title": s.title,
                                "description": s.description,
                                "priority": s.priority,
                                "points": s.story_points or (8 if s.priority == "high" else (5 if s.priority == "medium" else 3)),
                                "story_points": s.story_points,
                                "owner": s.owner,
                                "tags": json.loads(s.tags) if s.tags else []
                            }
                            for s in stories_sorted
                        ]
            
            sprint_planning = sprint_planning_agent.run(stories=stories_for_sprint)
            outputs["sprint_planning"] = sprint_planning
            if sprint_planning.get("success"):
                print(f"[Meeting Ended Pipeline] Sprint Planning: {len(sprint_planning.get('sprint_scope', []))} items, {sprint_planning.get('total_points', 0)} points")
            else:
                print(f"[Meeting Ended Pipeline] Sprint Planning: {sprint_planning.get('error', 'Unknown error')}")
        except Exception as e:
            print(f"Error in sprint planning agent: {str(e)}")
            import traceback
            traceback.print_exc()
            outputs["sprint_planning"] = {"success": False, "error": str(e)}
        
        # 7. Create Comprehensive Report Page and Backlog Database Entries
        print("[Meeting Ended Pipeline] Creating Notion report and database entries...")
        report_page_data = None
        database_entries_result = None
        
        try:
            from utils.notion_reports import create_comprehensive_report_page, create_backlog_database_entries
            
            # Get stories from story extraction - ONLY from current run
            stories = []
            if outputs.get("story_extraction", {}).get("success"):
                story_data = outputs["story_extraction"]
                # Get Story objects from database - ONLY from current run
                from database import Story
                story_ids = story_data.get("story_ids", [])
                if story_ids:
                    # Only get stories from current run (by ID list)
                    stories = db.query(Story).filter(
                        Story.id.in_(story_ids),
                        Story.user_id == user_id,
                        Story.status.in_(["pending", "approved"])  # Only active stories from current run
                    ).all()
                else:
                    # Fallback: get stories from current run only (last 5 minutes)
                    from datetime import timedelta
                    recent_cutoff = datetime.utcnow() - timedelta(minutes=5)
                    stories = db.query(Story).filter(
                        Story.user_id == user_id,
                        Story.status.in_(["pending", "approved"]),
                        Story.created_at >= recent_cutoff  # Only current run
                    ).order_by(Story.created_at.desc()).limit(100).all()
            
            # Determine meeting name and date from most recent meeting note
            meeting_name = "Meeting"
            meeting_date = datetime.now().isoformat()
            parent_page_id = None
            
            if notion_pages and len(notion_pages) > 0:
                # Use the most recent page as the meeting note
                most_recent_page = notion_pages[0]
                meeting_name = most_recent_page.get("title", "Meeting")
                meeting_date = most_recent_page.get("last_edited_time") or most_recent_page.get("created_time", meeting_date)
                parent_page_id = most_recent_page.get("id")
            
            # If no parent page, try to find one
            if not parent_page_id:
                try:
                    pages = get_notion_pages(notion_token.access_token, page_size=1, include_archived=False)
                    if pages and len(pages) > 0:
                        parent_page_id = pages[0].get("id")
                        meeting_name = pages[0].get("title", "Meeting")
                except Exception as e:
                    print(f"⚠️ Error finding parent page: {str(e)}")
            
            # Create comprehensive report page
            if parent_page_id and stories:
                report_page_data = create_comprehensive_report_page(
                    access_token=notion_token.access_token,
                    parent_page_id=parent_page_id,
                    meeting_name=meeting_name,
                    meeting_date=meeting_date,
                    agent_outputs=outputs,
                    stories=stories
                )
                
                if report_page_data:
                    report_page_url = report_page_data.get("url", "")
                    print(f"✅ Created comprehensive report page: {report_page_url}")
                    
                    # Create backlog database entries for auto-approved stories
                    auto_approved_stories = [s for s in stories if s.status == "approved" and (s.confidence or 0) >= 80]
                    if auto_approved_stories:
                        database_entries_result = create_backlog_database_entries(
                            access_token=notion_token.access_token,
                            stories=auto_approved_stories,
                            report_page_url=report_page_url
                        )
                        
                        if database_entries_result.get("success"):
                            print(f"✅ Created {database_entries_result.get('created_count', 0)} stories in Backlog database")
                        else:
                            print(f"⚠️ Database entries creation had issues: {database_entries_result.get('error', 'Unknown error')}")
                else:
                    print("⚠️ Failed to create report page")
            else:
                print("⚠️ Cannot create report page: missing parent page ID or stories")
        
        except Exception as e:
            print(f"⚠️ Error creating Notion report/database entries: {str(e)}")
            import traceback
            traceback.print_exc()
            # Continue even if report creation fails
        
        # Calculate summary statistics
        processing_time = time.time() - start_time
        
        # Extract summary data
        stories_extracted = 0
        stories_auto_approved = 0
        stories_pending_review = 0
        database_entries_created = 0
        duplicates_found = 0
        insights_generated = 0
        action_items_total = 0
        report_page_url = None
        report_page_title = None
        
        # From story extraction
        if outputs.get("story_extraction", {}).get("success"):
            story_data = outputs["story_extraction"]
            stories_extracted = story_data.get("stories_extracted", 0) or len(story_data.get("stories", []))
            auto_approved_stories = story_data.get("auto_approved_stories", [])
            pending_review_stories = story_data.get("pending_review_stories", [])
            if isinstance(auto_approved_stories, list):
                stories_auto_approved = len(auto_approved_stories)
            else:
                stories_auto_approved = story_data.get("auto_approved_count", 0)
            if isinstance(pending_review_stories, list):
                stories_pending_review = len(pending_review_stories)
            else:
                stories_pending_review = story_data.get("pending_review_count", 0)
        
        # From backlog grooming
        if outputs.get("backlog_grooming", {}).get("success"):
            backlog_data = outputs["backlog_grooming"]
            duplicates_found = backlog_data.get("duplicate_count", len(backlog_data.get("duplicates", [])))
        
        # From meeting insights
        if outputs.get("meeting_insights", {}).get("success"):
            meeting_data = outputs["meeting_insights"]
            meetings = meeting_data.get("meetings", [])
            insights_generated = meeting_data.get("total_meetings", len(meetings))
            action_items_total = meeting_data.get("total_action_items", 0) or sum(len(m.get("action_items", [])) for m in meetings)
        
        # From customer research
        if outputs.get("customer_research", {}).get("success"):
            customer_data = outputs["customer_research"]
            themes = customer_data.get("customer_themes", [])
            insights_generated += len(themes)
        
        # From cross-team updates
        if outputs.get("cross_team_updates", {}).get("success"):
            cross_team_data = outputs["cross_team_updates"]
            recommended_actions = cross_team_data.get("recommended_actions", [])
            action_items_total += len(recommended_actions)
        
        # From report/database creation
        if report_page_data:
            report_page_url = report_page_data.get("url", "")
            report_page_title = report_page_data.get("title", "")
        
        if database_entries_result and database_entries_result.get("success"):
            database_entries_created = database_entries_result.get("created_count", 0)
        
        summary = {
            "stories_extracted": stories_extracted,
            "stories_auto_approved": stories_auto_approved,
            "stories_pending_review": stories_pending_review,
            "database_entries_created": database_entries_created,
            "duplicates_found": duplicates_found,
            "insights_generated": insights_generated,
            "action_items_total": action_items_total,
            "report_page_url": report_page_url,
            "report_page_title": report_page_title
        }
        
        print(f"[Meeting Ended Pipeline] Complete! Processing time: {processing_time:.2f}s")
        
        # Log summary
        if database_entries_created > 0:
            print(f"✅ {database_entries_created} stories auto-created in Backlog Database")
        if report_page_url:
            print(f"📄 Full report page: {report_page_title or 'Meeting Ended Report'}")
            print(f"   URL: {report_page_url}")
        if stories_pending_review > 0:
            print(f"⚠️ {stories_pending_review} stories need review (see report page)")
        
        return {
            "success": True,
            "processing_time_seconds": round(processing_time, 2),
            "outputs": outputs,
            "summary": summary,
            "report_page": report_page_data,
            "database_entries": database_entries_result
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error running meeting ended pipeline: {str(e)}"
        )

