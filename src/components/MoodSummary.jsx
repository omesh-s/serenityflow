import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import axios from 'axios';
import { API_BASE_URL } from '../utils/constants';

/**
 * Insights Display Component - Shows informative insights with expand/collapse
 * Shows first 2 insights by default, expands to show all on "more" click
 */
const InsightsDisplay = ({ insights }) => {
  const [expanded, setExpanded] = useState(false);
  
  // Show first 2 insights by default (since they're now more informative)
  const defaultCount = 2;
  const displayInsights = expanded ? insights : insights.slice(0, defaultCount).filter(Boolean);
  const hasMore = insights.length > defaultCount;

  return (
    <div className="space-y-2">
      {displayInsights.map((insight, index) => (
        <motion.div
          key={index}
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: index * 0.05 }}
          className="flex items-start space-x-2"
        >
          <span className="text-ocean-400 mt-1 text-sm">•</span>
          <span className="text-ocean-600 flex-1 text-sm leading-relaxed">{insight}</span>
        </motion.div>
      ))}
      {hasMore && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-sm text-ocean-500 hover:text-ocean-700 mt-1 ml-5 transition-colors focus:outline-none font-medium"
        >
          {expanded ? '... Show less' : `... Show ${insights.length - defaultCount} more`}
        </button>
      )}
    </div>
  );
};

/**
 * Mood Summary Component - displays wellness analytics from Notion
 * Can receive wellness metrics as props or fetch from backend
 */
