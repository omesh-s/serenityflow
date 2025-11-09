import { useState, useEffect, createContext, useContext } from 'react';

/**
 * Sound Control Context for managing mute/unmute state
 */
const SoundControlContext = createContext(null);

/**
 * Hook to access sound control
 */
export const useSoundControl = () => {
  const context = useContext(SoundControlContext);
  if (!context) {
    throw new Error('useSoundControl must be used within SoundControlProvider');
  }
  return context;
};

/**
 * Sound Control Provider Component
 */
export const SoundControlProvider = ({ children }) => {
  const [isMuted, setIsMuted] = useState(() => {
    try {
      const saved = localStorage.getItem('serenity_sound_muted');
      return saved === 'true';
    } catch (e) {
      return false;
    }
  });

  // Save mute state to localStorage
  useEffect(() => {
    try {
      localStorage.setItem('serenity_sound_muted', isMuted.toString());
    } catch (e) {
      console.warn('Failed to save mute state to localStorage:', e);
    }
  }, [isMuted]);

  const toggleMute = () => {
    setIsMuted(prev => !prev);
  };

  const mute = () => {
    setIsMuted(true);
  };

  const unmute = () => {
    setIsMuted(false);
  };

  return (
    <SoundControlContext.Provider value={{ isMuted, toggleMute, mute, unmute }}>
      {children}
    </SoundControlContext.Provider>
  );
};

