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


def select_break_type_by_duration(duration_minutes: int, gap_minutes: int, meeting_index: int = 0, time_of_day: str = '') -> str:
    """Select break type based on available duration, gap size, meeting context, and variety.
    
    Uses a deterministic pattern based on meeting index to ensure variety while maintaining
    stability (same meetings always get same break types).
    
    Args:
        duration_minutes: Duration of the break
        gap_minutes: Total gap size between meetings
        meeting_index: Index of the meeting (for variety - alternate break types)
        time_of_day: Time of day ('morning', 'afternoon', 'evening') for context-aware selection
    
    Returns:
        Break type string: 'hydrate', 'breathing', 'stretch', 'walk', etc.
    """
    # Determine time of day if not provided
    if not time_of_day:
        from datetime import datetime
        current_hour = datetime.now().hour
        if current_hour < 12:
            time_of_day = 'morning'
        elif current_hour < 17:
            time_of_day = 'afternoon'
        else:
            time_of_day = 'evening'
    
    # Create variety patterns for different duration ranges
    # These patterns cycle to ensure different break types throughout the day
    # Pattern is deterministic based on meeting index
    
    # For very short breaks (3-7 min): prioritize quick breaks
    if duration_minutes <= 7:
        quick_options = ['hydrate', 'breathing', 'eye_rest', 'hydrate', 'breathing']
        return quick_options[meeting_index % len(quick_options)]
    
    # For short breaks (8-12 min): breathing, hydrate, eye_rest, walk
    elif duration_minutes <= 12:
        short_options = ['breathing', 'walk', 'hydrate', 'eye_rest', 'breathing', 'walk']
        return short_options[meeting_index % len(short_options)]
    
    # For medium breaks (13-20 min): stretch, walk, breathing, eye_rest
    elif duration_minutes <= 20:
        # Most common case - provide good variety
        medium_options = ['stretch', 'walk', 'breathing', 'stretch', 'walk', 'eye_rest', 'breathing', 'stretch']
        return medium_options[meeting_index % len(medium_options)]
    
    # For longer breaks (21+ min): walk, stretch, rest
    else:
        long_options = ['walk', 'stretch', 'rest', 'walk', 'stretch']
        return long_options[meeting_index % len(long_options)]


def match_pages_to_events(events: List[Dict], notion_pages: List[Dict]) -> Dict[str, List[Dict]]:
    """Match Notion pages to calendar events based on timing and title similarity.
    
    Args:
        events: List of calendar events with start_dt and end_dt
        notion_pages: List of Notion pages
    
    Returns:
        Dictionary mapping event IDs to list of matching Notion pages
    """
    event_pages_map = {}
    
    for event in events:
        event_id = event.get('id', '')
        event_title = event.get('summary', '').lower()
        event_start = event.get('start_dt')
        event_end = event.get('end_dt')
        
        if not event_start or not event_end:
            continue
        
        matching_pages = []
        
        for page in notion_pages:
            page_title = page.get('title', '').lower()
            page_created = page.get('created_time', '')
            page_edited = page.get('last_edited_time', '')
            
            # Try to parse page timestamps
            try:
                from dateutil import parser as date_parser
                if page_edited:
                    page_time = date_parser.isoparse(page_edited)
                elif page_created:
                    page_time = date_parser.isoparse(page_created)
                else:
                    continue
                
                # Ensure page_time is timezone-aware and convert to UTC
                if page_time.tzinfo is None:
                    page_time = page_time.replace(tzinfo=timezone.utc)
                else:
                    page_time = page_time.astimezone(timezone.utc)
                
                # Ensure event times are in UTC (they should already be from parse_datetime)
                event_start_utc = event_start
                event_end_utc = event_end
                if event_start_utc.tzinfo is None:
                    event_start_utc = event_start_utc.replace(tzinfo=timezone.utc)
                else:
                    event_start_utc = event_start_utc.astimezone(timezone.utc)
                if event_end_utc.tzinfo is None:
                    event_end_utc = event_end_utc.replace(tzinfo=timezone.utc)
                else:
                    event_end_utc = event_end_utc.astimezone(timezone.utc)
                
                # Check if page was created/edited within 2 hours after meeting ended
                # or within 30 minutes before meeting started (for pre-meeting notes)
                time_diff_after = (page_time - event_end_utc).total_seconds() / 3600  # hours
                time_diff_before = (event_start_utc - page_time).total_seconds() / 3600  # hours
                
                # Match if:
                # 1. Page created/edited within 2 hours after meeting (meeting notes)
                # 2. Page created/edited within 30 min before meeting (pre-meeting notes)
                # 3. Title similarity (fuzzy match)
                title_match = False
                if event_title and page_title:
                    # Simple title matching: check if key words match
                    event_words = set(event_title.split())
                    page_words = set(page_title.split())
                    # Remove common words
                    common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with'}
                    event_words -= common_words
                    page_words -= common_words
                    if event_words and page_words:
                        # If 30% of words match, consider it a match
                        overlap = len(event_words & page_words) / max(len(event_words), len(page_words))
                        title_match = overlap > 0.3
                
                if (0 <= time_diff_after <= 2) or (0 <= time_diff_before <= 0.5) or title_match:
                    matching_pages.append(page)
            
            except Exception:
                # If we can't parse the time, skip this page
                continue
        
        if matching_pages:
            event_pages_map[event_id] = matching_pages
    
    return event_pages_map


