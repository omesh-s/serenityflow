import { useRef, useCallback } from 'react';
import { API_BASE_URL } from '../utils/constants';
import { useSoundControl } from './useSoundControl';

/**
 * Hook for playing event sounds (startup, error, accept)
 */
export const useEventSounds = () => {
  const audioRefs = useRef({});
  const { isMuted } = useSoundControl();

  const playSound = useCallback(async (eventType, volume = 0.7) => {
    // Don't play sound if muted
    if (isMuted) {
      return;
    }

    try {
      // Stop any currently playing sound of this type
      if (audioRefs.current[eventType]) {
        audioRefs.current[eventType].pause();
        audioRefs.current[eventType].currentTime = 0;
      }

      // Create new audio element
      const audioUrl = `${API_BASE_URL}/api/audio/event/${eventType}`;
      const audio = new Audio(audioUrl);
      audio.volume = volume;
      
      // Store reference
      audioRefs.current[eventType] = audio;

      // Play sound
      try {
        await audio.play();
      } catch (playError) {
        // User may not have interacted with page yet, or audio failed to load
        console.log(`Could not play ${eventType} sound:`, playError);
      }

      // Clean up when sound ends
      audio.addEventListener('ended', () => {
        if (audioRefs.current[eventType] === audio) {
          audioRefs.current[eventType] = null;
        }
      });

      audio.addEventListener('error', () => {
        // Silently handle errors - sounds are optional
        if (audioRefs.current[eventType] === audio) {
          audioRefs.current[eventType] = null;
        }
      });
    } catch (error) {
      // Silently handle errors - sounds are optional
      console.log(`Error playing ${eventType} sound:`, error);
    }
  }, [isMuted]);

  const playStartup = useCallback(() => playSound('startup', 0.5), [playSound]);
  const playError = useCallback(() => playSound('error', 0.6), [playSound]);
  const playAccept = useCallback(() => playSound('accept', 0.6), [playSound]);

  return {
    playStartup,
    playError,
    playAccept,
  };
};

