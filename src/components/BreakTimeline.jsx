import React, { useMemo, useState, useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import { IoCreateOutline, IoAddOutline } from 'react-icons/io5';
import BreakEditor from './BreakEditor';
import { getBreakType } from '../utils/breakTypes';
import axios from 'axios';
import { API_BASE_URL } from '../utils/constants';
import { useTimezone } from '../hooks/useTimezone.jsx';
import { useTheme } from '../hooks/useTheme.jsx';

/**
 * Break Timeline Component - visualizes recommended break windows and calendar events
 * Displays calendar events and AI-generated break suggestions with editing capabilities
 */
const BreakTimeline = ({ events = [], breakSuggestions = [], loading = false, onBreaksUpdate, onMeetingEnd }) => {
  const [editingBreak, setEditingBreak] = useState(null);
  const [addingBreak, setAddingBreak] = useState(false);
  const [localBreakUpdates, setLocalBreakUpdates] = useState({}); // Track local time updates
  const { timezone } = useTimezone();
  const { themeColors } = useTheme();
  
  // Combine events and break suggestions into a timeline
  const timeSlots = useMemo(() => {
    const slots = [];
    const now = new Date();
    
    // Helper to get UTC timestamp for accurate sorting
    // Always use UTC for sorting to ensure breaks and meetings are in correct order
    const getSortTime = (date) => {
      if (!date) return 0;
      const d = date instanceof Date ? date : new Date(date);
      if (isNaN(d.getTime())) return 0;
      // getTime() returns UTC timestamp in milliseconds - perfect for sorting
      return d.getTime();
    };
    
    // Parse and add events as meetings
    const parsedEvents = [];
    events.forEach(event => {
      const start = new Date(event.start);
      const end = new Date(event.end);
      const duration = Math.round((end - start) / 60000); // duration in minutes
      
      if (end > now) { // Only show future events
        const eventSlot = {
          time: start,
          sortTime: getSortTime(start), // Use UTC timestamp for sorting
          endTime: end,
          endSortTime: getSortTime(end),
          type: 'meeting',
          duration: duration,
          title: event.summary || 'Meeting',
          location: event.location,
          attendees: event.attendees,
          htmlLink: event.htmlLink,
        };
        slots.push(eventSlot);
        parsedEvents.push(eventSlot);
      }
    });
    
    // Add break suggestions - show all future breaks (backend validates placement)
    // Use a Set to track break IDs and prevent duplicates
    const seenBreakIds = new Set();
    breakSuggestions.forEach(breakSuggestion => {
      // Use stable ID from backend, or generate one based on time (rounded to minute)
      const breakTimeRaw = new Date(breakSuggestion.time);
      const breakTimeRounded = new Date(breakTimeRaw.getFullYear(), breakTimeRaw.getMonth(), breakTimeRaw.getDate(), 
                                        breakTimeRaw.getHours(), breakTimeRaw.getMinutes(), 0);
      const breakId = breakSuggestion.id || `break_${breakTimeRounded.getTime()}`;
      
      // Skip if we've already seen this break (prevent duplicates)
      if (seenBreakIds.has(breakId)) {
        return;
      }
      seenBreakIds.add(breakId);
      
      // Apply local time update if available
      const breakTimeStr = localBreakUpdates[breakId] || breakSuggestion.time;
      const breakTime = new Date(breakTimeStr);
      const breakType = getBreakType(breakSuggestion.activity);
      
      // Only show future breaks
      if (breakTime > now) {
        slots.push({
          id: breakId,
          time: breakTime,
          sortTime: getSortTime(breakTime), // Use UTC timestamp for sorting
          type: 'break',
          duration: breakSuggestion.duration,
          title: breakType.name,
          activity: breakSuggestion.activity,
          reason: breakSuggestion.reason,
          description: breakSuggestion.description || breakType.description,
          icon: breakSuggestion.icon || breakType.icon,
          color: breakType.color,
          recommended: true,
          breakData: { ...breakSuggestion, time: breakTimeStr }, // Include updated time in breakData
        });
      }
    });
    
    // Sort all slots by UTC timestamp (sortTime) to ensure correct chronological order
    // This ensures breaks and meetings are mixed correctly regardless of timezone
    slots.sort((a, b) => (a.sortTime || a.time.getTime()) - (b.sortTime || b.time.getTime()));
    
    // Limit to next 20 items to show more context
    return slots.slice(0, 20);
  }, [events, breakSuggestions, timezone, localBreakUpdates]);
  
  const formatTime = (date) => {
    if (!date) return '';
    const d = date instanceof Date ? date : new Date(date);
    if (isNaN(d.getTime())) return '';
    
    // Format in user's selected timezone
    try {
      return new Intl.DateTimeFormat('en-US', {
        timeZone: timezone,
        hour: 'numeric',
        minute: '2-digit',
        hour12: true
      }).format(d);
    } catch (e) {
      // Fallback to local timezone if timezone is invalid
      return d.toLocaleTimeString('en-US', {
        hour: 'numeric',
        minute: '2-digit',
        hour12: true
      });
    }
  };
  
  const formatDate = (date) => {
    if (!date) return '';
    const d = date instanceof Date ? date : new Date(date);
    if (isNaN(d.getTime())) return '';
    
    const today = new Date();
    const tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 1);
    
    // Get date in user's timezone for comparison
    try {
      const formatter = new Intl.DateTimeFormat('en-US', {
        timeZone: timezone,
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
      });
      
      const dateParts = formatter.formatToParts(d);
      const year = parseInt(dateParts.find(p => p.type === 'year').value);
      const month = parseInt(dateParts.find(p => p.type === 'month').value) - 1;
      const day = parseInt(dateParts.find(p => p.type === 'day').value);
      const userDate = new Date(year, month, day);
      
      const todayParts = formatter.formatToParts(today);
      const todayYear = parseInt(todayParts.find(p => p.type === 'year').value);
      const todayMonth = parseInt(todayParts.find(p => p.type === 'month').value) - 1;
      const todayDay = parseInt(todayParts.find(p => p.type === 'day').value);
      const userToday = new Date(todayYear, todayMonth, todayDay);
      
      const tomorrowParts = formatter.formatToParts(tomorrow);
      const tomorrowYear = parseInt(tomorrowParts.find(p => p.type === 'year').value);
      const tomorrowMonth = parseInt(tomorrowParts.find(p => p.type === 'month').value) - 1;
      const tomorrowDay = parseInt(tomorrowParts.find(p => p.type === 'day').value);
      const userTomorrow = new Date(tomorrowYear, tomorrowMonth, tomorrowDay);
      
      if (userDate.getTime() === userToday.getTime()) {
        return 'Today';
      } else if (userDate.getTime() === userTomorrow.getTime()) {
        return 'Tomorrow';
      } else {
        return new Intl.DateTimeFormat('en-US', {
          timeZone: timezone,
          weekday: 'short',
          month: 'short',
          day: 'numeric'
        }).format(d);
      }
    } catch (e) {
      // Fallback to local timezone
      if (d.toDateString() === today.toDateString()) {
        return 'Today';
      } else if (d.toDateString() === tomorrow.toDateString()) {
        return 'Tomorrow';
      } else {
        return d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
      }
    }
  };

  const getSlotColor = (type, recommended, color) => {
    if (type === 'break' && recommended) {
      return 'bg-gradient-to-r from-serenity to-serenity-dark';
    }
    if (type === 'break') {
      // Use a light version of the break type color
      return 'bg-ocean-200';
    }
    switch (type) {
      case 'meeting': 
        // Use theme primary color for meetings
        return ''; // Return empty string, we'll use inline style
      case 'work': 
        // Use theme light color for work
        return ''; // Return empty string, we'll use inline style
      default: return 'bg-gray-200';
    }
  };
  
  const getMeetingStyle = (type) => {
    if (type === 'meeting' && themeColors) {
      return {
        backgroundColor: themeColors.primary,
        color: '#ffffff',
      };
    }
    if (type === 'work' && themeColors) {
      return {
        backgroundColor: themeColors.primaryLight + '40', // Add transparency
        color: themeColors.text,
      };
    }
    return {};
  };

  const getSlotStyle = (type, color) => {
    if (type === 'break' && color) {
      // Use inline style for dynamic colors
      const rgb = hexToRgb(color);
      return {
        backgroundColor: `rgba(${rgb}, 0.2)`,
        borderColor: color,
        borderWidth: '2px',
      };
    }
    return {};
  };

  const hexToRgb = (hex) => {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return result 
      ? `${parseInt(result[1], 16)}, ${parseInt(result[2], 16)}, ${parseInt(result[3], 16)}`
      : '14, 165, 233';
  };

  // Returns minutes until the given end time (positive if in the future, <= 0 if passed)
  const minutesUntilEnd = (endDateString) => {
    const end = new Date(endDateString);
    const now = new Date();
    if (isNaN(end.getTime())) return null;
    return Math.round((end - now) / 60000);
  };

  // Track which meetings we've already used as triggers so we don't call the callback repeatedly
  const triggeredMeetingIdsRef = useRef(new Set());

  // Periodically check events and call `onMeetingEnd(event)` once when an event has passed
  useEffect(() => {
    if (!events || events.length === 0) {
      // Clean up stored IDs if there are no events
      triggeredMeetingIdsRef.current.clear();
      return;
    }

    const checkFn = () => {
      const now = new Date();
      // Build a set of current event ids to allow cleanup of stale triggered ids
      const currentIds = new Set(events.map(e => e.id || `${e.summary || 'evt'}_${new Date(e.start).getTime()}`));

      events.forEach(event => {
        const id = event.id || `${event.summary || 'evt'}_${new Date(event.start).getTime()}`;
        const mins = minutesUntilEnd(event.end);

        // If minutes is null we couldn't parse the end time - skip
        if (mins === null) return;

        // Trigger once when meeting has passed (end time <= now)
        if (mins <= 0 && !triggeredMeetingIdsRef.current.has(id)) {
          try {
            if (typeof onMeetingEnd === 'function') {
              onMeetingEnd(event);
            } else {
              // Fallback behavior: log the ended meeting so developer can wire a handler
              // eslint-disable-next-line no-console
              console.log('[BreakTimeline] Meeting ended trigger:', event);
            }
          } catch (err) {
            // swallow callback errors - they should be handled by the caller
            // eslint-disable-next-line no-console
            console.error('onMeetingEnd handler threw', err);
          }

          triggeredMeetingIdsRef.current.add(id);
        }
      });

      // Remove any triggered IDs that are no longer in the events list
      for (const id of Array.from(triggeredMeetingIdsRef.current)) {
        if (!currentIds.has(id)) triggeredMeetingIdsRef.current.delete(id);
      }
    };

    // Run immediately, then poll every 15 seconds while component is mounted
    checkFn();
    const interval = setInterval(checkFn, 15000);
    return () => clearInterval(interval);
  }, [events, onMeetingEnd]);

  const getSlotIcon = (type, icon) => {
    if (icon) return icon;
    switch (type) {
      case 'meeting': return '📅';
      case 'break': return '🧘';
      case 'work': return '💻';
      default: return '•';
    }
  };

  const handleBreakSave = async (breakData) => {
    try {
      // Save break customization via API
      await axios.post(`${API_BASE_URL}/api/breaks/customize`, {
        breaks: [breakData],
        user_id: "default", // In production, get from auth
      });
      
      // Clear local updates after save
      if (breakData.id) {
        setLocalBreakUpdates(prev => {
          const updated = { ...prev };
          delete updated[breakData.id];
          return updated;
        });
      }
      
      // Notify parent component to refresh breaks
      if (onBreaksUpdate) {
        onBreaksUpdate();
      }
      
      setEditingBreak(null);
      setAddingBreak(false);
    } catch (error) {
      console.error('Error saving break:', error);
      alert('Failed to save break. Please try again.');
    }
  };

  const handleBreakDelete = async (breakId) => {
    try {
      await axios.delete(`${API_BASE_URL}/api/breaks/${breakId}`, {
        params: { user_id: "default" }
      });
      
      if (onBreaksUpdate) {
        onBreaksUpdate();
      }
      
      setEditingBreak(null);
    } catch (error) {
      console.error('Error deleting break:', error);
      alert('Failed to delete break. Please try again.');
    }
  };

  const handleAddBreak = () => {
    // Find a good time slot (after next event or in a gap)
    const now = new Date();
    const nextEvent = events.find(e => new Date(e.start) > now);
    const defaultTime = nextEvent 
      ? new Date(new Date(nextEvent.end).getTime() + 5 * 60000) // 5 minutes after next event
      : new Date(now.getTime() + 30 * 60000); // 30 minutes from now
    
    setEditingBreak({
      time: defaultTime.toISOString(),
      duration: 10,
      activity: 'meditation',
      reason: '',
    });
    setAddingBreak(true);
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
      <div className="flex items-center justify-between mb-6">
        <h3 
          className="text-xl font-semibold"
          style={themeColors ? { color: themeColors.text } : {}}
        >
          Today's Flow & Break Windows
          {timeSlots.length > 0 && (
            <span 
              className="ml-2 text-sm font-normal"
              style={themeColors ? { color: themeColors.textLight } : {}}
            >
              ({timeSlots.length} {timeSlots.length === 1 ? 'item' : 'items'})
            </span>
          )}
        </h3>
        <button
          onClick={handleAddBreak}
          className="px-4 py-2 text-white rounded-lg transition-colors flex items-center space-x-2 text-sm"
          style={themeColors ? {
            backgroundColor: themeColors.primary,
          } : {
            backgroundColor: '#0ea5e9',
          }}
          onMouseEnter={(e) => {
            if (themeColors) {
              e.currentTarget.style.backgroundColor = themeColors.primaryDark;
            } else {
              e.currentTarget.style.backgroundColor = '#0284c7';
            }
          }}
          onMouseLeave={(e) => {
            if (themeColors) {
              e.currentTarget.style.backgroundColor = themeColors.primary;
            } else {
              e.currentTarget.style.backgroundColor = '#0ea5e9';
            }
          }}
        >
          <IoAddOutline size={18} />
          <span>Add Break</span>
        </button>
      </div>

      {timeSlots.length === 0 ? (
        <div 
          className="text-center py-8"
          style={themeColors ? { color: themeColors.textLight } : {}}
        >
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
                    <div 
                      className="text-sm font-medium"
                      style={themeColors ? { color: themeColors.text } : {}}
                    >
                      {formatTime(slot.time)}
                    </div>
                    <div 
                      className="text-xs"
                      style={themeColors ? { color: themeColors.textLight } : {}}
                    >
                      {formatDate(slot.time)}
                    </div>
                  </div>

                  {/* Timeline dot */}
                  <div 
                    className={`absolute left-[19px] top-2 w-3 h-3 rounded-full z-10 ${
                      slot.recommended ? 'bg-serenity-dark animate-pulse' : ''
                    }`}
                    style={slot.recommended ? {} : (slot.type === 'meeting' && themeColors ? {
                      backgroundColor: themeColors.primary
                    } : {})}
                  ></div>

                  {/* Slot card */}
                  <div className="flex-1 ml-4">
                    <div 
                      className={`${getSlotColor(slot.type, slot.recommended, slot.color)} rounded-lg px-4 py-3 transition-all ${
                        slot.recommended && slot.type === 'break' ? 'shadow-lg border-2 border-serenity-dark' : 'shadow-sm border-2'
                      } ${slot.htmlLink || slot.type === 'meeting' ? 'cursor-pointer hover:shadow-md' : ''} ${
                        slot.type === 'break' ? 'cursor-pointer' : ''
                      } ${slot.type === 'meeting' ? 'cursor-pointer' : ''}`}
                      style={{
                        ...(slot.type === 'break' ? getSlotStyle(slot.type, slot.color) : {}),
                        ...(slot.type === 'meeting' ? getMeetingStyle(slot.type) : {}),
                        ...(slot.type === 'work' ? getMeetingStyle(slot.type) : {}),
                        ...(slot.type === 'meeting' && themeColors ? {
                          borderColor: 'transparent',
                        } : {}),
                      }}
                      onMouseEnter={(e) => {
                        if (slot.type === 'meeting' && themeColors) {
                          e.currentTarget.style.backgroundColor = themeColors.primaryDark;
                        }
                      }}
                      onMouseLeave={(e) => {
                        if (slot.type === 'meeting' && themeColors) {
                          e.currentTarget.style.backgroundColor = themeColors.primary;
                        }
                      }}
                      onClick={() => {
                        if (slot.htmlLink) {
                          window.open(slot.htmlLink, '_blank');
                        } else if (slot.type === 'break') {
                          setEditingBreak(slot.breakData || slot);
                        } else if (slot.type === 'meeting' && slot.htmlLink) {
                          window.open(slot.htmlLink, '_blank');
                        }
                      }}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <div className="flex items-center space-x-2">
                            <span>{getSlotIcon(slot.type, slot.icon)}</span>
                            <span className={`font-medium ${
                              slot.type === 'meeting' ? 'text-white' : 
                              slot.recommended ? 'text-ocean-800' : 
                              'text-ocean-700'
                            }`}>
                              {slot.title}
                            </span>
                            {slot.type === 'break' && (
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setEditingBreak(slot.breakData || slot);
                                }}
                                className="ml-2 text-ocean-600 hover:text-ocean-800 transition-colors"
                                title="Edit break"
                              >
                                <IoCreateOutline size={16} />
                              </button>
                            )}
                          </div>
                          {slot.reason && (
                            <p className="text-xs text-ocean-600 mt-1 ml-7">{slot.reason}</p>
                          )}
                          {slot.description && (
                            <p className="text-xs text-ocean-500 mt-1 ml-7">{slot.description}</p>
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
                <div 
                  className="w-3 h-3 rounded-full"
                  style={themeColors ? { backgroundColor: themeColors.primary } : {}}
                ></div>
                <span style={themeColors ? { color: themeColors.text } : {}}>Meeting</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 rounded-full bg-gradient-to-r from-serenity to-serenity-dark"></div>
                <span style={themeColors ? { color: themeColors.text } : {}}>Recommended Break</span>
              </div>
            </div>
          </div>
        </>
      )}

      {/* Break Editor Modal */}
      {(editingBreak || addingBreak) && (
        <BreakEditor
          breakItem={editingBreak}
          onSave={handleBreakSave}
          onDelete={handleBreakDelete}
          onCancel={() => {
            setEditingBreak(null);
            setAddingBreak(false);
            // Clear local updates when canceling
            if (editingBreak?.id) {
              setLocalBreakUpdates(prev => {
                const updated = { ...prev };
                delete updated[editingBreak.id];
                return updated;
              });
            }
          }}
          onReset={async (breakId) => {
            try {
              // Delete the customization to reset to original break
              await axios.delete(`${API_BASE_URL}/api/breaks/${breakId}`, {
                params: { user_id: "default" }
              });
              
              // Refresh breaks to show original
              if (onBreaksUpdate) {
                onBreaksUpdate();
              }
              
              // Close editor
              setEditingBreak(null);
            } catch (error) {
              console.error('Error resetting break:', error);
              alert('Failed to reset break. Please try again.');
            }
          }}
          originalBreakData={editingBreak ? (() => {
            // Find the original break data before customization
            // If the break has been customized, we need to get it from the backend
            // For now, use the break data from breakSuggestions (which may be customized)
            // The reset will delete the customization, restoring the original
            const found = breakSuggestions.find(b => b.id === editingBreak.id);
            return found || editingBreak;
          })() : null}
          events={events}
          onTimeChange={(breakId, newTime) => {
            // Update local state immediately for real-time display
            setLocalBreakUpdates(prev => ({
              ...prev,
              [breakId]: newTime
            }));
            // Also update the editingBreak state
            if (editingBreak?.id === breakId) {
              setEditingBreak(prev => ({
                ...prev,
                time: newTime
              }));
            }
          }}
        />
      )}
    </div>
  );
};

export default BreakTimeline;