def should_add_meditation_after_meeting(event: Dict, matching_pages: List[Dict], model) -> bool:
    """Use LLM to determine if meditation break is needed after a meeting based on meeting notes.
    
    Args:
        event: Calendar event
        matching_pages: List of Notion pages associated with this meeting
        model: Gemini model instance
    
    Returns:
        True if meditation break is recommended, False otherwise
    """
    if not matching_pages:
        return False
    
    try:
        # Extract content from matching pages using wellness analyzer's extraction method
        from utils.wellness_analyzer import extract_note_content
        page_contents = []
        for page in matching_pages[:3]:  # Limit to 3 most recent pages
            title = page.get('title', '')
            # Use wellness analyzer's content extraction method
            content_text = extract_note_content(page)
            # If extraction returned minimal content, try raw_data as fallback
            if len(content_text) < 20 and 'raw_data' in page:
                raw_data = page.get('raw_data', {})
                props = raw_data.get('properties', {})
                for prop_name, prop_data in props.items():
                    if prop_data.get('type') == 'rich_text' and prop_data.get('rich_text'):
                        content_text += ' ' + ' '.join([rt.get('plain_text', '') for rt in prop_data['rich_text']])
            
            # Combine title and content
            full_content = f"{title} {content_text}".strip()
            page_contents.append(f"Page: {title}\nContent: {full_content[:800]}")  # Limit content length
        
        pages_text = "\n\n".join(page_contents)
        meeting_title = event.get('summary', 'Meeting')
        meeting_duration = int((event.get('end_dt') - event.get('start_dt')).total_seconds() / 60)
        
        prompt = f"""Analyze the following meeting and its notes to determine if a meditation break is recommended after this meeting.

Meeting: {meeting_title}
Duration: {meeting_duration} minutes

Meeting Notes:
{pages_text}

Consider the following factors:
1. Was the meeting stressful, intense, or emotionally draining?
2. Were there conflicts, difficult decisions, or challenging topics discussed?
3. Does the meeting notes indicate high stress, tension, or need for mental recovery?
4. Was it a long or back-to-back meeting that would benefit from mindfulness?

Respond with ONLY "yes" or "no" - no other text."""
        
        response = model.generate_content(prompt)
        response_text = response.text.strip().lower()
        
        return 'yes' in response_text or 'true' in response_text
        
    except Exception as e:
        print(f"Error determining meditation need: {str(e)}")
        # Default to False if LLM fails
        return False


