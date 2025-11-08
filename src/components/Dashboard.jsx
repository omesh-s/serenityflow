import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import MeetingList from './MeetingList';
import BreakTimeline from './BreakTimeline';
import MoodSummary from './MoodSummary';
import SerenityBreak from './SerenityBreak';
import { useApi } from '../hooks/useApi';
import { useBreakScheduler } from '../hooks/useBreakScheduler';

/**
 * Main Dashboard - displays calendar, breaks, and mood summary
 * TODO: Connect all components to backend API endpoints
 */
const Dashboard = () => {
  const [showBreakModal, setShowBreakModal] = useState(false);
  const { data: meetings, loading: meetingsLoading, fetchData: fetchMeetings } = useApi('/calendar/meetings');
  const { data: moodData, fetchData: fetchMood } = useApi('/analytics/mood');
  const { upcomingBreak } = useBreakScheduler();

  useEffect(() => {
    loadDashboardData();
    
    // Refresh data every 2 minutes
    const interval = setInterval(loadDashboardData, 2 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  const loadDashboardData = async () => {
    try {
      // TODO: API Calls - Fetch data from backend
      // await Promise.all([
      //   fetchMeetings({ start: new Date(), end: addDays(new Date(), 7) }),
      //   fetchMood({ period: 'week' }),
      // ]);
      console.log('Loading dashboard data...');
    } catch (error) {
      console.error('Failed to load dashboard:', error);
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
      {upcomingBreak && (
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
                  Recommended in {Math.round((upcomingBreak.scheduledTime - new Date()) / 60000)} minutes
                </p>
              </div>
            </div>
            <button onClick={handleTakeBreak} className="btn-primary">
              Take Break Now
            </button>
          </div>
        </motion.div>
      )}

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Meetings List - Takes 2 columns */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.1 }}
          className="lg:col-span-2"
        >
          <MeetingList loading={meetingsLoading} />
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
        <BreakTimeline />
      </motion.div>

      {/* Serenity Break Modal */}
      {showBreakModal && (
        <SerenityBreak onClose={() => setShowBreakModal(false)} />
      )}
    </div>
  );
};

export default Dashboard;
