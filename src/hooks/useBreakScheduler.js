import { useState, useEffect } from 'react';
import { useApi } from './useApi';

/**
 * Break scheduling hook - manages break recommendations based on calendar
 * TODO: Connect to backend /breaks/schedule endpoint
 */
export const useBreakScheduler = () => {
  const [upcomingBreak, setUpcomingBreak] = useState(null);
  const [breakHistory, setBreakHistory] = useState([]);
  const { data: scheduleData, fetchData: fetchSchedule } = useApi('/breaks/schedule');

  useEffect(() => {
    loadBreakSchedule();
    
    // Refresh schedule every 5 minutes
    const interval = setInterval(loadBreakSchedule, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  const loadBreakSchedule = async () => {
    try {
      // TODO: API Call - Get recommended break times from backend
      // const schedule = await fetchSchedule();
      // setUpcomingBreak(schedule.nextBreak);
      
      // Mock data for development
      const mockBreak = {
        id: 'break-1',
        scheduledTime: new Date(Date.now() + 15 * 60 * 1000), // 15 min from now
        duration: 5,
        type: 'guided_meditation',
        reason: 'After back-to-back meetings',
      };
      setUpcomingBreak(mockBreak);
    } catch (error) {
      console.error('Failed to load break schedule:', error);
    }
  };

  const startBreak = async (breakId) => {
    try {
      // TODO: API Call - Log break start to backend
      // await apiClient.post(`/breaks/${breakId}/start`);
      console.log('Break started:', breakId);
    } catch (error) {
      console.error('Failed to start break:', error);
    }
  };

  const completeBreak = async (breakId, feedback = {}) => {
    try {
      // TODO: API Call - Log break completion and feedback
      // await apiClient.post(`/breaks/${breakId}/complete`, feedback);
      
      setBreakHistory(prev => [...prev, { id: breakId, completedAt: new Date(), ...feedback }]);
      loadBreakSchedule(); // Refresh schedule
    } catch (error) {
      console.error('Failed to complete break:', error);
    }
  };

  return {
    upcomingBreak,
    breakHistory,
    loadBreakSchedule,
    startBreak,
    completeBreak,
  };
};