def generate_break_suggestions(events: List[Dict], notion_pages: List[Dict], user_timezone: str = 'UTC') -> List[Dict]:
    """Generate break suggestions using Gemini based on calendar events and Notion pages."""
    try:
        # Use cache to ensure breaks are stable and don't change on refresh
        from utils.break_cache import get_cached_breaks, set_cached_breaks, get_events_fingerprint
        
        # Generate cache key and events fingerprint
        # Use a simple cache key - breaks should be stable based on events only
        cache_key = "breaks_default"  # Single cache key for all users (can be made user-specific later)
        events_fingerprint = get_events_fingerprint(events)
        
        # Check cache first - this is critical for preventing randomization
        is_cached, cached_breaks = get_cached_breaks(cache_key, events_fingerprint)
        if is_cached and cached_breaks:
            print(f"Using cached breaks (fingerprint: {events_fingerprint[:8]}...) - {len(cached_breaks)} breaks")
            return cached_breaks
        else:
            print(f"Cache miss - generating new breaks (fingerprint: {events_fingerprint[:8]}...)")
        
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
        # IMPORTANT: Sort events FIRST by start time to ensure consistent break generation
        # This prevents breaks from changing when events come in different orders
        events_sorted = sorted(events, key=lambda e: (e.get('start', ''), e.get('id', '')))
        
        parsed_events = []
        for event in events_sorted:
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
        
        # Sort parsed events by start time (redundant but ensures consistency)
        parsed_events.sort(key=lambda x: (x['start_dt'], x.get('id', '')))
        
        # Match Notion pages to events
        event_pages_map = match_pages_to_events(parsed_events, notion_pages)
        
        # Generate breaks after meetings - NO automatic meditation breaks
        # Only add meditation if LLM determines it's needed based on meeting notes
        # CRITICAL: Only create ONE break per gap between meetings
        automatic_breaks = []
        processed_gaps = set()  # Track which gaps we've already processed
        
        if parsed_events:
            for i in range(len(parsed_events)):
                event = parsed_events[i]
                event_end = event['end_dt']
                event_id = event.get('id', '') or event.get('summary', 'Unknown')
                
                # Check if there's a next meeting
                if i < len(parsed_events) - 1:
                    next_event = parsed_events[i + 1]
                    next_event_start = next_event['start_dt']
                    next_event_id = next_event.get('id', '') or next_event.get('summary', 'Unknown')
                    gap_minutes = (next_event_start - event_end).total_seconds() / 60
                    
                    # Create a unique gap identifier
                    gap_id = (event_id, next_event_id)
                    
                    # Skip if we've already processed this gap
                    if gap_id in processed_gaps:
                        print(f"Skipping gap {gap_id} - already processed")
                        continue
                    
                    # If gap is >= 10 minutes, add ONE break
                    if gap_minutes >= 10:
                        # Break starts 2 minutes after meeting ends
                        break_start = event_end + timedelta(minutes=2)
                        
                        # Determine time of day for context-aware break selection
                        break_hour = break_start.hour
                        if break_hour < 12:
                            time_of_day = 'morning'
                        elif break_hour < 17:
                            time_of_day = 'afternoon'
                        else:
                            time_of_day = 'evening'
                        
                        # Check if we should add meditation break based on meeting notes
                        matching_pages = event_pages_map.get(event.get('id', ''), [])
                        needs_meditation = False
                        if matching_pages:
                            try:
                                needs_meditation = should_add_meditation_after_meeting(event, matching_pages, model)
                            except Exception as e:
                                print(f"Error checking meditation need for event {event_id}: {str(e)}")
                                needs_meditation = False
                        
                        # Calculate break duration based on gap size
                        # Leave at least 2 minutes buffer before next meeting
                        # Use 30-40% of available gap for break, with reasonable limits
                        if gap_minutes >= 60:
                            # Very large gap: up to 20 minutes
                            break_duration = min(20, max(10, int(gap_minutes * 0.3)))
                        elif gap_minutes >= 30:
                            # Large gap: 10-15 minutes
                            break_duration = min(15, max(10, int(gap_minutes * 0.35)))
                        else:
                            # Small-medium gap: 5-12 minutes
                            break_duration = min(12, max(5, int(gap_minutes * 0.4)))
                        
                        # Ensure break doesn't overlap with next meeting (2 min buffer)
                        break_end = break_start + timedelta(minutes=break_duration)
                        if break_end <= (next_event_start - timedelta(minutes=2)):
                            break_time_iso = break_start.isoformat()
                            if not break_time_iso.endswith('Z'):
                                break_time_iso = break_time_iso.replace('+00:00', 'Z').replace('-00:00', 'Z')
                            
                            # Use meditation if LLM determined it's needed, otherwise use varied break selection
                            # Pass meeting index (i) for variety - this ensures different break types
                            if needs_meditation:
                                break_activity = 'meditation'
                            else:
                                break_activity = select_break_type_by_duration(
                                    break_duration, 
                                    gap_minutes, 
                                    meeting_index=i,  # Use meeting index for variety
                                    time_of_day=time_of_day
                                )
                            
                            # Mark this gap as processed
                            processed_gaps.add(gap_id)
                            
                            # Generate stable break ID here for consistency
                            import hashlib
                            time_rounded = break_start.replace(second=0, microsecond=0).isoformat().replace('+00:00', 'Z')
                            stable_id_string = f"{gap_id[0]}_{gap_id[1]}_{time_rounded}"
                            stable_break_id = hashlib.md5(stable_id_string.encode()).hexdigest()[:8]
                            
                            automatic_breaks.append({
                                'id': stable_break_id,  # Include ID in automatic breaks for stability
                                'time': break_time_iso,
                                'duration': break_duration,
                                'activity': break_activity,
                                'reason': f"After '{event.get('summary', 'Meeting')}' ends",
                                '_gap_id': gap_id,  # Store gap ID for debugging
                            })
                            print(f"Created break {stable_break_id} for gap {gap_id}: {break_activity} at {break_time_iso} ({break_duration} min)")
                        else:
                            print(f"Gap {gap_id} too small for break: {gap_minutes} min (break would be {break_duration} min)")
                else:
                    # Last event - no gap after it, so no break
                    pass
        
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

        # Skip Gemini customization to ensure deterministic breaks
        # Use the automatic breaks directly - they're already properly selected based on time
        # This prevents random changes on refresh
        customized_breaks = automatic_breaks
        
        # Final validation: ensure breaks don't overlap with meetings and are in the future
        # Also ensure only ONE break per gap between meetings
        final_breaks = []
        seen_gaps = set()  # Track which gaps already have breaks - ensures only one break per gap
        
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
            
            # Find which gap this break belongs to (between which two meetings)
            gap_key = None
            for i, event in enumerate(parsed_events):
                event_start = event['start_dt']
                event_end = event['end_dt']
                
                # Check if break overlaps with meeting (with 1-minute buffer)
                if (break_time < event_end + timedelta(minutes=1) and break_end > event_start - timedelta(minutes=1)):
                    overlaps = True
                    break
                
                # Check if break is in a gap after this meeting
                if i < len(parsed_events) - 1:
                    next_event_start = parsed_events[i + 1]['start_dt']
                    # Break is in gap if it's after this event ends and before next event starts
                    if event_end <= break_time < next_event_start:
                        # Use event IDs for stable gap key, or use times as fallback
                        event_id1 = event.get('id', '') or event.get('summary', '') + str(event_start)
                        event_id2 = parsed_events[i + 1].get('id', '') or parsed_events[i + 1].get('summary', '') + str(next_event_start)
                        gap_key = (event_id1, event_id2)
                        break
            
            # Skip if overlaps with meeting
            if overlaps:
                continue
            
            # CRITICAL: Skip if we already have a break for this gap (ensure only one break per gap)
            if gap_key and gap_key in seen_gaps:
                print(f"Skipping duplicate break for gap: {gap_key}")
                continue
            
            if gap_key:
                seen_gaps.add(gap_key)
            
            time_iso = break_time.isoformat().replace('+00:00', 'Z')
            # Generate stable ID based on gap and time - ensures same break always has same ID
            # Round time to nearest minute to prevent ID changes from microsecond differences
            import hashlib
            time_rounded = break_time.replace(second=0, microsecond=0).isoformat().replace('+00:00', 'Z')
            
            # Use gap key for stable ID generation
            if gap_key:
                # Use event IDs from gap key for stability
                id_string = f"{gap_key[0]}_{gap_key[1]}_{time_rounded}"
            else:
                # Fallback to time-based ID
                id_string = f"{time_rounded}"
            
            break_id = hashlib.md5(id_string.encode()).hexdigest()[:8]
            
            final_breaks.append({
                "id": break_item.get('id') or break_id,
                "time": time_iso,
                "duration": break_item.get('duration', 10),
                "activity": break_item.get('activity', 'meditation'),
                "reason": break_item.get('reason', 'Break after meeting')
            })
        
        # Sort breaks by time for consistent ordering
        final_breaks.sort(key=lambda x: parse_datetime(x["time"]) or datetime.min.replace(tzinfo=timezone.utc))
        
        # Additional deduplication: remove breaks that are too close together (within 2 minutes)
        # This is a safety check in case gap tracking missed something
        if len(final_breaks) > 1:
            unique_breaks = [final_breaks[0]]
            for break_item in final_breaks[1:]:
                prev_break = unique_breaks[-1]
                prev_time = parse_datetime(prev_break["time"])
                curr_time = parse_datetime(break_item["time"])
                
                if prev_time and curr_time:
                    time_diff = abs((curr_time - prev_time).total_seconds())
                    # If breaks are more than 2 minutes apart, keep both
                    # Otherwise, it's likely a duplicate
                    if time_diff >= 120:  # More than 2 minutes apart
                        unique_breaks.append(break_item)
                    else:
                        print(f"Removing duplicate break: {break_item['time']} (too close to {prev_break['time']})")
            final_breaks = unique_breaks
        
        # Log final break count for debugging
        print(f"Generated {len(final_breaks)} breaks for {len(parsed_events)} events")
        
        # Cache the results for stability
        set_cached_breaks(cache_key, final_breaks, events_fingerprint)
        print(f"Cached {len(final_breaks)} breaks with fingerprint: {events_fingerprint[:8]}...")
        
        return final_breaks
    except Exception as e:
        print(f"Error generating break suggestions with Gemini: {str(e)}")
        import traceback
        traceback.print_exc()
        # Try to return automatic breaks if they were created
        try:
            if 'automatic_breaks' in locals() and automatic_breaks:
                # Cache even the automatic breaks for stability
                try:
                    if 'cache_key' in locals() and 'events_fingerprint' in locals():
                        set_cached_breaks(cache_key, automatic_breaks, events_fingerprint)
                except:
                    pass
                return automatic_breaks
        except:
            pass
        return []

