"""Cache for break suggestions to prevent regeneration on every request."""
from datetime import datetime, timedelta
from typing import Dict, Tuple, List, Optional
import hashlib
import json

# Cache for break suggestions
_break_cache: Dict[str, Tuple[List[Dict], datetime, str]] = {}
_cache_ttl = timedelta(hours=24)  # Cache breaks for 24 hours - breaks should be stable


def get_events_fingerprint(events: List[Dict]) -> str:
    """Generate a stable fingerprint based on event IDs and times.
    Events are sorted by start time first to ensure consistent fingerprinting
    regardless of API response order.
    """
    if not events:
        return "no_events"
    
    # Sort events by start time to ensure consistent fingerprinting
    # This prevents cache misses when events come in different orders
    sorted_events = sorted(events, key=lambda e: (e.get('start', ''), e.get('id', '')))
    
    # Get event IDs and times (normalized)
    event_info = []
    for event in sorted_events[:20]:  # Limit to first 20 events
        event_id = event.get('id', '')
        start = event.get('start', '')
        end = event.get('end', '')
        # Normalize times to remove any timezone variations that don't affect breaks
        # Use just the date and time part, not the full ISO string
        event_info.append(f"{event_id}:{start}:{end}")
    
    # Create hash of event information (already sorted, so this is deterministic)
    events_str = "|".join(event_info)
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

