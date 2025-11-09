import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import MeetingList from './MeetingList';
import BreakTimeline from './BreakTimeline';
import MoodSummary from './MoodSummary';
import SerenityBreak from './SerenityBreak';
import axios from 'axios';
import { API_BASE_URL } from '../utils/constants';
import { useBreakScheduler } from '../hooks/useBreakScheduler';

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

  useEffect(() => {
    loadDashboardData();
    
    // Refresh data every 2 minutes
    const interval = setInterval(loadDashboardData, 2 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await axios.get(`${API_BASE_URL}/api/serenity/schedule`, {
        params: {
          max_events: 10,
          max_pages: 10
        }
      });
      setScheduleData(response.data);
    } catch (err) {
      console.error('Failed to load dashboard:', err);
      setError('Failed to load schedule. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleTakeBreak = () => {
    setShowBreakModal(true);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-card p-6"
      >
        <h2 className="text-3xl font-bold text-ocean-800 mb-2">Welcome back 🌊</h2>
        <p className="text-ocean-600">Here's your schedule and wellness insights for today.</p>
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
              className="glass-card p-6 border-2 border-ocean-300 serenity-gradient"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-4">
                  <div className="w-12 h-12 rounded-full bg-white flex items-center justify-center animate-breath">
                    <span className="text-2xl">🧘</span>
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-ocean-800">Time for a Serenity Break</h3>
                    <p className="text-ocean-600 text-sm">
                      {nextBreak.activity} break recommended in {minutesUntil} minutes
                    </p>
                    <p className="text-ocean-500 text-xs mt-1">{nextBreak.reason}</p>
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
          />
        </motion.div>

        {/* Mood Summary - Takes 1 column */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.2 }}
        >
          <MoodSummary />
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
        />
      </motion.div>

      {/* Serenity Break Modal */}
      {showBreakModal && (
        <SerenityBreak onClose={() => setShowBreakModal(false)} />
      )}
    </div>
  );
};

export default Dashboard;
