"""Utility functions for Gemini API."""
import google.generativeai as genai
import json
import re
from typing import List, Dict
from config import settings


def initialize_gemini():
    """Initialize Gemini API client."""
    genai.configure(api_key=settings.gemini_api_key)


def generate_break_suggestions(events: List[Dict], notion_pages: List[Dict]) -> List[Dict]:
    """Generate break suggestions using Gemini based on calendar events and Notion pages."""
    try:
        initialize_gemini()
        # Use gemini-1.5-flash which is faster and more cost-effective
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Prepare context with detailed event information
        from datetime import datetime
        
        # Sort events by start time
        sorted_events = sorted(events, key=lambda x: x.get('start', ''))[:10]
        
        events_summary = "\n".join([
            f"- {event.get('summary', 'No Title')} from {event.get('start', '')} to {event.get('end', '')} (Location: {event.get('location', 'N/A')}, Attendees: {event.get('attendees', 0)})"
            for event in sorted_events
        ])
        
        # Calculate gaps between events for better break suggestions
        current_time = datetime.utcnow().isoformat() + 'Z'
        gaps = []
        
        def parse_datetime(date_str):
            """Parse datetime string handling various timezone formats."""
            if not date_str:
                return None
            try:
                from dateutil import parser as date_parser
                # Use dateutil parser which handles all ISO 8601 formats including timezones
                dt = date_parser.isoparse(date_str)
                # Convert to UTC and make timezone-naive for comparison
                if dt.tzinfo:
                    dt = dt.astimezone(datetime.timezone.utc).replace(tzinfo=None)
                return dt
            except ImportError:
                # Fallback to manual parsing if dateutil is not available
                try:
                    # Handle ISO format with Z
                    if date_str.endswith('Z'):
                        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    elif '+' in date_str[-6:]:  # Has timezone like +05:30
                        dt = datetime.fromisoformat(date_str)
                    elif date_str.count('-') >= 3 and 'T' in date_str:  # Has timezone like -06:00
                        # Find where timezone starts (last occurrence of - or + before the end)
                        dt = datetime.fromisoformat(date_str)
                    else:
                        # No timezone, assume UTC
                        dt = datetime.fromisoformat(date_str.replace('T', ' ').split('.')[0])
                    # Convert to UTC and make timezone-naive
                    if dt.tzinfo:
                        dt = dt.astimezone(datetime.timezone.utc).replace(tzinfo=None)
                    return dt
                except Exception as e:
                    print(f"Error parsing datetime {date_str}: {e}")
                    return None
            except Exception as e:
                print(f"Error parsing datetime {date_str}: {e}")
                return None
        
        if sorted_events:
            # Check gap before first event
            first_event_start = sorted_events[0].get('start', '')
            if first_event_start:
                first_start = parse_datetime(first_event_start)
                if first_start:
                    now = datetime.utcnow()
                    if first_start > now:
                        gap_minutes = (first_start - now).total_seconds() / 60
                        if gap_minutes > 15:  # Only suggest breaks for gaps > 15 minutes
                            gaps.append(f"Gap before first meeting: {gap_minutes:.0f} minutes")
            
            # Check gaps between consecutive events
            for i in range(len(sorted_events) - 1):
                event1_end = sorted_events[i].get('end', '')
                event2_start = sorted_events[i + 1].get('start', '')
                if event1_end and event2_start:
                    end1 = parse_datetime(event1_end)
                    start2 = parse_datetime(event2_start)
                    if end1 and start2:
                        gap_minutes = (start2 - end1).total_seconds() / 60
                        if gap_minutes > 15:  # Only suggest breaks for gaps > 15 minutes
                            gaps.append(f"Gap between '{sorted_events[i].get('summary', 'Event 1')}' and '{sorted_events[i+1].get('summary', 'Event 2')}': {gap_minutes:.0f} minutes")
        
        gaps_summary = "\n".join(gaps) if gaps else "No significant gaps found between events"
        
        pages_summary = "\n".join([
            f"- {page['title']} (last edited: {page['last_edited_time']})"
            for page in notion_pages[:5]  # Limit to first 5 pages
        ])
        
        prompt = f"""You are a wellness assistant helping to schedule breaks between calendar events. Analyze the following calendar schedule and suggest optimal break times.

Current Time: {current_time}

Calendar Events (sorted by time):
{events_summary if events_summary else "No upcoming events"}

Identified Gaps:
{gaps_summary}

Notion Pages (recent work):
{pages_summary if pages_summary else "No recent pages"}

Based on this schedule, suggest 3-5 break times that:
1. Fit naturally into gaps between meetings
2. Are at least 15 minutes after the current time
3. Don't overlap with any scheduled events
4. Consider the intensity of the schedule (back-to-back meetings need longer breaks)

For each break suggestion, provide:
- time: ISO 8601 format (e.g., "2025-11-09T14:30:00Z")
- duration: minutes (5-20, typically 10-15 for gaps between meetings)
- activity: one of ["meditation", "walk", "breathing", "stretch", "rest", "hydrate"]
- reason: brief explanation based on the schedule context

Format your response as a JSON array with objects containing: time, duration, activity, reason.
Example format:
[
  {{"time": "2025-11-09T14:30:00Z", "duration": 15, "activity": "meditation", "reason": "15-minute gap between back-to-back meetings"}},
  {{"time": "2025-11-09T16:00:00Z", "duration": 10, "activity": "walk", "reason": "After intensive meeting session"}}
]

Only return valid JSON, no additional text or markdown formatting."""
        
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        # Try to extract JSON from response
        # Remove markdown code blocks if present
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        # Parse JSON
        try:
            suggestions = json.loads(response_text)
        except json.JSONDecodeError:
            # Try to find JSON array in the response
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if json_match:
                suggestions = json.loads(json_match.group())
            else:
                raise ValueError("Could not parse JSON from Gemini response")
        
        # Validate and format suggestions
        formatted_suggestions = []
        if not isinstance(suggestions, list):
            suggestions = [suggestions] if isinstance(suggestions, dict) else []
        
        for suggestion in suggestions:
            if isinstance(suggestion, dict) and all(key in suggestion for key in ["time", "duration", "activity", "reason"]):
                formatted_suggestions.append({
                    "time": suggestion["time"],
                    "duration": suggestion["duration"],
                    "activity": suggestion["activity"],
                    "reason": suggestion["reason"]
                })
        
        return formatted_suggestions if formatted_suggestions else []
    except Exception as e:
        print(f"Error generating break suggestions with Gemini: {str(e)}")
        # Return empty list if Gemini fails - let the frontend handle empty suggestions
        return []

