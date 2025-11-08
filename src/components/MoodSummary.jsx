import React from 'react';
import { motion } from 'framer-motion';

/**
 * Mood Summary Component - displays sentiment analytics
 * TODO: Connect to backend /analytics/mood endpoint
 */
const MoodSummary = () => {
  // Mock data for development
  const mockMoodData = {
    currentMood: 'calm',
    moodScore: 75,
    trend: 'improving',
    insights: [
      'Taking regular breaks has improved your focus',
      'Stress levels decreased by 15% this week',
      'Peak productivity hours: 10 AM - 12 PM',
    ],
    weeklyBreaks: 12,
    completionRate: 85,
  };

  const getMoodEmoji = (mood) => {
    const moods = {
      calm: '😌',
      focused: '🎯',
      energized: '⚡',
      stressed: '😰',
      relaxed: '😊',
    };
    return moods[mood] || '😊';
  };

  const getMoodColor = (score) => {
    if (score >= 80) return 'text-green-600';
    if (score >= 60) return 'text-ocean-600';
    if (score >= 40) return 'text-yellow-600';
    return 'text-orange-600';
  };

  return (
    <div className="glass-card p-6 h-full">
      <h3 className="text-xl font-semibold text-ocean-800 mb-6">Wellness Insights</h3>

      {/* Current Mood */}
      <div className="mb-6 text-center">
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: 'spring', bounce: 0.5 }}
          className="text-6xl mb-3"
        >
          {getMoodEmoji(mockMoodData.currentMood)}
        </motion.div>
        <p className="text-sm text-ocean-600 mb-2">Current State</p>
        <p className="text-2xl font-bold capitalize text-ocean-800">{mockMoodData.currentMood}</p>
      </div>

      {/* Mood Score */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-ocean-700">Wellness Score</span>
          <span className={`text-lg font-bold ${getMoodColor(mockMoodData.moodScore)}`}>
            {mockMoodData.moodScore}%
          </span>
        </div>
        <div className="w-full h-3 bg-ocean-100 rounded-full overflow-hidden">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${mockMoodData.moodScore}%` }}
            transition={{ duration: 1, ease: 'easeOut' }}
            className="h-full bg-gradient-to-r from-ocean-400 to-ocean-600 rounded-full"
          ></motion.div>
        </div>
        <p className="text-xs text-ocean-500 mt-1 text-right">
          {mockMoodData.trend === 'improving' ? '📈 Improving' : '📉 Needs attention'}
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-4 mb-6">
        <div className="bg-white/50 rounded-xl p-4 text-center">
          <p className="text-2xl font-bold text-ocean-700">{mockMoodData.weeklyBreaks}</p>
          <p className="text-xs text-ocean-600 mt-1">Breaks This Week</p>
        </div>
        <div className="bg-white/50 rounded-xl p-4 text-center">
          <p className="text-2xl font-bold text-ocean-700">{mockMoodData.completionRate}%</p>
          <p className="text-xs text-ocean-600 mt-1">Completion Rate</p>
        </div>
      </div>

      {/* Insights */}
      <div>
        <h4 className="text-sm font-semibold text-ocean-700 mb-3">AI Insights</h4>
        <div className="space-y-2">
          {mockMoodData.insights.map((insight, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.1 }}
              className="flex items-start space-x-2 text-sm"
            >
              <span className="text-ocean-400 mt-0.5">•</span>
              <span className="text-ocean-600 flex-1">{insight}</span>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default MoodSummary;
