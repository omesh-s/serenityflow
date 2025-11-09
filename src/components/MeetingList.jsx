import React from 'react';
import { IoCalendarOutline, IoTimeOutline, IoPeopleOutline } from 'react-icons/io5';
import { useTimezone } from '../hooks/useTimezone.jsx';

/**
 * Meeting List Component - displays upcoming meetings from Google Calendar
 * Connects to backend /api/serenity/schedule endpoint
 */
const MeetingList = ({ loading, events = [], error }) => {
  const { timezone } = useTimezone();
  
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


  if (loading) {
    return (
      <div className="glass-card p-6">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-xl font-semibold text-ocean-800 flex items-center space-x-2">
            <IoCalendarOutline size={24} />
            <span>Upcoming Meetings</span>
          </h3>
        </div>
        <div className="animate-pulse space-y-4">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-20 bg-ocean-100 rounded-lg"></div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="glass-card p-6">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-xl font-semibold text-ocean-800 flex items-center space-x-2">
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
        <h3 className="text-xl font-semibold text-ocean-800 flex items-center space-x-2">
          <IoCalendarOutline size={24} />
          <span>Upcoming Meetings</span>
        </h3>
        <span className="text-sm text-ocean-600">{events.length} upcoming</span>
      </div>

      <div className="space-y-3">
        {events.length === 0 ? (
          <div className="text-center py-8 text-ocean-500">
            <p>No meetings scheduled. Enjoy your free time! 🎉</p>
            <p className="text-sm mt-2">Connect your Google Calendar to see your events here.</p>
          </div>
        ) : (
          events.map((event) => (
            <div
              key={event.id}
              className="p-4 bg-white/50 hover:bg-white/80 rounded-xl transition-all cursor-pointer border border-ocean-100 hover:border-ocean-300 hover:shadow-md"
              onClick={() => event.htmlLink && window.open(event.htmlLink, '_blank')}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <h4 className="font-semibold text-ocean-800 mb-2">{event.summary || 'No Title'}</h4>
                  
                  <div className="flex flex-wrap gap-4 text-sm text-ocean-600">
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
                    <div className="mt-2 text-xs text-ocean-500">📍 {event.location}</div>
                  )}
                  
                  {event.description && (
                    <div className="mt-2 text-xs text-ocean-400 line-clamp-2">{event.description}</div>
                  )}
                </div>

                <div className="ml-4 text-right">
                  <div className="text-xs text-ocean-500 mb-1">{formatDate(event.start)}</div>
                  <span className="inline-block px-3 py-1 bg-ocean-100 text-ocean-700 text-xs font-medium rounded-full">
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
