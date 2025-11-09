"""Wellness cache to reduce Gemini API calls."""
from datetime import datetime, timedelta
from typing import Dict, Tuple, Any, List
import hashlib
import json

# Cache for wellness results to avoid repeated Gemini API calls
_wellness_cache: Dict[str, Tuple[Dict[str, Any], datetime, str]] = {}
_cache_ttl = timedelta(minutes=30)  # Cache for 30 minutes (or until notes change)


def get_notes_fingerprint(pages: List[Dict]) -> str:
    """Generate a fingerprint based on note IDs and last edited times.
    This ensures cache is invalidated when notes actually change.
    """
    if not pages:
        return "no_notes"
    
    # Get note IDs and last edited times
    note_info = []
    for page in pages[:50]:  # Limit to first 50 notes
        note_id = page.get('id', '')
        last_edited = page.get('last_edited_time', '')
        note_info.append(f"{note_id}:{last_edited}")
    
    # Create hash of note information
    notes_str = "|".join(sorted(note_info))
    return hashlib.md5(notes_str.encode()).hexdigest()[:16]


def get_cached_wellness(cache_key: str, notes_fingerprint: str = None) -> Tuple[bool, Dict[str, Any]]:
    """Get cached wellness data if available and not expired.
    
    Args:
        cache_key: Cache key for the user
        notes_fingerprint: Optional fingerprint of current notes. If provided,
                         cache is invalidated if notes have changed.
    
    Returns:
        Tuple of (is_cached, data)
    """
    if cache_key in _wellness_cache:
        cached_data, cached_time, cached_fingerprint = _wellness_cache[cache_key]
        
        # Check if notes have changed
        if notes_fingerprint and cached_fingerprint != notes_fingerprint:
            # Notes have changed, invalidate cache
            del _wellness_cache[cache_key]
            return False, {}
        
        # Check if cache is expired
        if datetime.utcnow() - cached_time < _cache_ttl:
            return True, cached_data
        else:
            # Remove expired cache
            del _wellness_cache[cache_key]
    return False, {}


def set_cached_wellness(cache_key: str, data: Dict[str, Any], notes_fingerprint: str = None):
    """Cache wellness data with optional notes fingerprint."""
    _wellness_cache[cache_key] = (data, datetime.utcnow(), notes_fingerprint or "")


def clear_cache():
    """Clear all cached wellness data."""
    _wellness_cache.clear()

