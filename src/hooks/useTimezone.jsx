import { useState, useEffect, createContext, useContext } from 'react';

/**
 * Timezone Context for managing user's timezone preference
 */
const TimezoneContext = createContext(null);

/**
 * Get initial timezone from localStorage or browser default
 */
const getInitialTimezone = () => {
  try {
    const saved = localStorage.getItem('serenity_timezone');
    if (saved) {
      return saved;
    }
    // Also check settings
    const settings = localStorage.getItem('serenity_settings');
    if (settings) {
      try {
        const parsed = JSON.parse(settings);
        if (parsed.timezone) {
          return parsed.timezone;
        }
      } catch (e) {
        // Ignore parsing errors
      }
    }
    // Default to browser timezone
    return Intl.DateTimeFormat().resolvedOptions().timeZone;
  } catch (e) {
    // Fallback to UTC
    return 'UTC';
  }
};

/**
 * Timezone hook to access and update timezone
 */
export const useTimezone = () => {
  const context = useContext(TimezoneContext);
  if (!context) {
    throw new Error('useTimezone must be used within TimezoneProvider');
  }
  return context;
};

/**
 * Timezone Provider Component
 */
export const TimezoneProvider = ({ children }) => {
  const [timezone, setTimezone] = useState(() => {
    try {
      return getInitialTimezone();
    } catch (e) {
      console.error('Error getting initial timezone:', e);
      return 'UTC';
    }
  });

  // Save timezone to localStorage when it changes
  useEffect(() => {
    try {
      localStorage.setItem('serenity_timezone', timezone);
      
      // Also update settings if they exist
      const settings = localStorage.getItem('serenity_settings');
      if (settings) {
        try {
          const parsed = JSON.parse(settings);
          parsed.timezone = timezone;
          localStorage.setItem('serenity_settings', JSON.stringify(parsed));
        } catch (e) {
          // Ignore parsing errors
          console.warn('Failed to update settings:', e);
        }
      }
    } catch (e) {
      // localStorage might not be available
      console.warn('Failed to save timezone to localStorage:', e);
    }
  }, [timezone]);

  const changeTimezone = (tz) => {
    try {
      setTimezone(tz);
    } catch (e) {
      console.error('Error changing timezone:', e);
    }
  };

  return (
    <TimezoneContext.Provider value={{ timezone, changeTimezone }}>
      {children}
    </TimezoneContext.Provider>
  );
};

/**
 * Convert a date string or Date object to the user's timezone
 */
export const toUserTimezone = (date, userTimezone) => {
  if (!date) return null;
  
  try {
    const d = typeof date === 'string' ? new Date(date) : date;
    if (isNaN(d.getTime())) return null;
    
    // Create a date in the user's timezone by formatting and parsing
    // This ensures consistent timezone handling
    const formatter = new Intl.DateTimeFormat('en-US', {
      timeZone: userTimezone,
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    });
    
    const parts = formatter.formatToParts(d);
    const year = parts.find(p => p.type === 'year').value;
    const month = parts.find(p => p.type === 'month').value;
    const day = parts.find(p => p.type === 'day').value;
    const hour = parts.find(p => p.type === 'hour').value;
    const minute = parts.find(p => p.type === 'minute').value;
    const second = parts.find(p => p.type === 'second').value;
    
    // Create a new date in local time (this represents the time in user's timezone)
    return new Date(`${year}-${month}-${day}T${hour}:${minute}:${second}`);
  } catch (e) {
    console.error('Error converting to user timezone:', e);
    return typeof date === 'string' ? new Date(date) : date;
  }
};

/**
 * Get common timezones list
 */
export const COMMON_TIMEZONES = [
  { value: 'America/New_York', label: 'Eastern Time (ET)' },
  { value: 'America/Chicago', label: 'Central Time (CT)' },
  { value: 'America/Denver', label: 'Mountain Time (MT)' },
  { value: 'America/Los_Angeles', label: 'Pacific Time (PT)' },
  { value: 'America/Phoenix', label: 'Arizona Time (MST)' },
  { value: 'America/Anchorage', label: 'Alaska Time (AKT)' },
  { value: 'Pacific/Honolulu', label: 'Hawaii Time (HST)' },
  { value: 'UTC', label: 'UTC' },
  { value: 'Europe/London', label: 'London (GMT)' },
  { value: 'Europe/Paris', label: 'Paris (CET)' },
  { value: 'Asia/Tokyo', label: 'Tokyo (JST)' },
  { value: 'Asia/Shanghai', label: 'Shanghai (CST)' },
  { value: 'Asia/Dubai', label: 'Dubai (GST)' },
  { value: 'Australia/Sydney', label: 'Sydney (AEDT)' },
  { value: 'America/Toronto', label: 'Toronto (EST)' },
  { value: 'America/Vancouver', label: 'Vancouver (PST)' },
  { value: 'America/Mexico_City', label: 'Mexico City (CST)' },
  { value: 'America/Sao_Paulo', label: 'São Paulo (BRT)' },
  { value: 'Europe/Berlin', label: 'Berlin (CET)' },
  { value: 'Asia/Kolkata', label: 'Mumbai/Delhi (IST)' },
];