const MoodSummary = ({ wellnessMetrics = null }) => {
  const [wellnessData, setWellnessData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    // If wellness metrics are provided as props, use them (no additional API call needed)
    if (wellnessMetrics) {
      const metricsData = {
        wellness_score: wellnessMetrics.wellness_score || 50,
        completion_rate: wellnessMetrics.completion_rate || 0,
        peak_productivity_hours: wellnessMetrics.peak_productivity_hours || 'No data available',
        insights: wellnessMetrics.insights || [],
        engagement_score: wellnessMetrics.engagement_score || 0,
        active_days: wellnessMetrics.active_days || 0,
        total_notes: wellnessMetrics.total_notes || 0,
        current_state: wellnessMetrics.current_state || 'neutral',
        trend: wellnessMetrics.trend || 'stable'
      };
      setWellnessData(metricsData);
      setLoading(false);
      setError(null); // Always clear errors when data is provided via props
      return;
    }
    
    // Only fetch from wellness endpoint if metrics not provided as props
    // This prevents duplicate API calls when Dashboard already has the data
    loadWellnessData();
    
    // Refresh data every 10 minutes (increased from 5 to reduce API calls)
    const interval = setInterval(loadWellnessData, 10 * 60 * 1000);
    return () => clearInterval(interval);
  }, [wellnessMetrics]);

  const loadWellnessData = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await axios.get(`${API_BASE_URL}/api/wellness`, {
        params: {
          max_notes: 50
        }
      });
      setWellnessData(response.data);
      setError(null); // Clear error on success
    } catch (err) {
      console.error('Failed to load wellness data:', err);
      // Only show error if we don't already have data (to avoid showing error when data exists)
      if (err.response?.status !== 401 && !wellnessData) {
        setError('Failed to load wellness insights');
      }
      // Only set default data if we don't have existing data
      if (!wellnessData) {
        setWellnessData({
          wellness_score: 50,
          completion_rate: 0,
          peak_productivity_hours: 'No data available',
          insights: ['Connect your Notion account to see wellness insights'],
          engagement_score: 0,
          active_days: 0,
          total_notes: 0,
          current_state: 'neutral',
          trend: 'stable'
        });
      }
    } finally {
      setLoading(false);
    }
  };

  const getMoodFromState = (state) => {
    const states = {
      'energized': { mood: 'energized', emoji: '⚡', color: 'text-green-600' },
      'focused': { mood: 'focused', emoji: '🎯', color: 'text-ocean-600' },
      'calm': { mood: 'calm', emoji: '😌', color: 'text-blue-600' },
      'stressed': { mood: 'stressed', emoji: '😰', color: 'text-yellow-600' },
      'overwhelmed': { mood: 'overwhelmed', emoji: '😓', color: 'text-orange-600' },
      'neutral': { mood: 'neutral', emoji: '😊', color: 'text-gray-600' }
    };
    return states[state] || states['neutral'];
  };

  const getMoodColor = (score) => {
    if (score >= 80) return 'text-green-600';
    if (score >= 60) return 'text-ocean-600';
    if (score >= 40) return 'text-yellow-600';
    return 'text-orange-600';
  };

  const getTrendIcon = (trend) => {
    if (trend === 'improving') return '📈';
    if (trend === 'stable') return '➡️';
    return '📉';
  };

  const getTrendText = (trend) => {
    if (trend === 'improving') return 'Improving';
    if (trend === 'stable') return 'Stable';
    return 'Needs Attention';
  };

  if (loading && !wellnessData) {
    return (
      <div className="glass-card p-6 h-full">
        <h3 className="text-xl font-semibold text-ocean-800 mb-6">Wellness Insights</h3>
        <div className="animate-pulse space-y-4">
          <div className="h-32 bg-ocean-100 rounded-lg"></div>
          <div className="h-20 bg-ocean-100 rounded-lg"></div>
        </div>
      </div>
    );
  }

  const data = wellnessData || {
    wellness_score: 50,
    completion_rate: 0,
    peak_productivity_hours: 'No data available',
    insights: ['Connect your Notion account to see wellness insights'],
    engagement_score: 0,
    active_days: 0,
    total_notes: 0,
    current_state: 'neutral',
    trend: 'stable'
  };

  const moodInfo = getMoodFromState(data.current_state || 'neutral');

  return (
    <div className="glass-card p-6 h-full">
      <h3 className="text-xl font-semibold text-ocean-800 mb-6">Wellness Insights</h3>

      {/* Only show error if we have no data at all */}
      {error && (!wellnessData || !wellnessData.total_notes) && (
        <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded-lg text-sm">
          {error}
        </div>
      )}

      {/* Current State */}
      <div className="mb-6 text-center">
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: 'spring', bounce: 0.5 }}
          className="text-6xl mb-3"
        >
          {moodInfo.emoji}
        </motion.div>
        <p className="text-sm text-ocean-600 mb-2">Current State</p>
        <p className="text-2xl font-bold capitalize text-ocean-800">{moodInfo.mood}</p>
      </div>

      {/* Wellness Score */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-ocean-700">Wellness Score</span>
          <span className={`text-lg font-bold ${getMoodColor(data.wellness_score || 50)}`}>
            {typeof data.wellness_score === 'number' ? data.wellness_score.toFixed(1) : '50.0'}
          </span>
        </div>
        <div className="w-full h-3 bg-ocean-100 rounded-full overflow-hidden">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${data.wellness_score || 50}%` }}
            transition={{ duration: 1, ease: 'easeOut' }}
            className={`h-full rounded-full ${
              (data.wellness_score || 50) >= 80 ? 'bg-gradient-to-r from-green-400 to-green-600' :
              (data.wellness_score || 50) >= 60 ? 'bg-gradient-to-r from-ocean-400 to-ocean-600' :
              (data.wellness_score || 50) >= 40 ? 'bg-gradient-to-r from-yellow-400 to-yellow-600' :
              'bg-gradient-to-r from-orange-400 to-orange-600'
            }`}
          ></motion.div>
        </div>
        <p className="text-xs text-ocean-500 mt-1 text-right flex items-center justify-end space-x-1">
          <span>{getTrendIcon(data.trend)}</span>
          <span>{getTrendText(data.trend)}</span>
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className="bg-white/50 rounded-xl p-3 text-center">
          <p className="text-xl font-bold text-ocean-700">{typeof data.engagement_score === 'number' ? data.engagement_score.toFixed(0) : 0}</p>
          <p className="text-xs text-ocean-600 mt-1">Engagement</p>
        </div>
        <div className="bg-white/50 rounded-xl p-3 text-center">
          <p className="text-xl font-bold text-ocean-700">{data.total_notes || 0}</p>
          <p className="text-xs text-ocean-600 mt-1">Notes This Week</p>
        </div>
        <div className="bg-white/50 rounded-xl p-3 text-center">
          <p className="text-xl font-bold text-ocean-700">{data.active_days || 0}</p>
          <p className="text-xs text-ocean-600 mt-1">Active Days</p>
        </div>
        <div className="bg-white/50 rounded-xl p-3 text-center">
          <p className="text-xl font-bold text-ocean-700">{typeof data.completion_rate === 'number' ? data.completion_rate.toFixed(0) : 0}%</p>
          <p className="text-xs text-ocean-600 mt-1">Completion</p>
        </div>
      </div>

      {/* Peak Productivity Hours */}
      {data.peak_productivity_hours && data.peak_productivity_hours !== 'No data available' && (
        <div className="mb-4 bg-white/50 rounded-xl p-3">
          <p className="text-xs text-ocean-600 mb-1">Peak Productivity Hours</p>
          <p className="text-sm font-semibold text-ocean-800">{data.peak_productivity_hours}</p>
        </div>
      )}

      {/* AI Insights */}
      <div className="mt-4">
        <h4 className="text-sm font-semibold text-ocean-700 mb-3">AI Insights</h4>
        {data.insights && data.insights.length > 0 ? (
          <div className="bg-white/30 rounded-lg p-3">
            <InsightsDisplay insights={data.insights} />
          </div>
        ) : (
          <p className="text-xs text-ocean-500">No insights available. Connect Notion to see wellness insights.</p>
        )}
      </div>
    </div>
  );
};

export default MoodSummary;
