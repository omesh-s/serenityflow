/** Break type definitions with icons, descriptions, and metadata */
export const BREAK_TYPES = {
  meditation: {
    name: "Meditation",
    icon: "🧘",
    description: "Quiet mindfulness and breathing exercise",
    defaultDuration: 10,
    minDuration: 5,
    maxDuration: 30,
    ambience: "calm",
    color: "#6366f1",
  },
  walk: {
    name: "Walk",
    icon: "🚶",
    description: "Short walk to refresh and move",
    defaultDuration: 15,
    minDuration: 5,
    maxDuration: 30,
    ambience: "energizing",
    color: "#10b981",
  },
  breathing: {
    name: "Breathing Exercise",
    icon: "💨",
    description: "Deep breathing and relaxation",
    defaultDuration: 5,
    minDuration: 3,
    maxDuration: 15,
    ambience: "calm",
    color: "#3b82f6",
  },
  stretch: {
    name: "Stretch",
    icon: "🤸",
    description: "Gentle stretching and movement",
    defaultDuration: 10,
    minDuration: 5,
    maxDuration: 20,
    ambience: "energizing",
    color: "#f59e0b",
  },
  rest: {
    name: "Rest",
    icon: "😴",
    description: "Quiet rest and recovery",
    defaultDuration: 15,
    minDuration: 10,
    maxDuration: 30,
    ambience: "calm",
    color: "#8b5cf6",
  },
  hydrate: {
    name: "Hydrate",
    icon: "💧",
    description: "Drink water and refresh",
    defaultDuration: 5,
    minDuration: 3,
    maxDuration: 10,
    ambience: "refreshing",
    color: "#06b6d4",
  },
  power_nap: {
    name: "Power Nap",
    icon: "😴",
    description: "Short rest to recharge",
    defaultDuration: 20,
    minDuration: 10,
    maxDuration: 30,
    ambience: "calm",
    color: "#6366f1",
  },
  mindfulness_sketch: {
    name: "Mindfulness Sketch",
    icon: "✏️",
    description: "Creative drawing or sketching",
    defaultDuration: 10,
    minDuration: 5,
    maxDuration: 20,
    ambience: "creative",
    color: "#ec4899",
  },
  snack: {
    name: "Healthy Snack",
    icon: "🍎",
    description: "Nutritious snack break",
    defaultDuration: 10,
    minDuration: 5,
    maxDuration: 15,
    ambience: "refreshing",
    color: "#f59e0b",
  },
  eye_rest: {
    name: "Eye Rest",
    icon: "👁️",
    description: "Rest eyes from screen time",
    defaultDuration: 5,
    minDuration: 3,
    maxDuration: 10,
    ambience: "calm",
    color: "#8b5cf6",
  },
};

export const getBreakType = (activity) => {
  return BREAK_TYPES[activity] || {
    name: activity ? activity.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()) : "Custom Break",
    icon: "⏸️",
    description: "Custom break",
    defaultDuration: 10,
    minDuration: 5,
    maxDuration: 30,
    ambience: "neutral",
    color: "#6b7280",
  };
};

export const getAllBreakTypes = () => {
  return Object.entries(BREAK_TYPES).map(([id, metadata]) => ({
    id,
    ...metadata,
  }));
};

