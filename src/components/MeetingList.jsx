import React, { useEffect, useRef } from 'react';
import { IoCalendarOutline, IoTimeOutline, IoPeopleOutline } from 'react-icons/io5';
import { useTimezone } from '../hooks/useTimezone.jsx';
import { useTheme } from '../hooks/useTheme.jsx';

/**
 * Meeting List Component - displays upcoming meetings from Google Calendar
 * Connects to backend /api/serenity/schedule endpoint
 */
const MeetingList = ({ loading, events = [], error, onMeetingEnd }) => {
  const { timezone } = useTimezone();
  const { themeColors } = useTheme();
  
  const formatTime = (dateString) => {
    const date = new Date(dateString);
    try {
      return new Intl.DateTimeFormat('en-US', {
        timeZone: timezone,
        hour: 'numeric',
        minute: '2-digit',
        hour12: true
      }).format(date);
    } catch (e) {
      return date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true });
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    const today = new Date();
    const tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 1);
    
    try {
      const formatter = new Intl.DateTimeFormat('en-US', {
        timeZone: timezone,
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
      });
      
      const dateStr = formatter.format(date);
      const todayStr = formatter.format(today);
      const tomorrowStr = formatter.format(tomorrow);
      
      if (dateStr === todayStr) {
        return 'Today';
      } else if (dateStr === tomorrowStr) {
        return 'Tomorrow';
      } else {
        return new Intl.DateTimeFormat('en-US', {
          timeZone: timezone,
          weekday: 'short',
          month: 'short',
          day: 'numeric'
        }).format(date);
      }
    } catch (e) {
      if (date.toDateString() === today.toDateString()) {
        return 'Today';
      } else if (date.toDateString() === tomorrow.toDateString()) {
        return 'Tomorrow';
      } else {
        return date.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
      }
    }
  };

  const getTimeUntil = (dateString) => {
    const date = new Date(dateString);
    const now = new Date();
    const minutes = Math.round((date - now) / 60000);
    
    if (minutes < 0) {
      return 'Past';
    } else if (minutes < 60) {
      return `in ${minutes}m`;
    } else {
      const hours = Math.floor(minutes / 60);
      const mins = minutes % 60;
      return `in ${hours}h ${mins > 0 ? mins + 'm' : ''}`;
    }
  };

  // Returns minutes until the given end time (positive if in the future, <= 0 if passed)
  // This helper is useful when the parent component wants to take action once a meeting ends.
  // It returns `null` if the date couldn't be parsed.
  const minutesUntilEnd = (endDateString) => {
    const end = new Date(endDateString);
    const now = new Date();
    if (isNaN(end.getTime())) return null;
    return Math.round((end - now) / 60000);
  };

  // Track which meetings we've already used as triggers so we don't call the callback repeatedly
  const triggeredMeetingIdsRef = useRef(new Set());

  // Periodically check events and call `onMeetingEnd(event)` once when an event has passed.
  // Behavior notes (intentionally similar to BreakTimeline):
  // - Runs immediately and then polls every 15s while the component is mounted.
  // - Uses a Set to avoid duplicate triggers for the same event id.
  // - If `onMeetingEnd` is not provided, it logs the ended meeting as a fallback.
  useEffect(() => {
    if (!events || events.length === 0) {
      triggeredMeetingIdsRef.current.clear();
      return;
    }

    const checkFn = () => {
      const currentIds = new Set(events.map(e => e.id || `${e.summary || 'evt'}_${new Date(e.start).getTime()}`));

      events.forEach(event => {
        const id = event.id || `${event.summary || 'evt'}_${new Date(event.start).getTime()}`;
        const mins = minutesUntilEnd(event.end);

        if (mins === null) return; // couldn't parse end time

        // Trigger once when meeting has passed (end time <= now)
        if (mins <= 0 && !triggeredMeetingIdsRef.current.has(id)) {
          try {
            if (typeof onMeetingEnd === 'function') {
              onMeetingEnd(event);
            } else {
              // Fallback behavior: log the ended meeting so developer can wire a handler
              // eslint-disable-next-line no-console
              console.log('[MeetingList] Meeting ended trigger:', event);
            }
          } catch (err) {
            // swallow callback errors - they should be handled by the caller
            // eslint-disable-next-line no-console
            console.error('onMeetingEnd handler threw', err);
          }

          triggeredMeetingIdsRef.current.add(id);
        }
      });

      // Cleanup any triggered IDs that are no longer in the current events list
      for (const id of Array.from(triggeredMeetingIdsRef.current)) {
        if (!currentIds.has(id)) triggeredMeetingIdsRef.current.delete(id);
      }
    };

    checkFn();
    const interval = setInterval(checkFn, 15000);
    return () => clearInterval(interval);
  }, [events, onMeetingEnd]);


  if (loading) {
    return (
      <div className="glass-card p-6">
        <div className="flex items-center justify-between mb-6">
          <h3 
            className="text-xl font-semibold flex items-center space-x-2"
            style={themeColors ? { color: themeColors.text } : {}}
          >
            <IoCalendarOutline size={24} />
            <span>Upcoming Meetings</span>
          </h3>
        </div>
        <div className="animate-pulse space-y-4">
          {[1, 2, 3].map(i => (
            <div 
              key={i} 
              className="h-20 rounded-lg"
              style={themeColors ? { backgroundColor: themeColors.primaryLight + '40' } : {}}
            ></div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="glass-card p-6">
        <div className="flex items-center justify-between mb-6">
          <h3 
            className="text-xl font-semibold flex items-center space-x-2"
            style={themeColors ? { color: themeColors.text } : {}}
          >
            <IoCalendarOutline size={24} />
            <span>Upcoming Meetings</span>
          </h3>
        </div>
        <div className="text-center py-8 text-red-500">
          <p>{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="glass-card p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 
          className="text-xl font-semibold flex items-center space-x-2"
          style={themeColors ? { color: themeColors.text } : {}}
        >
          <IoCalendarOutline size={24} />
          <span>Upcoming Meetings</span>
        </h3>
        <span 
          className="text-sm"
          style={themeColors ? { color: themeColors.textLight } : {}}
        >
          {events.length} upcoming
        </span>
      </div>

      <div className="space-y-3">
        {events.length === 0 ? (
          <div 
            className="text-center py-8"
            style={themeColors ? { color: themeColors.textLight } : {}}
          >
            <p>No meetings scheduled. Enjoy your free time! 🎉</p>
            <p className="text-sm mt-2">Connect your Google Calendar to see your events here.</p>
          </div>
        ) : (
          events.map((event) => (
            <div
              key={event.id}
              className="p-4 bg-white/50 hover:bg-white/80 rounded-xl transition-all cursor-pointer border hover:shadow-md"
              style={{
                borderColor: themeColors ? `${themeColors.primaryLight}80` : '#bae6fd',
              }}
              onMouseEnter={(e) => {
                if (themeColors) {
                  e.currentTarget.style.borderColor = themeColors.primary;
                }
              }}
              onMouseLeave={(e) => {
                if (themeColors) {
                  e.currentTarget.style.borderColor = `${themeColors.primaryLight}80`;
                }
              }}
              onClick={() => event.htmlLink && window.open(event.htmlLink, '_blank')}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <h4 
                    className="font-semibold mb-2"
                    style={themeColors ? { color: themeColors.text } : {}}
                  >
                    {event.summary || 'No Title'}
                  </h4>
                  
                  <div 
                    className="flex flex-wrap gap-4 text-sm"
                    style={themeColors ? { color: themeColors.textLight } : {}}
                  >
                    <div className="flex items-center space-x-1">
                      <IoTimeOutline />
                      <span>{formatTime(event.start)} - {formatTime(event.end)}</span>
                    </div>
                    {event.attendees > 0 && (
                      <div className="flex items-center space-x-1">
                        <IoPeopleOutline />
                        <span>{event.attendees} attendee{event.attendees !== 1 ? 's' : ''}</span>
                      </div>
                    )}
                  </div>
                  
                  {event.location && (
                    <div 
                      className="mt-2 text-xs"
                      style={themeColors ? { color: themeColors.textLight } : {}}
                    >
                      📍 {event.location}
                    </div>
                  )}
                  
                  {event.description && (
                    <div 
                      className="mt-2 text-xs line-clamp-2"
                      style={themeColors ? { color: themeColors.textLight + 'CC' } : {}}
                    >
                      {event.description}
                    </div>
                  )}
                </div>

                <div className="ml-4 text-right">
                  <div 
                    className="text-xs mb-1"
                    style={themeColors ? { color: themeColors.textLight } : {}}
                  >
                    {formatDate(event.start)}
                  </div>
                  <span 
                    className="inline-block px-3 py-1 text-xs font-medium rounded-full"
                    style={themeColors ? {
                      backgroundColor: themeColors.primaryLight + '40',
                      color: themeColors.text,
                    } : {}}
                  >
                    {getTimeUntil(event.start)}
                  </span>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default MeetingList;
