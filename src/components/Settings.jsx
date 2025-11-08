import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { IoSaveOutline, IoKeyOutline, IoBrushOutline, IoNotificationsOutline } from 'react-icons/io5';
import { SOUND_THEMES } from '../utils/constants';
import { useApi } from '../hooks/useApi';

/**
 * Settings Component - manage preferences and API keys
 * TODO: Connect to backend /settings endpoint
 */
const Settings = () => {
  const [settings, setSettings] = useState({
    soundTheme: 'ocean',
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

  const loadSettings = async () => {
    try {
      // TODO: API Call - Load user settings from backend
      // const userSettings = await fetchData();
      // setSettings(userSettings);
      
      // Load from localStorage for development
      const stored = localStorage.getItem('serenity_settings');
      if (stored) {
        setSettings(JSON.parse(stored));
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
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-card p-6"
      >
        <h2 className="text-3xl font-bold text-ocean-800 mb-2">Settings</h2>
        <p className="text-ocean-600">Customize your SerenityFlow experience</p>
      </motion.div>

      {/* Sound Theme */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="glass-card p-6"
      >
        <div className="flex items-center space-x-3 mb-6">
          <IoBrushOutline size={24} className="text-ocean-600" />
          <h3 className="text-xl font-semibold text-ocean-800">Sound Theme</h3>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {SOUND_THEMES.map(theme => (
            <button
              key={theme.id}
              onClick={() => handleInputChange('soundTheme', theme.id)}
              className={`p-6 rounded-xl border-2 transition-all ${
                settings.soundTheme === theme.id
                  ? 'border-ocean-500 bg-ocean-50 shadow-lg'
                  : 'border-ocean-200 bg-white hover:border-ocean-300'
              }`}
            >
              <div className="text-4xl mb-2">{theme.icon}</div>
              <p className="text-sm font-medium text-ocean-700">{theme.name}</p>
            </button>
          ))}
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

export default Settings;
