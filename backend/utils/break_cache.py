"""Cache for break suggestions to prevent regeneration on every request."""
from datetime import datetime, timedelta
from typing import Dict, Tuple, List, Optional
import hashlib
import json

# Cache for break suggestions
_break_cache: Dict[str, Tuple[List[Dict], datetime, str]] = {}
_cache_ttl = timedelta(hours=1)  # Cache breaks for 1 hour


def get_events_fingerprint(events: List[Dict]) -> str:
    """Generate a fingerprint based on event IDs and times."""
    if not events:
        return "no_events"
    
    # Get event IDs and times
    event_info = []
    for event in events[:20]:  # Limit to first 20 events
        event_id = event.get('id', '')
        start = event.get('start', '')
        end = event.get('end', '')
        event_info.append(f"{event_id}:{start}:{end}")
    
    # Create hash of event information
    events_str = "|".join(sorted(event_info))
    return hashlib.md5(events_str.encode()).hexdigest()[:16]


def get_cached_breaks(cache_key: str, events_fingerprint: str = None) -> Tuple[bool, List[Dict]]:
    """Get cached break suggestions if available and not expired.
    
    Args:
        cache_key: Cache key for the user
        events_fingerprint: Optional fingerprint of current events. If provided,
                          cache is invalidated if events have changed.
    
    Returns:
        Tuple of (is_cached, breaks)
    """
    if cache_key in _break_cache:
        cached_breaks, cached_time, cached_fingerprint = _break_cache[cache_key]
        
        # Check if events have changed
        if events_fingerprint and cached_fingerprint != events_fingerprint:
            # Events have changed, invalidate cache
            del _break_cache[cache_key]
            return False, []
        
        # Check if cache is expired
        if datetime.utcnow() - cached_time < _cache_ttl:
            return True, cached_breaks
        else:
            # Remove expired cache
            del _break_cache[cache_key]
    return False, []


def set_cached_breaks(cache_key: str, breaks: List[Dict], events_fingerprint: str = None):
    """Cache break suggestions with optional events fingerprint."""
    _break_cache[cache_key] = (breaks, datetime.utcnow(), events_fingerprint or "")


def clear_break_cache():
    """Clear all cached break suggestions."""
    _break_cache.clear()

