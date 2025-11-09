"""Break type definitions with icons, descriptions, and ambience mapping."""
from typing import Dict, List, Optional

# Default break types with metadata
BREAK_TYPES = {
    "meditation": {
        "name": "Meditation",
        "icon": "🧘",
        "description": "Quiet mindfulness and breathing exercise",
        "default_duration": 10,
        "min_duration": 5,
        "max_duration": 30,
        "ambience": "calm",
        "color": "#6366f1",  # Indigo
    },
    "walk": {
        "name": "Walk",
        "icon": "🚶",
        "description": "Short walk to refresh and move",
        "default_duration": 15,
        "min_duration": 5,
        "max_duration": 30,
        "ambience": "energizing",
        "color": "#10b981",  # Green
    },
    "breathing": {
        "name": "Breathing Exercise",
        "icon": "💨",
        "description": "Deep breathing and relaxation",
        "default_duration": 5,
        "min_duration": 3,
        "max_duration": 15,
        "ambience": "calm",
        "color": "#3b82f6",  # Blue
    },
    "stretch": {
        "name": "Stretch",
        "icon": "🤸",
        "description": "Gentle stretching and movement",
        "default_duration": 10,
        "min_duration": 5,
        "max_duration": 20,
        "ambience": "energizing",
        "color": "#f59e0b",  # Amber
    },
    "rest": {
        "name": "Rest",
        "icon": "😴",
        "description": "Quiet rest and recovery",
        "default_duration": 15,
        "min_duration": 10,
        "max_duration": 30,
        "ambience": "calm",
        "color": "#8b5cf6",  # Purple
    },
    "hydrate": {
        "name": "Hydrate",
        "icon": "💧",
        "description": "Drink water and refresh",
        "default_duration": 5,
        "min_duration": 3,
        "max_duration": 10,
        "ambience": "refreshing",
        "color": "#06b6d4",  # Cyan
    },
    "power_nap": {
        "name": "Power Nap",
        "icon": "😴",
        "description": "Short rest to recharge",
        "default_duration": 20,
        "min_duration": 10,
        "max_duration": 30,
        "ambience": "calm",
        "color": "#6366f1",  # Indigo
    },
    "mindfulness_sketch": {
        "name": "Mindfulness Sketch",
        "icon": "✏️",
        "description": "Creative drawing or sketching",
        "default_duration": 10,
        "min_duration": 5,
        "max_duration": 20,
        "ambience": "creative",
        "color": "#ec4899",  # Pink
    },
    "snack": {
        "name": "Healthy Snack",
        "icon": "🍎",
        "description": "Nutritious snack break",
        "default_duration": 10,
        "min_duration": 5,
        "max_duration": 15,
        "ambience": "refreshing",
        "color": "#f59e0b",  # Amber
    },
    "eye_rest": {
        "name": "Eye Rest",
        "icon": "👁️",
        "description": "Rest eyes from screen time",
        "default_duration": 5,
        "min_duration": 3,
        "max_duration": 10,
        "ambience": "calm",
        "color": "#8b5cf6",  # Purple
    },
}


def get_break_type(activity: str) -> Dict:
    """Get break type metadata by activity name."""
    return BREAK_TYPES.get(activity, {
        "name": activity.title(),
        "icon": "⏸️",
        "description": "Custom break",
        "default_duration": 10,
        "min_duration": 5,
        "max_duration": 30,
        "ambience": "neutral",
        "color": "#6b7280",  # Gray
    })


def get_all_break_types() -> List[Dict]:
    """Get all available break types."""
    return [
        {**metadata, "id": activity_id}
        for activity_id, metadata in BREAK_TYPES.items()
    ]


def is_valid_break_type(activity: str) -> bool:
    """Check if activity is a valid break type."""
    return activity in BREAK_TYPES


def get_break_type_suggestions(context: str = "") -> List[str]:
    """Get suggested break types based on context."""
    # Default suggestions
    suggestions = ["meditation", "walk", "breathing", "stretch", "rest", "hydrate"]
    
    # Context-aware suggestions
    context_lower = context.lower()
    if "tired" in context_lower or "exhausted" in context_lower:
        suggestions = ["power_nap", "rest", "meditation"] + suggestions
    elif "stressed" in context_lower or "overwhelmed" in context_lower:
        suggestions = ["breathing", "meditation", "walk"] + suggestions
    elif "long" in context_lower and "meeting" in context_lower:
        suggestions = ["stretch", "walk", "eye_rest"] + suggestions
    elif "focus" in context_lower or "deep work" in context_lower:
        suggestions = ["walk", "breathing", "snack"] + suggestions
    
    return suggestions[:6]  # Return top 6 suggestions

