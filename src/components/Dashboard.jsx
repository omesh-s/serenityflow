import React, { useState, useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import MeetingList from './MeetingList';
import BreakTimeline from './BreakTimeline';
import MoodSummary from './MoodSummary';
import SerenityBreak from './SerenityBreak';
import ConvaiWidget from './ConvaiWidget';
import axios from 'axios';
import { API_BASE_URL } from '../utils/constants';
import { useBreakScheduler } from '../hooks/useBreakScheduler';
import { useTheme } from '../hooks/useTheme.jsx';
import { useTimezone } from '../hooks/useTimezone.jsx';
import { useAuth } from '../hooks/useAuth';
import { hexToRgba } from '../utils/hexToRgb';

/**
 * Main Dashboard - displays calendar, breaks, and mood summary
 * Connects to backend API endpoints
 */
const Dashboard = () => {
  const [showBreakModal, setShowBreakModal] = useState(false);
  const [scheduleData, setScheduleData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const { upcomingBreak } = useBreakScheduler();
  const { themeColors } = useTheme();
  const { timezone } = useTimezone();
  const { user } = useAuth();
  
  // Memoize schedule data to prevent unnecessary re-fetches
  const [lastFetchTime, setLastFetchTime] = useState(0);

  // Load data only once on mount - no automatic refresh
  useEffect(() => {
    // Only load if we don't have data yet
    if (!scheduleData) {
      loadDashboardData(false, true); // Load once, show loading spinner
    }
    
    // Disable automatic refresh to prevent breaks from changing
    // User can manually refresh if needed
    // const interval = setInterval(() => {
    //   if (scheduleData) {
    //     loadDashboardData(false, false);
    //   }
    // }, 5 * 60 * 1000);
    // return () => clearInterval(interval);
  }, []); // Empty dependency array - only run on mount
  
  // Separate effect for timezone changes - but don't auto-reload
  // Only reload if user explicitly changes timezone in settings
  // useEffect(() => {
  //   if (scheduleData && timezone) {
  //     loadDashboardData(true, true);
  //   }
  // }, [timezone]);

  const loadDashboardData = async (forceRefresh = false, showLoading = true) => {
    try {
      // Only show loading if explicitly requested and (force refresh or first load)
      if (showLoading && (forceRefresh || !scheduleData)) {
        setLoading(true);
      }
      setError(null);
      const response = await axios.get(`${API_BASE_URL}/api/serenity/schedule`, {
        params: {
          max_events: 10,
          max_pages: 10,
          timezone: timezone || Intl.DateTimeFormat().resolvedOptions().timeZone
        }
      });
      setScheduleData(response.data);
      setLastFetchTime(Date.now());
    } catch (err) {
      console.error('Failed to load dashboard:', err);
      setError('Failed to load schedule. Please try again.');
    } finally {
      if (showLoading) {
        setLoading(false);
      }
    }
  };

  // Refs to track audio and timer so we can stop playback from other handlers
  const audioRef = useRef(null);
  const audioTimerRef = useRef(null);

  // Stop audio helper (available to modal close and cleanup)
  const stopCalmingAudio = () => {
    try {
      if (audioTimerRef.current) {
        clearTimeout(audioTimerRef.current);
        audioTimerRef.current = null;
      }
      if (audioRef.current) {
        try {
          audioRef.current.pause();
          audioRef.current.currentTime = 0;
        } catch (e) {
          // ignore
        }
        audioRef.current = null;
      }
    } catch (err) {
      console.error('Failed to stop calming audio:', err);
    }
  };

  // Start calming audio and schedule stop after 5 minutes
  const startCalmingAudio = (url) => {
    try {
      // Stop any existing audio first
      stopCalmingAudio();

      const audio = new Audio(url);
      audio.loop = true;
      audio.play().catch((err) => {
        // autoplay may be blocked by browser policies; user interaction usually allows playback
        console.warn('Audio playback failed (browser may block autoplay):', err);
      });
      audioRef.current = audio;

      // Ensure audio stops after 5 minutes (300000 ms)
      audioTimerRef.current = window.setTimeout(() => {
        stopCalmingAudio();
      }, 5 * 60 * 1000);
    } catch (err) {
      console.error('Failed to start calming audio:', err);
    }
  };

  const handleTakeBreak = () => {
    const CALM_AUDIO_URL = '/assets/calm.wav';

    startCalmingAudio(CALM_AUDIO_URL);
    setShowBreakModal(true);
  };

  // Stop audio when component unmounts
  useEffect(() => {
    return () => {
      stopCalmingAudio();
    };
  }, []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-card p-6"
      >
        <h2 
          className="text-3xl font-bold mb-2"
          style={{
            color: themeColors ? themeColors.text : '#075985',
            transition: 'color 0.5s ease-in-out'
          }}
        >
          Welcome back{user?.name && user.name !== 'User' ? `, ${user.name}` : ''}
        </h2>
        <p 
          style={{
            color: themeColors ? themeColors.textLight : '#0284c7',
            transition: 'color 0.5s ease-in-out'
          }}
        >
          Here's your schedule and wellness insights for today.
        </p>
      </motion.div>

      {/* Upcoming Break Alert */}
      {scheduleData?.break_suggestions && scheduleData.break_suggestions.length > 0 && (() => {
        const nextBreak = scheduleData.break_suggestions[0];
        const breakTime = new Date(nextBreak.time);
        const minutesUntil = Math.round((breakTime - new Date()) / 60000);
        
        if (minutesUntil > 0 && minutesUntil < 60) {
          return (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="glass-card p-6 border-2"
              style={{
                borderColor: themeColors ? hexToRgba(themeColors.primary, 0.5) : '#7dd3fc',
                background: themeColors 
                  ? `linear-gradient(135deg, ${hexToRgba(themeColors.backgroundStart, 0.8)} 0%, ${hexToRgba(themeColors.backgroundEnd, 0.8)} 100%)`
                  : 'linear-gradient(135deg, #e8f4f8 0%, #b8dde6 50%, #7fb3c2 100%)',
                transition: 'all 0.5s ease-in-out'
              }}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-4">
                  <div className="w-12 h-12 rounded-full bg-white flex items-center justify-center animate-breath">
                    <span className="text-2xl">🧘</span>
                  </div>
                  <div>
                    <h3 
                      className="text-lg font-semibold"
                      style={{
                        color: themeColors ? themeColors.text : '#075985',
                        transition: 'color 0.5s ease-in-out'
                      }}
                    >
                      Time for a Serenity Break
                    </h3>
                    <p 
                      className="text-sm"
                      style={{
                        color: themeColors ? themeColors.textLight : '#0284c7',
                        transition: 'color 0.5s ease-in-out'
                      }}
                    >
                      {nextBreak.activity} break recommended in {minutesUntil} minutes
                    </p>
                    <p 
                      className="text-xs mt-1"
                      style={{
                        color: themeColors ? hexToRgba(themeColors.textLight, 0.8) : '#0ea5e9',
                        transition: 'color 0.5s ease-in-out'
                      }}
                    >
                      {nextBreak.reason}
                    </p>
                  </div>
                </div>
                <button onClick={handleTakeBreak} className="btn-primary">
                  Take Break Now
                </button>
              </div>
            </motion.div>
          );
        }
        return null;
      })()}

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Meetings List - Takes 2 columns */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.1 }}
          className="lg:col-span-2"
        >
          <MeetingList
            loading={loading}
            events={scheduleData?.events || []}
            error={error}
            onMeetingEnd={async (event) => {
              // Meeting ended handler wired from Dashboard
              // We look up the current wellness/mood score from the schedule data returned by the backend.
              // Path: scheduleData.wellness_metrics.wellness_score (number, 0-100)
              const moodScore = scheduleData?.wellness_metrics?.wellness_score;

             
              const MOOD_THRESHOLD = 70; 
              console.log('Checking mood score on meeting end:', moodScore);
              if (typeof moodScore === 'number' && moodScore < MOOD_THRESHOLD) {
                try {
                  // Only allow calling the explicitly permitted destination. The backend also enforces this.
                  const allowedTo = '+18607302832';
                  const message = `Hi — we noticed your wellness score is ${moodScore}. If you'd like support, reply or press any key to connect.`;
                  const resp = await axios.post(`${API_BASE_URL}/api/twilio/call`, {
                    to: allowedTo,
                    message,
                  });
                  console.log('Twilio call response:', resp.data);
                } catch (err) {
                  console.error('Failed to initiate Twilio call:', err);
                  // Fallback to showing the break modal if the call fails
                  handleTakeBreak();
                }
              } else {
                // Default/else behavior: open the Take Break modal so the user can start a break immediately.
                // This is the standard behavior used previously.
                console.log('onMeetingEnd fired for event:', event, 'moodScore:', moodScore);
                handleTakeBreak();
              }
            }}
          />
        </motion.div>

        {/* Mood Summary - Takes 1 column */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.2 }}
        >
          <MoodSummary wellnessMetrics={scheduleData?.wellness_metrics} />
        </motion.div>
      </div>

             {/* Break Timeline */}
             <motion.div
               initial={{ opacity: 0, y: 20 }}
               animate={{ opacity: 1, y: 0 }}
               transition={{ delay: 0.3 }}
             >
               <BreakTimeline 
                 events={scheduleData?.events || []}
                 breakSuggestions={scheduleData?.break_suggestions || []}
                 loading={loading}
                 onBreaksUpdate={() => {
                   // Small delay to allow backend to process the update
                   setTimeout(() => loadDashboardData(true), 500);
                 }}
               />
             </motion.div>

      {/* Serenity Break Modal */}
      {showBreakModal && (
        <SerenityBreak onClose={() => {
          // Stop the calming audio when the modal is closed by the user
          stopCalmingAudio();
          setShowBreakModal(false);
        }} />
      )}

      {/* ElevenLabs ConvAI widget (embedded) - renders the chat/agent widget on the dashboard */}
      <ConvaiWidget />
    </div>
  );
};

export default Dashboard;
