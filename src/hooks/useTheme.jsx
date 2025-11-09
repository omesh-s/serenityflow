import { useState, useEffect, createContext, useContext } from 'react';

/**
 * Theme Context for managing sound themes and colors
 */
const ThemeContext = createContext(null);

/**
 * Get color palette for a theme
 */
export const getThemeColors = (themeId) => {
  const themes = {
    ocean: {
      primary: '#0ea5e9',
      primaryDark: '#0369a1',
      primaryLight: '#38bdf8',
      accent: '#0284c7',
      background: 'linear-gradient(135deg, #e0f2fe 0%, #bae6fd 50%, #7dd3fc 100%)',
      backgroundStart: '#e0f2fe',
      backgroundEnd: '#7dd3fc',
      card: 'rgba(240, 249, 255, 0.6)',
      text: '#075985',
      textLight: '#0284c7',
    },
    forest: {
      primary: '#16a34a',
      primaryDark: '#15803d',
      primaryLight: '#4ade80',
      accent: '#22c55e',
      background: 'linear-gradient(135deg, #dcfce7 0%, #bbf7d0 50%, #86efac 100%)',
      backgroundStart: '#dcfce7',
      backgroundEnd: '#86efac',
      card: 'rgba(240, 253, 244, 0.6)',
      text: '#166534',
      textLight: '#15803d',
    },
    rain: {
      primary: '#64748b',
      primaryDark: '#475569',
      primaryLight: '#94a3b8',
      accent: '#64748b',
      background: 'linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 50%, #cbd5e1 100%)',
      backgroundStart: '#f1f5f9',
      backgroundEnd: '#cbd5e1',
      card: 'rgba(248, 250, 252, 0.6)',
      text: '#334155',
      textLight: '#475569',
    },
    wind: {
      primary: '#a78bfa',
      primaryDark: '#8b5cf6',
      primaryLight: '#c4b5fd',
      accent: '#a78bfa',
      background: 'linear-gradient(135deg, #faf5ff 0%, #f3e8ff 50%, #e9d5ff 100%)',
      backgroundStart: '#faf5ff',
      backgroundEnd: '#e9d5ff',
      card: 'rgba(250, 245, 255, 0.6)',
      text: '#7c3aed',
      textLight: '#8b5cf6',
    },
  };

  return themes[themeId] || themes.ocean;
};

/**
 * Apply theme colors to CSS variables
 */
const applyThemeColors = (colors) => {
  try {
    if (typeof document === 'undefined') {
      // SSR - document not available
      return;
    }
    
    const root = document.documentElement;
    if (!root) {
      return;
    }
    
    root.style.setProperty('--theme-primary', colors.primary);
    root.style.setProperty('--theme-primary-dark', colors.primaryDark);
    root.style.setProperty('--theme-primary-light', colors.primaryLight);
    root.style.setProperty('--theme-accent', colors.accent);
    root.style.setProperty('--theme-text', colors.text);
    root.style.setProperty('--theme-text-light', colors.textLight);
    root.style.setProperty('--theme-background', colors.background);
    
    // Also set RGB values for opacity calculations
    const hexToRgb = (hex) => {
      try {
        const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
        return result 
          ? `${parseInt(result[1], 16)}, ${parseInt(result[2], 16)}, ${parseInt(result[3], 16)}`
          : '14, 165, 233';
      } catch (e) {
        return '14, 165, 233';
      }
    };
    
    root.style.setProperty('--theme-primary-rgb', hexToRgb(colors.primary));
    root.style.setProperty('--theme-primary-dark-rgb', hexToRgb(colors.primaryDark));
    root.style.setProperty('--theme-primary-light-rgb', hexToRgb(colors.primaryLight));
  } catch (e) {
    console.error('Error applying theme colors to DOM:', e);
  }
};

/**
 * Get initial theme from localStorage
 */
const getInitialTheme = () => {
  try {
    const savedTheme = localStorage.getItem('serenity_sound_theme');
    if (savedTheme) {
      return savedTheme;
    }
    // Also check settings
    const settings = localStorage.getItem('serenity_settings');
    if (settings) {
      try {
        const parsed = JSON.parse(settings);
        if (parsed.soundTheme) {
          return parsed.soundTheme;
        }
      } catch (e) {
        // Ignore parsing errors
      }
    }
  } catch (e) {
    // localStorage not available
  }
  return 'ocean';
};

/**
 * Theme hook to access and update theme
 */
export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within ThemeProvider');
  }
  return context;
};

/**
 * Theme Provider Component
 */
export const ThemeProvider = ({ children }) => {
  // Initialize with theme from localStorage or default
  // Use a function to safely initialize state
  const [currentTheme, setCurrentTheme] = useState(() => {
    try {
      return getInitialTheme();
    } catch (e) {
      console.error('Error getting initial theme:', e);
      return 'ocean';
    }
  });
  
  const [themeColors, setThemeColors] = useState(() => {
    try {
      const theme = getInitialTheme();
      return getThemeColors(theme);
    } catch (e) {
      console.error('Error getting initial theme colors:', e);
      return getThemeColors('ocean');
    }
  });

  // Apply theme colors on mount and when theme changes
  useEffect(() => {
    try {
      const colors = getThemeColors(currentTheme);
      setThemeColors(colors);
      applyThemeColors(colors);
    } catch (e) {
      console.error('Error applying theme colors:', e);
      // Fallback to default
      const defaultColors = getThemeColors('ocean');
      setThemeColors(defaultColors);
      applyThemeColors(defaultColors);
    }
  }, [currentTheme]);

  // Save theme to localStorage when it changes
  useEffect(() => {
    try {
      localStorage.setItem('serenity_sound_theme', currentTheme);
      
      // Also update settings if they exist
      const settings = localStorage.getItem('serenity_settings');
      if (settings) {
        try {
          const parsed = JSON.parse(settings);
          parsed.soundTheme = currentTheme;
          localStorage.setItem('serenity_settings', JSON.stringify(parsed));
        } catch (e) {
          // Ignore parsing errors
          console.warn('Failed to update settings:', e);
        }
      }
    } catch (e) {
      // localStorage might not be available
      console.warn('Failed to save theme to localStorage:', e);
    }
  }, [currentTheme]);

  const changeTheme = (themeId) => {
    try {
      setCurrentTheme(themeId);
    } catch (e) {
      console.error('Error changing theme:', e);
    }
  };

  // Ensure we always have valid theme colors
  const safeThemeColors = themeColors || getThemeColors('ocean');

  return (
    <ThemeContext.Provider value={{ currentTheme, themeColors: safeThemeColors, changeTheme }}>
      {children}
    </ThemeContext.Provider>
  );
};
