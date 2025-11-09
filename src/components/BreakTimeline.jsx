import React, { useMemo } from 'react';
import { motion } from 'framer-motion';

/**
 * Break Timeline Component - visualizes recommended break windows and calendar events
 * Displays calendar events and AI-generated break suggestions
 */
const BreakTimeline = ({ events = [], breakSuggestions = [], loading = false }) => {
  // Combine events and break suggestions into a timeline
  const timeSlots = useMemo(() => {
    const slots = [];
    const now = new Date();
    
    // Add events as meetings
    events.forEach(event => {
      const start = new Date(event.start);
      const end = new Date(event.end);
      const duration = Math.round((end - start) / 60000); // duration in minutes
      
      if (end > now) { // Only show future events
        slots.push({
          time: start,
          type: 'meeting',
          duration: duration,
          title: event.summary || 'Meeting',
          location: event.location,
          attendees: event.attendees,
          htmlLink: event.htmlLink,
        });
      }
    });
    
    // Add break suggestions
    breakSuggestions.forEach(breakSuggestion => {
      const breakTime = new Date(breakSuggestion.time);
      
      if (breakTime > now) { // Only show future breaks
        slots.push({
          time: breakTime,
          type: 'break',
          duration: breakSuggestion.duration,
          title: `${breakSuggestion.activity.charAt(0).toUpperCase() + breakSuggestion.activity.slice(1)} Break`,
          activity: breakSuggestion.activity,
          reason: breakSuggestion.reason,
          recommended: true,
        });
      }
    });
    
    // Sort by time
    slots.sort((a, b) => a.time - b.time);
    
    // Limit to next 10 items
    return slots.slice(0, 10);
  }, [events, breakSuggestions]);
  
  const formatTime = (date) => {
    return date.toLocaleTimeString('en-US', { 
      hour: 'numeric', 
      minute: '2-digit', 
      hour12: true 
    });
  };
  
  const formatDate = (date) => {
    const today = new Date();
    const tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 1);
    
    if (date.toDateString() === today.toDateString()) {
      return 'Today';
    } else if (date.toDateString() === tomorrow.toDateString()) {
      return 'Tomorrow';
    } else {
      return date.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
    }
  };

  const getSlotColor = (type, recommended) => {
    if (recommended) return 'bg-gradient-to-r from-serenity to-serenity-dark';
    switch (type) {
      case 'meeting': return 'bg-ocean-500';
      case 'break': return 'bg-ocean-200';
      case 'work': return 'bg-ocean-100';
      default: return 'bg-gray-200';
    }
  };

  const getSlotIcon = (type) => {
    switch (type) {
      case 'meeting': return '📅';
      case 'break': return '🧘';
      case 'work': return '💻';
      default: return '•';
    }
  };

  if (loading) {
    return (
      <div className="glass-card p-6">
        <h3 className="text-xl font-semibold text-ocean-800 mb-6">Today's Flow & Break Windows</h3>
        <div className="animate-pulse space-y-4">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-16 bg-ocean-100 rounded-lg"></div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="glass-card p-6">
      <h3 className="text-xl font-semibold text-ocean-800 mb-6">
        Today's Flow & Break Windows
        {timeSlots.length > 0 && (
          <span className="ml-2 text-sm font-normal text-ocean-500">
            ({timeSlots.length} {timeSlots.length === 1 ? 'item' : 'items'})
          </span>
        )}
      </h3>

      {timeSlots.length === 0 ? (
        <div className="text-center py-8 text-ocean-500">
          <p>No upcoming events or breaks scheduled.</p>
          <p className="text-sm mt-2">Connect your Google Calendar to see your schedule and get break recommendations.</p>
        </div>
      ) : (
        <>
          <div className="relative">
            {/* Timeline line */}
            <div className="absolute left-6 top-0 bottom-0 w-0.5 bg-ocean-200"></div>

            {/* Time slots */}
            <div className="space-y-3">
              {timeSlots.map((slot, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.05 }}
                  className="relative flex items-start"
                >
                  {/* Time marker */}
                  <div className="w-24 flex-shrink-0 pt-1 pl-10">
                    <div className="text-sm font-medium text-ocean-600">{formatTime(slot.time)}</div>
                    <div className="text-xs text-ocean-400">{formatDate(slot.time)}</div>
                  </div>

                  {/* Timeline dot */}
                  <div className={`absolute left-[19px] top-2 w-3 h-3 rounded-full z-10 ${
                    slot.recommended ? 'bg-serenity-dark animate-pulse' : 'bg-ocean-400'
                  }`}></div>

                  {/* Slot card */}
                  <div className="flex-1 ml-4">
                    <div 
                      className={`${getSlotColor(slot.type, slot.recommended)} rounded-lg px-4 py-3 cursor-pointer transition-transform hover:scale-[1.02] ${
                        slot.recommended ? 'shadow-lg border-2 border-serenity-dark' : 'shadow-sm'
                      } ${slot.htmlLink ? 'hover:shadow-md' : ''}`}
                      onClick={() => slot.htmlLink && window.open(slot.htmlLink, '_blank')}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <div className="flex items-center space-x-2">
                            <span>{getSlotIcon(slot.type)}</span>
                            <span className={`font-medium ${
                              slot.type === 'meeting' ? 'text-white' : 
                              slot.recommended ? 'text-ocean-800' : 
                              'text-ocean-700'
                            }`}>
                              {slot.title}
                            </span>
                          </div>
                          {slot.reason && (
                            <p className="text-xs text-ocean-600 mt-1 ml-7">{slot.reason}</p>
                          )}
                          {slot.location && (
                            <p className="text-xs text-ocean-400 mt-1 ml-7">📍 {slot.location}</p>
                          )}
                          {slot.attendees > 0 && (
                            <p className="text-xs text-ocean-400 mt-1 ml-7">👥 {slot.attendees} attendee{slot.attendees !== 1 ? 's' : ''}</p>
                          )}
                        </div>
                        <span className={`text-xs font-medium ml-2 ${
                          slot.type === 'meeting' ? 'text-white/90' : 
                          'text-ocean-600'
                        }`}>
                          {slot.duration} min
                        </span>
                      </div>
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          </div>

          <div className="mt-6 pt-6 border-t border-ocean-200">
            <div className="flex items-center justify-center space-x-6 text-sm flex-wrap gap-2">
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 rounded-full bg-ocean-500"></div>
                <span className="text-ocean-600">Meeting</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 rounded-full bg-gradient-to-r from-serenity to-serenity-dark"></div>
                <span className="text-ocean-600">Recommended Break</span>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default BreakTimeline;
