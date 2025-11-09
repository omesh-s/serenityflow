import { useState, useRef, useCallback } from 'react';
import { API_BASE_URL } from '../utils/constants';

/**
 * Hook for playing sound theme previews
 */
export const useSoundPreview = () => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [loading, setLoading] = useState(false);
  const audioRef = useRef(null);
  const currentThemeRef = useRef(null);

  const playPreview = useCallback(async (themeId) => {
    try {
      // Stop any currently playing preview
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current.currentTime = 0;
        audioRef.current = null;
      }

      setLoading(true);
      setIsPlaying(true);
      currentThemeRef.current = themeId;

      // Create new audio element with cache busting
      const audioUrl = `${API_BASE_URL}/api/audio/chime/${themeId}?t=${Date.now()}`;
      const audio = new Audio(audioUrl);
      
      // Set volume for preview (lower than main audio)
      audio.volume = 0.3;
      
      // Set playback rate for a quicker chime effect
      audio.playbackRate = 1.2;

      // Handle audio events
      const handleEnded = () => {
        setIsPlaying(false);
        setLoading(false);
        if (audioRef.current === audio) {
          audioRef.current = null;
        }
      };

      const handleError = (e) => {
        // Silently fail - audio preview is optional
        console.log('Audio preview not available (this is okay)');
        setIsPlaying(false);
        setLoading(false);
        if (audioRef.current === audio) {
          audioRef.current = null;
        }
      };

      const handleLoadedData = () => {
        setLoading(false);
      };

      audio.addEventListener('ended', handleEnded);
      audio.addEventListener('error', handleError);
      audio.addEventListener('loadeddata', handleLoadedData);

      audioRef.current = audio;
      
      // Play the preview with error handling
      try {
        await audio.play();
      } catch (playError) {
        // User may have not interacted with page yet, or audio failed to load
        console.log('Could not play audio preview:', playError);
        handleError(playError);
      }
      
    } catch (error) {
      // Silently handle errors - audio preview is optional
      console.log('Audio preview error (this is okay):', error);
      setIsPlaying(false);
      setLoading(false);
      audioRef.current = null;
    }
  }, []);

  const stopPreview = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    setIsPlaying(false);
    setLoading(false);
  }, []);

  return {
    playPreview,
    stopPreview,
    isPlaying,
    loading,
  };
};

