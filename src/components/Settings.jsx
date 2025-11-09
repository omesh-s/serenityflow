import React, { useState, useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import { IoSaveOutline, IoKeyOutline, IoBrushOutline, IoNotificationsOutline, IoCheckmarkCircleOutline, IoCloseCircleOutline, IoTimeOutline } from 'react-icons/io5';
import { SOUND_THEMES } from '../utils/constants';
import { useApi } from '../hooks/useApi';
import axios from 'axios';
import { API_BASE_URL } from '../utils/constants';
import { useTheme } from '../hooks/useTheme.jsx';
import { useSoundPreview } from '../hooks/useSoundPreview';
import { useTimezone, COMMON_TIMEZONES } from '../hooks/useTimezone.jsx';

/**
 * Settings Component - manage preferences and API keys
 * TODO: Connect to backend /settings endpoint
 */
const Settings = () => {
  const { currentTheme, changeTheme, themeColors } = useTheme();
  const { timezone, changeTimezone } = useTimezone();
  
  const { playPreview, stopPreview } = useSoundPreview();
  const isChangingThemeRef = useRef(false);
  const [settings, setSettings] = useState({
    soundTheme: currentTheme || 'ocean',
    timezone: timezone || Intl.DateTimeFormat().resolvedOptions().timeZone,
    elevenLabsKey: '',
    breakDuration: 5,
    notificationsEnabled: true,
    autoBreakAccept: false,
  });
  const [saved, setSaved] = useState(false);
  const { postData } = useApi('/settings');

  useEffect(() => {
    loadSettings();
  }, []);

  // Cleanup: Stop any playing preview when component unmounts or theme changes externally
  useEffect(() => {
    return () => {
      stopPreview();
    };
  }, [stopPreview]);

  // Stop preview when theme changes externally (not from user input in this component)
  useEffect(() => {
    // Only stop preview if theme changed externally (not from our own change)
    // We check if the current theme matches settings to determine if it's external
    if (currentTheme !== settings.soundTheme) {
      stopPreview();
    }
  }, [currentTheme, settings.soundTheme, stopPreview]);

  // Sync theme with settings
  useEffect(() => {
    if (settings.soundTheme !== currentTheme) {
      changeTheme(settings.soundTheme);
    }
  }, [settings.soundTheme, currentTheme, changeTheme]);

  // Sync timezone with settings
  useEffect(() => {
    if (settings.timezone && settings.timezone !== timezone) {
      changeTimezone(settings.timezone);
    }
  }, [settings.timezone, timezone, changeTimezone]);

  // Update settings when timezone changes externally
  useEffect(() => {
    if (timezone && timezone !== settings.timezone) {
      setSettings(prev => ({ ...prev, timezone }));
    }
  }, [timezone]);

  const loadSettings = async () => {
    try {
      // TODO: API Call - Load user settings from backend
      // const userSettings = await fetchData();
      // setSettings(userSettings);
      
      // Load from localStorage for development
      const stored = localStorage.getItem('serenity_settings');
      if (stored) {
        const parsed = JSON.parse(stored);
        setSettings(prev => ({
          ...prev,
          ...parsed,
          // Ensure timezone is set from hook if not in stored settings
          timezone: parsed.timezone || timezone || Intl.DateTimeFormat().resolvedOptions().timeZone
        }));
      } else {
        // Initialize with current timezone
        setSettings(prev => ({
          ...prev,
          timezone: timezone || Intl.DateTimeFormat().resolvedOptions().timeZone
        }));
      }
    } catch (error) {
      console.error('Failed to load settings:', error);
    }
  };

  const handleSave = async () => {
    try {
      // TODO: API Call - Save settings to backend
      // await postData(settings);
      
      // Save to localStorage for development
      localStorage.setItem('serenity_settings', JSON.stringify(settings));
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (error) {
      console.error('Failed to save settings:', error);
    }
  };

  const handleInputChange = (field, value) => {
    setSettings(prev => ({ ...prev, [field]: value }));
    
    // If changing sound theme, stop any playing preview, update theme, then play new preview
    if (field === 'soundTheme') {
      // Stop any currently playing preview first
      stopPreview();
      
      // Update theme immediately
      changeTheme(value);
      
      // Auto-save theme change
      const updatedSettings = { ...settings, [field]: value };
      localStorage.setItem('serenity_settings', JSON.stringify(updatedSettings));
      
      // Small delay to ensure previous audio stops, then play preview
      setTimeout(() => {
        // Only play preview if theme hasn't changed again (user might click multiple themes quickly)
        if (settings.soundTheme === value || currentTheme === value) {
          playPreview(value);
        }
      }, 150);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-card p-6"
      >
        <h2 
          className="text-3xl font-bold mb-2"
          style={{
            color: themeColors?.text || '#075985',
            transition: 'color 0.5s ease-in-out'
          }}
        >
          Settings
        </h2>
        <p 
          style={{
            color: themeColors?.textLight || '#0284c7',
            transition: 'color 0.5s ease-in-out'
          }}
        >
          Customize your Serenity experience
        </p>
      </motion.div>

      {/* Sound Theme */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="glass-card p-6"
      >
        <div className="flex items-center space-x-3 mb-6">
          <IoBrushOutline 
            size={24} 
            style={{
              color: themeColors?.textLight || '#0284c7',
              transition: 'color 0.5s ease-in-out'
            }}
          />
          <h3 
            className="text-xl font-semibold"
            style={{
              color: themeColors?.text || '#075985',
              transition: 'color 0.5s ease-in-out'
            }}
          >
            Sound Theme
          </h3>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {SOUND_THEMES.map(theme => {
            const isSelected = settings.soundTheme === theme.id;
            const themeColors = getThemeButtonColors(theme.id, isSelected);
            
            return (
              <motion.button
                key={theme.id}
                onClick={() => handleInputChange('soundTheme', theme.id)}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className={`p-6 rounded-xl border-2 transition-all duration-300 ${
                  isSelected
                    ? `${themeColors.border} ${themeColors.bg} shadow-lg ring-2 ${themeColors.ring}`
                    : 'border-gray-200 bg-white hover:border-gray-300'
                }`}
                style={{
                  transition: 'all 0.3s ease-in-out'
                }}
              >
                <div className="text-4xl mb-2">{theme.icon}</div>
                <p className={`text-sm font-medium ${isSelected ? themeColors.text : 'text-gray-700'}`}>
                  {theme.name}
                </p>
              </motion.button>
            );
          })}
        </div>
      </motion.div>

      {/* Notion Connection */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.15 }}
        className="glass-card p-6"
      >
        <div className="flex items-center space-x-3 mb-6">
          <IoKeyOutline size={24} className="text-ocean-600" />
          <h3 className="text-xl font-semibold text-ocean-800">Notion Integration</h3>
        </div>

        <div className="space-y-4">
          <p className="text-sm text-ocean-600">
            Connect your Notion workspace to enable wellness analytics and break suggestions based on your notes.
          </p>
          
          <NotionConnection />
        </div>
      </motion.div>

      {/* ElevenLabs API Key */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="glass-card p-6"
      >
        <div className="flex items-center space-x-3 mb-6">
          <IoKeyOutline size={24} className="text-ocean-600" />
          <h3 className="text-xl font-semibold text-ocean-800">ElevenLabs API Key</h3>
        </div>

        <div className="space-y-4">
          <p className="text-sm text-ocean-600">
            Provide your ElevenLabs API key to enable personalized meditation audio.
            Your key is stored securely and never shared.
          </p>
          
          <div>
            <input
              type="password"
              value={settings.elevenLabsKey}
              onChange={(e) => handleInputChange('elevenLabsKey', e.target.value)}
              placeholder="sk_..."
              className="w-full px-4 py-3 rounded-lg border-2 border-ocean-200 focus:border-ocean-500 focus:outline-none bg-white"
            />
          </div>

          <a
            href="https://elevenlabs.io/app/settings/api-keys"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-block text-sm text-ocean-600 hover:text-ocean-800 underline"
          >
            Get your API key from ElevenLabs →
          </a>
        </div>
      </motion.div>

      {/* Timezone Settings */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.25 }}
        className="glass-card p-6"
      >
        <div className="flex items-center space-x-3 mb-6">
          <IoTimeOutline 
            size={24} 
            style={{
              color: themeColors?.textLight || '#0284c7',
              transition: 'color 0.5s ease-in-out'
            }}
          />
          <h3 
            className="text-xl font-semibold"
            style={{
              color: themeColors?.text || '#075985',
              transition: 'color 0.5s ease-in-out'
            }}
          >
            Timezone
          </h3>
        </div>

        <div className="space-y-4">
          <p 
            className="text-sm"
            style={{
              color: themeColors?.textLight || '#0284c7',
              transition: 'color 0.5s ease-in-out'
            }}
          >
            Select your timezone to ensure breaks and meetings are displayed in the correct order.
          </p>
          
          <div>
            <label 
              className="block text-sm font-medium mb-2"
              style={{
                color: themeColors?.text || '#075985',
                transition: 'color 0.5s ease-in-out'
              }}
            >
              Timezone
            </label>
            <select
              value={settings.timezone}
              onChange={(e) => {
                handleInputChange('timezone', e.target.value);
                changeTimezone(e.target.value);
              }}
              className="w-full px-4 py-3 rounded-lg border-2 border-ocean-200 focus:border-ocean-500 focus:outline-none bg-white"
            >
              {COMMON_TIMEZONES.map(tz => (
                <option key={tz.value} value={tz.value}>
                  {tz.label}
                </option>
              ))}
            </select>
            <p 
              className="text-xs mt-2"
              style={{
                color: themeColors?.textLight || '#0284c7',
                transition: 'color 0.5s ease-in-out'
              }}
            >
              Current timezone: {settings.timezone}
            </p>
          </div>
        </div>
      </motion.div>

      {/* Break Preferences */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="glass-card p-6"
      >
        <div className="flex items-center space-x-3 mb-6">
          <IoNotificationsOutline size={24} className="text-ocean-600" />
          <h3 className="text-xl font-semibold text-ocean-800">Break Preferences</h3>
        </div>

        <div className="space-y-6">
          {/* Break Duration */}
          <div>
            <label className="block text-sm font-medium text-ocean-700 mb-2">
              Default Break Duration (minutes)
            </label>
            <input
              type="number"
              min="3"
              max="15"
              value={settings.breakDuration}
              onChange={(e) => handleInputChange('breakDuration', parseInt(e.target.value))}
              className="w-full px-4 py-3 rounded-lg border-2 border-ocean-200 focus:border-ocean-500 focus:outline-none bg-white"
            />
          </div>

          {/* Notifications Toggle */}
          <div className="flex items-center justify-between p-4 bg-white/50 rounded-lg">
            <div>
              <p className="font-medium text-ocean-800">Enable Break Notifications</p>
              <p className="text-sm text-ocean-600">Receive reminders when it's time for a break</p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={settings.notificationsEnabled}
                onChange={(e) => handleInputChange('notificationsEnabled', e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-ocean-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-ocean-500"></div>
            </label>
          </div>

          {/* Auto-accept Toggle */}
          <div className="flex items-center justify-between p-4 bg-white/50 rounded-lg">
            <div>
              <p className="font-medium text-ocean-800">Auto-accept Break Suggestions</p>
              <p className="text-sm text-ocean-600">Automatically start breaks when recommended</p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={settings.autoBreakAccept}
                onChange={(e) => handleInputChange('autoBreakAccept', e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-ocean-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-ocean-500"></div>
            </label>
          </div>
        </div>
      </motion.div>

      {/* Save Button */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.4 }}
        className="flex justify-end"
      >
        <button
          onClick={handleSave}
          className={`btn-primary flex items-center space-x-2 ${
            saved ? 'bg-green-500 hover:bg-green-600' : ''
          }`}
        >
          <IoSaveOutline size={20} />
          <span>{saved ? 'Saved!' : 'Save Settings'}</span>
        </button>
      </motion.div>
    </div>
  );
};

const NotionConnection = () => {
  const [notionConnected, setNotionConnected] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    checkNotionStatus();
  }, []);

  const checkNotionStatus = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/auth/status`);
      const connected = response.data.notion?.connected || false;
      setNotionConnected(connected);
    } catch (error) {
      console.error('Error checking Notion status:', error);
    }
  };

  const handleNotionConnect = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_BASE_URL}/auth/notion`);
      window.location.href = response.data.authorization_url;
    } catch (error) {
      console.error('Error connecting Notion:', error);
      setLoading(false);
    }
  };

  const handleNotionDisconnect = async () => {
    try {
      setLoading(true);
      await axios.post(`${API_BASE_URL}/auth/disconnect/notion`);
      setNotionConnected(false);
      await checkNotionStatus();
    } catch (error) {
      console.error('Error disconnecting Notion:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between p-4 bg-white/50 rounded-lg">
        <div className="flex items-center space-x-3">
          {notionConnected ? (
            <IoCheckmarkCircleOutline size={24} className="text-green-600" />
          ) : (
            <IoCloseCircleOutline size={24} className="text-gray-400" />
          )}
          <div>
            <p className="font-medium text-ocean-800">
              {notionConnected ? 'Notion Connected' : 'Notion Not Connected'}
            </p>
            <p className="text-sm text-ocean-600">
              {notionConnected 
                ? 'Your Notion workspace is connected and being analyzed' 
                : 'Connect your Notion workspace to enable wellness analytics'}
            </p>
          </div>
        </div>
        <button
          onClick={notionConnected ? handleNotionDisconnect : handleNotionConnect}
          disabled={loading}
          className={`px-4 py-2 rounded-lg font-medium transition-colors ${
            notionConnected
              ? 'bg-red-100 text-red-700 hover:bg-red-200'
              : 'bg-ocean-500 text-white hover:bg-ocean-600'
          } disabled:opacity-50`}
        >
          {loading ? 'Loading...' : notionConnected ? 'Disconnect' : 'Connect Notion'}
        </button>
      </div>

      {notionConnected && (
        <div className="p-3 bg-green-50 border border-green-200 rounded-lg">
          <p className="text-sm text-green-800">
            ✓ Notion is connected. Your notes are being analyzed for wellness insights.
          </p>
        </div>
      )}
    </div>
  );
};

/**
 * Get theme-specific button colors
 */
const getThemeButtonColors = (themeId, isSelected) => {
  const colors = {
    ocean: {
      border: isSelected ? 'border-blue-500' : 'border-blue-200',
      bg: isSelected ? 'bg-blue-50' : 'bg-white',
      ring: 'ring-blue-200',
      text: 'text-blue-700',
    },
    forest: {
      border: isSelected ? 'border-green-500' : 'border-green-200',
      bg: isSelected ? 'bg-green-50' : 'bg-white',
      ring: 'ring-green-200',
      text: 'text-green-700',
    },
    rain: {
      border: isSelected ? 'border-slate-500' : 'border-slate-200',
      bg: isSelected ? 'bg-slate-50' : 'bg-white',
      ring: 'ring-slate-200',
      text: 'text-slate-700',
    },
    wind: {
      border: isSelected ? 'border-purple-500' : 'border-purple-200',
      bg: isSelected ? 'bg-purple-50' : 'bg-white',
      ring: 'ring-purple-200',
      text: 'text-purple-700',
    },
  };
  
  return colors[themeId] || colors.ocean;
};

export default Settings;
