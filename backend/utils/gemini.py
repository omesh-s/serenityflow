"""Utility functions for Gemini API."""
import google.generativeai as genai
import json
import re
from typing import List, Dict
from datetime import datetime, timezone, timedelta
from dateutil import tz as dateutil_tz
from config import settings


def initialize_gemini():
    """Initialize Gemini API client."""
    genai.configure(api_key=settings.gemini_api_key)


def generate_break_suggestions(events: List[Dict], notion_pages: List[Dict], user_timezone: str = 'UTC') -> List[Dict]:
    """Generate break suggestions using Gemini based on calendar events and Notion pages."""
    try:
        initialize_gemini()
        # Use gemini-2.5-flash-lite which is faster and more cost-effective
        model = genai.GenerativeModel('gemini-2.5-flash-lite')
        
        # Get current time in UTC (timezone-aware)
        current_time_utc = datetime.now(timezone.utc)
        current_time = current_time_utc.isoformat()
        gaps = []
        
        def parse_datetime(date_str):
            """Parse datetime string handling various timezone formats.
            Returns timezone-aware datetime in UTC.
            """
            if not date_str:
                return None
            try:
                from dateutil import parser as date_parser
                # Use dateutil parser which handles all ISO 8601 formats including timezones
                dt = date_parser.isoparse(date_str)
                # Ensure timezone-aware, convert to UTC
                if dt.tzinfo is None:
                    # If no timezone info, assume UTC
                    dt = dt.replace(tzinfo=timezone.utc)
                else:
                    # Convert to UTC
                    dt = dt.astimezone(timezone.utc)
                return dt
            except Exception as e:
                # Fallback to manual parsing
                try:
                    # Handle ISO format with Z (UTC)
                    if date_str.endswith('Z'):
                        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                        return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
                    
                    # Handle timezone offset like -06:00 or +05:30
                    if '+' in date_str or (date_str.count('-') > 2 and 'T' in date_str):
                        # Try to parse with timezone
                        try:
                            dt = datetime.fromisoformat(date_str)
                            if dt.tzinfo is None:
                                dt = dt.replace(tzinfo=timezone.utc)
                            else:
                                dt = dt.astimezone(timezone.utc)
                            return dt
                        except:
                            pass
                    
                    # Try parsing as naive datetime and assume UTC
                    # Remove timezone suffix if present for parsing
                    clean_str = date_str
                    if '+' in date_str[-6:]:
                        clean_str = date_str.rsplit('+', 1)[0]
                    elif date_str.count('-') > 2 and date_str[-6] in ['-', '+']:
                        # Might have timezone offset at the end
                        try:
                            dt = datetime.fromisoformat(date_str)
                            if dt.tzinfo:
                                dt = dt.astimezone(timezone.utc)
                            else:
                                dt = dt.replace(tzinfo=timezone.utc)
                            return dt
                        except:
                            pass
                    
                    # Parse as naive and assume UTC
                    if 'T' in clean_str:
                        dt = datetime.fromisoformat(clean_str.split('.')[0])
                    else:
                        dt = datetime.fromisoformat(clean_str.replace(' ', 'T').split('.')[0])
                    
                    # Assume UTC if no timezone
                    return dt.replace(tzinfo=timezone.utc)
                except Exception:
                    # Last resort: return None
                    return None
        
        # Parse all event times and filter to future events only
        parsed_events = []
        for event in events:
            start_str = event.get('start', '')
            end_str = event.get('end', '')
            if start_str and end_str:
                start_dt = parse_datetime(start_str)
                end_dt = parse_datetime(end_str)
                if start_dt and end_dt:
                    # Only include events that haven't ended yet
                    if end_dt > current_time_utc:
                        parsed_events.append({
                            **event,
                            'start_dt': start_dt,
                            'end_dt': end_dt,
                            'start_iso': start_dt.isoformat(),
                            'end_iso': end_dt.isoformat(),
                        })
        
        # Sort parsed events by start time
        parsed_events.sort(key=lambda x: x['start_dt'])
        
        # SIMPLE APPROACH: Generate a break after EACH meeting automatically
        automatic_breaks = []
        if parsed_events:
            for i in range(len(parsed_events)):
                event = parsed_events[i]
                event_end = event['end_dt']
                
                # Check if there's a next meeting
                if i < len(parsed_events) - 1:
                    next_event_start = parsed_events[i + 1]['start_dt']
                    gap_minutes = (next_event_start - event_end).total_seconds() / 60
                    
                    # If gap is >= 10 minutes, add a break
                    if gap_minutes >= 10:
                        # Break starts 2 minutes after meeting ends
                        break_start = event_end + timedelta(minutes=2)
                        
                        # Determine break strategy based on gap size
                        if gap_minutes >= 45:
                            # Very large gap (45+ min): Add two breaks strategically
                            # First break: 15-20 minutes right after meeting
                            first_break_duration = min(20, max(12, int(gap_minutes * 0.25)))
                            first_break_end = break_start + timedelta(minutes=first_break_duration)
                            
                            # Calculate remaining gap
                            remaining_gap = (next_event_start - first_break_end).total_seconds() / 60
                            
                            if remaining_gap >= 20:
                                # Add first break
                                first_break_time_iso = break_start.isoformat()
                                if not first_break_time_iso.endswith('Z'):
                                    first_break_time_iso = first_break_time_iso.replace('+00:00', 'Z').replace('-00:00', 'Z')
                                automatic_breaks.append({
                                    'time': first_break_time_iso,
                                    'duration': first_break_duration,
                                    'activity': 'meditation',  # Will be customized by Gemini
                                    'reason': f"After '{event.get('summary', 'Meeting')}' ends",
                                })
                                
                                # Add second break in the middle or before next meeting
                                # Place it about 15 minutes before the next meeting starts
                                second_break_duration = min(15, max(10, int(remaining_gap * 0.4)))
                                second_break_start = next_event_start - timedelta(minutes=second_break_duration + 2)
                                
                                # Ensure second break doesn't overlap with first
                                if second_break_start > first_break_end + timedelta(minutes=5):
                                    second_break_time_iso = second_break_start.isoformat()
                                    if not second_break_time_iso.endswith('Z'):
                                        second_break_time_iso = second_break_time_iso.replace('+00:00', 'Z').replace('-00:00', 'Z')
                                    automatic_breaks.append({
                                        'time': second_break_time_iso,
                                        'duration': second_break_duration,
                                        'activity': 'stretch',  # Will be customized by Gemini
                                        'reason': f"Before '{parsed_events[i + 1].get('summary', 'Meeting')}' starts",
                                    })
                            else:
                                # Not enough space for two breaks, add one longer break
                                break_duration = min(20, max(10, int(gap_minutes * 0.4)))
                                break_end = break_start + timedelta(minutes=break_duration)
                                if break_end <= (next_event_start - timedelta(minutes=2)):
                                    break_time_iso = break_start.isoformat()
                                    if not break_time_iso.endswith('Z'):
                                        break_time_iso = break_time_iso.replace('+00:00', 'Z').replace('-00:00', 'Z')
                                    automatic_breaks.append({
                                        'time': break_time_iso,
                                        'duration': break_duration,
                                        'activity': 'meditation',
                                        'reason': f"After '{event.get('summary', 'Meeting')}' ends",
                                    })
                        elif gap_minutes >= 30:
                            # Large gap (30-45 min): Add one break, check for second if space allows
                            break_duration = min(15, max(10, int(gap_minutes * 0.35)))
                            break_end = break_start + timedelta(minutes=break_duration)
                            
                            if break_end <= (next_event_start - timedelta(minutes=2)):
                                break_time_iso = break_start.isoformat()
                                if not break_time_iso.endswith('Z'):
                                    break_time_iso = break_time_iso.replace('+00:00', 'Z').replace('-00:00', 'Z')
                                automatic_breaks.append({
                                    'time': break_time_iso,
                                    'duration': break_duration,
                                    'activity': 'meditation',
                                    'reason': f"After '{event.get('summary', 'Meeting')}' ends",
                                })
                                
                                # Check if we can add a second break (need at least 17 min remaining)
                                remaining_gap = (next_event_start - break_end).total_seconds() / 60
                                if remaining_gap >= 17:
                                    # Add second break before next meeting
                                    second_break_duration = min(12, max(8, int(remaining_gap * 0.45)))
                                    second_break_start = next_event_start - timedelta(minutes=second_break_duration + 2)
                                    second_break_end = second_break_start + timedelta(minutes=second_break_duration)
                                    
                                    # Ensure second break doesn't overlap with first
                                    if second_break_start > break_end + timedelta(minutes=3) and second_break_end <= (next_event_start - timedelta(minutes=2)):
                                        second_break_time_iso = second_break_start.isoformat()
                                        if not second_break_time_iso.endswith('Z'):
                                            second_break_time_iso = second_break_time_iso.replace('+00:00', 'Z').replace('-00:00', 'Z')
                                        automatic_breaks.append({
                                            'time': second_break_time_iso,
                                            'duration': second_break_duration,
                                            'activity': 'stretch',
                                            'reason': f"Before '{parsed_events[i + 1].get('summary', 'Meeting')}' starts",
                                        })
                        else:
                            # Small-medium gap (10-30 min): Add one break
                            break_duration = min(15, max(5, int(gap_minutes * 0.4)))
                            break_end = break_start + timedelta(minutes=break_duration)
                            
                            if break_end <= (next_event_start - timedelta(minutes=2)):
                                break_time_iso = break_start.isoformat()
                                if not break_time_iso.endswith('Z'):
                                    break_time_iso = break_time_iso.replace('+00:00', 'Z').replace('-00:00', 'Z')
                                automatic_breaks.append({
                                    'time': break_time_iso,
                                    'duration': break_duration,
                                    'activity': 'meditation',
                                    'reason': f"After '{event.get('summary', 'Meeting')}' ends",
                                })
        
        # Format events for prompt
        events_summary = "\n".join([
            f"- {event.get('summary', 'No Title')} from {event['start_dt'].strftime('%Y-%m-%d %H:%M UTC')} to {event['end_dt'].strftime('%H:%M UTC')} (Duration: {int((event['end_dt'] - event['start_dt']).total_seconds() / 60)} min)"
            for event in parsed_events
        ]) if parsed_events else "No upcoming events"
        
        # Format gaps for context
        gaps_info = []
        if len(parsed_events) > 1:
            for i in range(len(parsed_events) - 1):
                event1 = parsed_events[i]
                event2 = parsed_events[i + 1]
                gap_minutes = (event2['start_dt'] - event1['end_dt']).total_seconds() / 60
                if gap_minutes >= 10:
                    gaps_info.append(f"Gap after '{event1.get('summary', 'Meeting')}': {gap_minutes:.0f} minutes until '{event2.get('summary', 'Meeting')}'")
        
        gaps_summary = "\n".join(gaps_info) if gaps_info else "No gaps between meetings"
        
        pages_summary = "\n".join([
            f"- {page['title']} (last edited: {page['last_edited_time']})"
            for page in notion_pages[:5]  # Limit to first 5 pages
        ])
        
        # Analyze schedule density and intensity
        schedule_analysis = ""
        if parsed_events:
            back_to_back_count = 0
            long_meetings = 0
            total_duration = 0
            for i, event in enumerate(parsed_events):
                duration_minutes = (event['end_dt'] - event['start_dt']).total_seconds() / 60
                total_duration += duration_minutes
                if duration_minutes > 60:
                    long_meetings += 1
                
                # Check for back-to-back meetings
                if i < len(parsed_events) - 1:
                    gap = (parsed_events[i + 1]['start_dt'] - event['end_dt']).total_seconds() / 60
                    if gap < 15:
                        back_to_back_count += 1
            
            schedule_analysis = f"""
Schedule Analysis:
- Total upcoming events: {len(parsed_events)}
- Back-to-back meetings (<15 min gap): {back_to_back_count}
- Long meetings (>60 min): {long_meetings}
- Total meeting time: {total_duration:.0f} minutes
- Schedule intensity: {'High' if back_to_back_count > 2 or total_duration > 240 else 'Moderate' if back_to_back_count > 0 else 'Low'}
"""

        # If we have automatic breaks, customize them with Gemini based on sentiment
        if automatic_breaks and parsed_events:
            # Prepare sentiment/wellness context from Notion pages
            wellness_context = ""
            if pages:
                # Extract key information from pages for context
                recent_pages = pages[:5]
                page_summaries = [page.get('title', 'Untitled') for page in recent_pages]
                wellness_context = f"Recent work: {', '.join(page_summaries)}"
            
            # Create break list for prompt
            break_list = "\n".join([
                f"- Break {i+1}: {break_info['duration']} min at {break_info['time']} (after meeting ending around that time)"
                for i, break_info in enumerate(automatic_breaks)
            ])
            
            prompt = f"""You are optimizing break types for a schedule. Breaks are already placed after each meeting. Your job is to customize the break TYPE and DURATION based on meeting context and user wellness.

Current Time: {current_time}

Calendar Events:
{events_summary}

Automatic Breaks (already placed after each meeting):
{break_list}

{wellness_context}

Your task: For each automatic break above, suggest the BEST break type and duration based on:
1. Meeting length and intensity
2. Gap size between meetings  
3. User's recent work/wellness context
4. Whether meetings are back-to-back

AVAILABLE BREAK TYPES:
- "meditation": Stress relief, mental clarity (5-30 min)
- "walk": Physical movement, refreshment (5-30 min)
- "breathing": Quick stress relief (3-15 min)
- "stretch": Physical tension release (5-20 min)
- "rest": Quiet recovery (10-30 min)
- "hydrate": Quick refreshment (3-10 min)
- "power_nap": Energy recovery (10-30 min)
- "eye_rest": Screen fatigue relief (3-10 min)

Return a JSON array with one object per break, matching the order of automatic breaks. Use the EXACT time from the automatic break:
[
  {{"time": "{automatic_breaks[0]['time'] if automatic_breaks else ''}", "duration": <optimized duration>, "activity": "<break type>", "reason": "<brief reason>"}},
  ...
]

Keep the same time for each break. Only optimize activity type and duration."""
            
            try:
                response = model.generate_content(prompt)
            except Exception as gemini_error:
                print(f"Gemini API error (using automatic breaks): {str(gemini_error)}")
                # Fall back to automatic breaks
                return automatic_breaks
        else:
            # No events or breaks, return automatic breaks if we have them
            return automatic_breaks if automatic_breaks else []
        
        # Extract JSON from response
        try:
            response_text = response.text.strip()
            
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
                    print("Could not parse JSON from Gemini, using automatic breaks")
                    suggestions = []
        except Exception as parse_error:
            print(f"Error parsing Gemini response: {str(parse_error)}")
            suggestions = []
        
        # Try to customize breaks with Gemini, but fall back to automatic breaks if it fails
        customized_breaks = []
        
        try:
            if not isinstance(suggestions, list):
                suggestions = [suggestions] if isinstance(suggestions, dict) else []
            
            # Match Gemini suggestions to automatic breaks by time
            for auto_break in automatic_breaks:
                auto_time = parse_datetime(auto_break['time'])
                if not auto_time:
                    continue
                
                # Find matching Gemini suggestion
                matched = False
                for gemini_suggestion in suggestions:
                    if isinstance(gemini_suggestion, dict) and 'time' in gemini_suggestion:
                        gemini_time = parse_datetime(gemini_suggestion['time'])
                        if gemini_time and abs((gemini_time - auto_time).total_seconds()) < 300:  # Within 5 minutes
                            # Use Gemini's customization
                            customized_breaks.append({
                                "time": auto_break['time'],  # Use auto break time (more reliable)
                                "duration": gemini_suggestion.get("duration", auto_break['duration']),
                                "activity": gemini_suggestion.get("activity", auto_break['activity']),
                                "reason": gemini_suggestion.get("reason", auto_break['reason'])
                            })
                            matched = True
                            break
                
                # If no match, use automatic break
                if not matched:
                    customized_breaks.append(auto_break)
        
        except Exception as e:
            print(f"Error processing Gemini suggestions, using automatic breaks: {str(e)}")
            # Fall back to automatic breaks
            customized_breaks = automatic_breaks
        
        # Final validation: ensure breaks don't overlap with meetings and are in the future
        final_breaks = []
        for break_item in customized_breaks:
            break_time = parse_datetime(break_item['time'])
            if not break_time:
                continue
            
            # Ensure timezone-aware
            if break_time.tzinfo is None:
                break_time = break_time.replace(tzinfo=timezone.utc)
            else:
                break_time = break_time.astimezone(timezone.utc)
            
            # Must be in the future
            if break_time <= current_time_utc:
                continue
            
            # Check it doesn't overlap with any meeting
            overlaps = False
            break_duration = break_item.get('duration', 10)
            break_end = break_time + timedelta(minutes=break_duration)
            
            for event in parsed_events:
                event_start = event['start_dt']
                event_end = event['end_dt']
                # Check if break overlaps with meeting (with 1-minute buffer)
                if (break_time < event_end + timedelta(minutes=1) and break_end > event_start - timedelta(minutes=1)):
                    overlaps = True
                    break
            
            if not overlaps:
                time_iso = break_time.isoformat().replace('+00:00', 'Z')
                final_breaks.append({
                    "time": time_iso,
                    "duration": break_item.get('duration', 10),
                    "activity": break_item.get('activity', 'meditation'),
                    "reason": break_item.get('reason', 'Break after meeting')
                })
        
        # Sort breaks by time
        final_breaks.sort(key=lambda x: parse_datetime(x["time"]) or datetime.min.replace(tzinfo=timezone.utc))
        
        # Remove duplicates (same time within 1 minute)
        if len(final_breaks) > 1:
            unique_breaks = [final_breaks[0]]
            for break_item in final_breaks[1:]:
                prev_time = parse_datetime(unique_breaks[-1]["time"])
                curr_time = parse_datetime(break_item["time"])
                if prev_time and curr_time:
                    time_diff = abs((curr_time - prev_time).total_seconds())
                    if time_diff > 60:  # More than 1 minute apart
                        unique_breaks.append(break_item)
            final_breaks = unique_breaks
        
        return final_breaks
    except Exception as e:
        print(f"Error generating break suggestions with Gemini: {str(e)}")
        import traceback
        traceback.print_exc()
        # Try to return automatic breaks if they were created
        try:
            if 'automatic_breaks' in locals() and automatic_breaks:
                return automatic_breaks
        except:
            pass
        return []

