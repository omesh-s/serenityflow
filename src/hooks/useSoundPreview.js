import { useState, useRef, useCallback, useEffect } from 'react';
import { API_BASE_URL } from '../utils/constants';

/**
 * Hook for playing sound theme previews
 */
export const useSoundPreview = () => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [loading, setLoading] = useState(false);
  const audioRef = useRef(null);
  const currentThemeRef = useRef(null);
  const timeoutRef = useRef(null);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
      if (audioRef.current) {
        try {
          audioRef.current.pause();
          audioRef.current.currentTime = 0;
        } catch (e) {
          // Ignore
        }
      }
    };
  }, []);

  const playPreview = useCallback(async (themeId) => {
    try {
      // Stop any currently playing preview first
      if (audioRef.current) {
        try {
          audioRef.current.pause();
          audioRef.current.currentTime = 0;
          // Remove event listeners
          audioRef.current.onended = null;
          audioRef.current.onerror = null;
          audioRef.current.onloadeddata = null;
          audioRef.current.oncanplay = null;
        } catch (e) {
          // Ignore errors when stopping
        }
        audioRef.current = null;
      }

      // Clear any existing timeout
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }

      setLoading(true);
      setIsPlaying(true);
      currentThemeRef.current = themeId;

      // Create new audio element with cache busting
      const audioUrl = `${API_BASE_URL}/api/audio/chime/${themeId}?t=${Date.now()}`;
      const audio = new Audio(audioUrl);
      
      // CRITICAL: Do NOT set loop - preview should play once and stop
      audio.loop = false;
      
      // Force remove any loop metadata that might be in the audio file
      audio.addEventListener('loadedmetadata', () => {
        audio.loop = false; // Explicitly set to false after metadata loads
      }, { once: true });
      
      // Set volume for preview (lower than main audio)
      audio.volume = 0.3;
      
      // Set playback rate for a quicker chime effect
      audio.playbackRate = 2.5; // Faster playback for shorter preview

      // Set maximum preview duration (1.5 seconds max to keep it very short)
      const MAX_PREVIEW_DURATION = 1500; // 1.5 seconds

      // Handle audio events
      const handleEnded = () => {
        setIsPlaying(false);
        setLoading(false);
        // Clear timeout if audio ends naturally
        if (timeoutRef.current) {
          clearTimeout(timeoutRef.current);
          timeoutRef.current = null;
        }
        // Clean up audio reference
        if (audioRef.current === audio) {
          try {
            audioRef.current.pause();
            audioRef.current.currentTime = 0;
            audioRef.current.onended = null;
            audioRef.current.onerror = null;
            audioRef.current.onloadeddata = null;
            audioRef.current.oncanplay = null;
          } catch (e) {
            // Ignore cleanup errors
          }
          audioRef.current = null;
        }
      };

      const handleError = (e) => {
        // Silently fail - audio preview is optional
        console.log('Audio preview not available (this is okay)');
        setIsPlaying(false);
        setLoading(false);
        // Clear timeout on error
        if (timeoutRef.current) {
          clearTimeout(timeoutRef.current);
          timeoutRef.current = null;
        }
        // Clean up audio reference
        if (audioRef.current === audio) {
          audioRef.current = null;
        }
      };

      const handleLoadedData = () => {
        setLoading(false);
      };

      // Add event listeners with once: true to ensure they only fire once
      audio.addEventListener('ended', handleEnded, { once: true });
      audio.addEventListener('error', handleError, { once: true });
      audio.addEventListener('loadeddata', handleLoadedData, { once: true });

      audioRef.current = audio;
      
      // Set a timeout to force stop the preview after max duration
      // This ensures the preview stops even if the audio file is long
      timeoutRef.current = setTimeout(() => {
        if (audioRef.current === audio) {
          try {
            audio.pause();
            audio.currentTime = 0;
            handleEnded();
          } catch (e) {
            // Ignore errors
          }
        }
      }, MAX_PREVIEW_DURATION);
      
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
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }
    }
  }, []);

  const stopPreview = useCallback(() => {
    // Clear timeout
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    
    if (audioRef.current) {
      try {
        audioRef.current.pause();
        audioRef.current.currentTime = 0;
        // Remove event listeners to prevent memory leaks
        audioRef.current.onended = null;
        audioRef.current.onerror = null;
        audioRef.current.onloadeddata = null;
        audioRef.current.oncanplay = null;
      } catch (e) {
        // Ignore errors when stopping
      }
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

