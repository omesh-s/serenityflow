"""Automation scheduler for running agents in the background."""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import atexit
from database import SessionLocal, get_db
from utils.agents import StoryExtractionAgent, NoiseClearingAgent, ReleaseReportAgent, StakeholderAgent
from utils.google_calendar import get_events, get_upcoming_events
from utils.notion import get_notion_pages
from utils.token_manager import get_token
from utils.integration_health import check_integration_health, create_integration_checklist_items


class AutomationScheduler:
    """Scheduler for running automation agents in the background."""
    
    def __init__(self):
        """Initialize the scheduler."""
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
        atexit.register(lambda: self.scheduler.shutdown())
        print("Automation scheduler started")
    
    def schedule_agents(self):
        """Schedule all automation agents."""
        # Story extraction - run every 2 hours
        self.scheduler.add_job(
            func=self.run_story_extraction,
            trigger=IntervalTrigger(hours=2),
            id='story_extraction',
            name='Story Extraction Agent',
            replace_existing=True
        )
        
        # Noise clearing - run daily at 9 AM
        self.scheduler.add_job(
            func=self.run_noise_clearing,
            trigger=CronTrigger(hour=9, minute=0),
            id='noise_clearing',
            name='Noise Clearing Agent',
            replace_existing=True
        )
        
        # Release report generation - run weekly on Monday at 10 AM
        self.scheduler.add_job(
            func=self.run_release_report,
            trigger=CronTrigger(day_of_week='mon', hour=10, minute=0),
            id='release_report',
            name='Release Report Agent',
            replace_existing=True
        )
        
        # Stakeholder mapping - run every 4 hours
        self.scheduler.add_job(
            func=self.run_stakeholder_mapping,
            trigger=IntervalTrigger(hours=4),
            id='stakeholder_mapping',
            name='Stakeholder Mapping Agent',
            replace_existing=True
        )
        
        # Integration health check - run every hour
        self.scheduler.add_job(
            func=self.run_integration_health_check,
            trigger=IntervalTrigger(hours=1),
            id='integration_health_check',
            name='Integration Health Check',
            replace_existing=True
        )
        
        print("All agents scheduled")
    
    def run_story_extraction(self, user_id: str = "default"):
        """Run story extraction agent."""
        try:
            db = SessionLocal()
            try:
                agent = StoryExtractionAgent(db, user_id)
                
                # Get recent events and Notion pages
                notion_token = get_token(db, "notion")
                google_token = get_token(db, "google")
                
                notion_pages = None
                events = None
                
                if notion_token:
                    try:
                        # Fetch all pages with pagination (limit to recent ones for scheduled runs)
                        notion_pages = get_notion_pages(notion_token.access_token, page_size=100, max_pages=50, include_archived=False)
                    except Exception as e:
                        print(f"Error fetching Notion pages: {str(e)}")
                
                if google_token:
                    try:
                        from utils.google_calendar import get_upcoming_events
                        events, _ = get_upcoming_events(google_token.access_token, google_token.refresh_token, max_results=10)
                    except Exception as e:
                        print(f"Error fetching Google Calendar events: {str(e)}")
                        events = None
                
                result = agent.run(notion_pages=notion_pages, events=events)
                print(f"Story extraction completed: {result.get('count', 0)} stories extracted")
                
            finally:
                db.close()
        except Exception as e:
            print(f"Error running story extraction: {str(e)}")
    
    def run_noise_clearing(self, user_id: str = "default"):
        """Run noise clearing agent."""
        try:
            db = SessionLocal()
            try:
                agent = NoiseClearingAgent(db, user_id)
                result = agent.run()
                print(f"Noise clearing completed: Health score: {result.get('health_score', 0)}")
            finally:
                db.close()
        except Exception as e:
            print(f"Error running noise clearing: {str(e)}")
    
    def run_release_report(self, user_id: str = "default"):
        """Run release report agent."""
        try:
            db = SessionLocal()
            try:
                agent = ReleaseReportAgent(db, user_id)
                result = agent.run()
                print(f"Release report generated: {result.get('report_id', 'None')}")
            finally:
                db.close()
        except Exception as e:
            print(f"Error running release report: {str(e)}")
    
    def run_stakeholder_mapping(self, user_id: str = "default"):
        """Run stakeholder mapping agent."""
        try:
            db = SessionLocal()
            try:
                agent = StakeholderAgent(db, user_id)
                result = agent.run()
                print(f"Stakeholder mapping completed: {result.get('stakeholders_count', 0)} stakeholders")
            finally:
                db.close()
        except Exception as e:
            print(f"Error running stakeholder mapping: {str(e)}")
    
    def run_integration_health_check(self, user_id: str = "default"):
        """Run integration health check and create checklist items for issues."""
        try:
            db = SessionLocal()
            try:
                # Check integration health
                health = check_integration_health(user_id, db)
                
                # Create checklist items for any issues
                checklist_item_ids = create_integration_checklist_items(db, user_id)
                
                if checklist_item_ids:
                    print(f"Integration health check: {len(checklist_item_ids)} issue(s) found")
                else:
                    print("Integration health check: All integrations healthy")
            finally:
                db.close()
        except Exception as e:
            print(f"Error running integration health check: {str(e)}")
    
    def shutdown(self):
        """Shutdown the scheduler."""
        self.scheduler.shutdown()
        print("Automation scheduler shut down")


# Global scheduler instance
_scheduler = None


def get_scheduler() -> AutomationScheduler:
    """Get or create the global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = AutomationScheduler()
        _scheduler.schedule_agents()
    return _scheduler

