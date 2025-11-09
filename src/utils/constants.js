// API Configuration
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

// Google OAuth Configuration
// TODO: Replace with your actual Google Client ID from Google Cloud Console
export const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || 'YOUR_GOOGLE_CLIENT_ID';

// ElevenLabs Configuration
export const ELEVENLABS_VOICES = {
  calm: 'calm-voice-id',
  meditation: 'meditation-voice-id',
  nature: 'nature-voice-id',
};

// Break Settings
export const DEFAULT_BREAK_DURATION = 5; // minutes
export const MIN_BREAK_INTERVAL = 30; // minutes between meetings

// Theme Settings
export const SOUND_THEMES = [
  { 
    id: 'ocean', 
    name: 'Ocean Waves', 
    icon: '🌊',
    previewText: 'gentle ocean waves crashing softly on the shore',
    colorClass: 'theme-ocean'
  },
  { 
    id: 'forest', 
    name: 'Forest Sounds', 
    icon: '🌲',
    previewText: 'peaceful forest with birds chirping and leaves rustling',
    colorClass: 'theme-forest'
  },
  { 
    id: 'rain', 
    name: 'Gentle Rain', 
    icon: '🌧️',
    previewText: 'gentle rain falling softly on leaves',
    colorClass: 'theme-rain'
  },
  { 
    id: 'wind', 
    name: 'Wind Chimes', 
    icon: '🎐',
    previewText: 'delicate wind chimes tinkling in a gentle breeze',
    colorClass: 'theme-wind'
  },
];
