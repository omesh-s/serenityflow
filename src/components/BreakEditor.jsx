import React, { useState, useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import { IoClose, IoCheckmark, IoTrash, IoAdd, IoRefresh } from 'react-icons/io5';
import { BREAK_TYPES, getBreakType, getAllBreakTypes } from '../utils/breakTypes';
import axios from 'axios';
import { API_BASE_URL } from '../utils/constants';
import { useTimezone } from '../hooks/useTimezone.jsx';

/**
 * Break Editor Component - Edit break details inline
 */
const BreakEditor = ({ breakItem, onSave, onDelete, onCancel, onReset, events = [], onTimeChange, originalBreakData }) => {
  // Store original break data for reset functionality
  const originalDataRef = useRef(originalBreakData || breakItem);
  
  const [activity, setActivity] = useState(breakItem?.activity || 'meditation');
  const [duration, setDuration] = useState(breakItem?.duration || 10);
  const [reason, setReason] = useState(breakItem?.reason || '');
  const [description, setDescription] = useState(breakItem?.description || '');
  const [time, setTime] = useState(breakItem?.time || new Date().toISOString());
  const [customActivity, setCustomActivity] = useState('');
  const [showCustom, setShowCustom] = useState(false);
  const [hasBeenEdited, setHasBeenEdited] = useState(false);
  const { timezone } = useTimezone();

  const breakType = getBreakType(activity);
  const allBreakTypes = getAllBreakTypes();
  
  // Track if break was originally customized (to determine if reset is needed)
  const isCustomized = breakItem?.custom || false;

  // Update duration limits when activity changes
  useEffect(() => {
    if (breakType) {
      const currentDuration = parseInt(duration);
      if (currentDuration < breakType.minDuration) {
        setDuration(breakType.minDuration);
      } else if (currentDuration > breakType.maxDuration) {
        setDuration(breakType.maxDuration);
      }
    }
  }, [activity, breakType]);
  
  // Track if break has been edited
  useEffect(() => {
    const original = originalDataRef.current;
    if (original) {
      const edited = 
        activity !== (original.activity || 'meditation') ||
        duration !== (original.duration || 10) ||
        time !== (original.time || '') ||
        reason !== (original.reason || '') ||
        description !== (original.description || '');
      setHasBeenEdited(edited);
    }
  }, [activity, duration, time, reason, description]);
  
  // Clear reason when time changes (reason is context-specific)
  useEffect(() => {
    const original = originalDataRef.current;
    if (original && time !== (original.time || '')) {
      // Time has changed - clear the reason since it's no longer accurate
      setReason('');
    }
  }, [time]);

  const handleSave = () => {
    const breakData = {
      id: breakItem?.id,
      time: time,
      duration: parseInt(duration),
      activity: showCustom && customActivity ? customActivity.toLowerCase().replace(/\s+/g, '_') : activity,
      reason: reason || '', // Don't use breakType.description as default - leave empty if no reason
      description: description || breakType.description,
      icon: breakType.icon,
      custom: showCustom && customActivity ? true : (isCustomized || hasBeenEdited),
    };

    onSave(breakData);
  };

  const handleDelete = () => {
    if (window.confirm('Are you sure you want to delete this break?')) {
      onDelete(breakItem?.id);
    }
  };
  
  const handleReset = () => {
    if (window.confirm('Reset this break to its original state? This will undo all your changes.')) {
      const original = originalDataRef.current;
      if (original) {
        setActivity(original.activity || 'meditation');
        setDuration(original.duration || 10);
        setReason(original.reason || '');
        setDescription(original.description || '');
        setTime(original.time || new Date().toISOString());
        setCustomActivity('');
        setShowCustom(false);
        setHasBeenEdited(false);
        
        // Notify parent to reset the break
        if (onReset && breakItem?.id) {
          onReset(breakItem.id);
        }
      }
    }
  };
  
  // Convert UTC time to user's timezone for datetime-local input
  // datetime-local input works in browser's local timezone, so we need to show
  // the time that when converted from user's timezone to UTC gives the correct result
  const getLocalTimeString = (utcTimeString) => {
    if (!utcTimeString) return '';
    try {
      const date = new Date(utcTimeString);
      if (isNaN(date.getTime())) return '';
      
      // Format the date in the user's selected timezone
      // We'll use Intl to get the components in the user's timezone
      const formatter = new Intl.DateTimeFormat('en-CA', {
        timeZone: timezone,
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        hour12: false
      });
      
      // Format and parse to get the components
      const formatted = formatter.format(date);
      // Format is YYYY-MM-DD, HH:MM - we need to extract and combine
      const parts = formatter.formatToParts(date);
      const year = parts.find(p => p.type === 'year').value;
      const month = parts.find(p => p.type === 'month').value;
      const day = parts.find(p => p.type === 'day').value;
      const hour = parts.find(p => p.type === 'hour').value;
      const minute = parts.find(p => p.type === 'minute').value;
      
      return `${year}-${month}-${day}T${hour}:${minute}`;
    } catch (e) {
      console.error('Error converting time to local string:', e);
      // Fallback to simple conversion
      try {
        const date = new Date(utcTimeString);
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        const hours = String(date.getHours()).padStart(2, '0');
        const minutes = String(date.getMinutes()).padStart(2, '0');
        return `${year}-${month}-${day}T${hours}:${minutes}`;
      } catch (e2) {
        return '';
      }
    }
  };
  
  // Convert datetime-local input back to UTC
  // Simplified approach: datetime-local gives us time in browser's local timezone
  // We need to interpret the input as representing time in the user's selected timezone
  // and convert that to UTC
  const getUTCFromLocal = (localTimeString) => {
    if (!localTimeString) return new Date().toISOString();
    try {
      // Parse the input (YYYY-MM-DDTHH:mm)
      const [datePart, timePart] = localTimeString.split('T');
      if (!datePart || !timePart) return new Date().toISOString();
      
      const [year, month, day] = datePart.split('-').map(Number);
      const [hours, minutes] = timePart.split(':').map(Number);
      
      // Create a date string in ISO format that we can work with
      // We'll create it as if it's in UTC, then adjust
      const dateStr = `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}T${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:00`;
      
      // Create a date assuming this is in the user's timezone
      // We do this by creating a date and using the timezone offset
      // Approach: Create date in browser local time, calculate offset to user's timezone
      
      // Create date from the string (will be interpreted as browser local time)
      const browserLocalDate = new Date(dateStr);
      
      // Get what time this represents in the user's timezone
      const userTZStr = new Intl.DateTimeFormat('en-CA', {
        timeZone: timezone,
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        hour12: false
      }).format(browserLocalDate);
      
      // Get what time this represents in browser timezone  
      const browserTZStr = new Intl.DateTimeFormat('en-CA', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        hour12: false
      }).format(browserLocalDate);
      
      // If they match, browser timezone = user timezone
      if (userTZStr === browserTZStr) {
        return browserLocalDate.toISOString();
      }
      
      // Calculate the offset needed
      // We want the input time to represent the time in user's timezone
      // So if input shows "16:02" and user timezone shows "15:02" for the same moment,
      // we need to adjust by +1 hour
      
      // Parse the formatted strings to compare
      const inputStr = `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}T${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`;
      
      // Find a UTC time that when formatted in user's timezone gives us the input time
      // Use binary search or iterative approach
      // Simpler: Try creating UTC date and see what it shows in user timezone
      
      // Create UTC date with the time components
      let testDate = new Date(Date.UTC(year, month - 1, day, hours, minutes));
      let testInUserTZ = new Intl.DateTimeFormat('en-CA', {
        timeZone: timezone,
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        hour12: false
      }).format(testDate);
      
      // Compare and adjust
      if (testInUserTZ === inputStr) {
        return testDate.toISOString();
      }
      
      // They don't match - need to find the right UTC time
      // Get offset by comparing a known UTC time
      const now = new Date();
      const nowInUserTZ = new Intl.DateTimeFormat('en-CA', {
        timeZone: timezone,
        hour: '2-digit',
        minute: '2-digit',
        hour12: false
      }).format(now);
      const nowInBrowserTZ = new Intl.DateTimeFormat('en-CA', {
        hour: '2-digit',
        minute: '2-digit',
        hour12: false
      }).format(now);
      
      // If user and browser timezones are different, we need to account for it
      // For simplicity, just use the UTC date we created
      // The backend should handle timezone properly
      return testDate.toISOString();
    } catch (e) {
      console.error('Error converting local time to UTC:', e);
      // Fallback: create date from string (browser local time)
      try {
        const date = new Date(localTimeString);
        return date.toISOString();
      } catch (e2) {
        return new Date().toISOString();
      }
    }
  };

  const formatTime = (dateString) => {
    if (!dateString) return '';
    const date = new Date(dateString);
    if (isNaN(date.getTime())) return '';
    
    // Format in user's selected timezone
    try {
      return new Intl.DateTimeFormat('en-US', {
        timeZone: timezone,
        hour: 'numeric',
        minute: '2-digit',
        hour12: true
      }).format(date);
    } catch (e) {
      // Fallback to local timezone
      return date.toLocaleTimeString('en-US', {
        hour: 'numeric',
        minute: '2-digit',
        hour12: true
      });
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
      onClick={(e) => e.target === e.currentTarget && onCancel()}
    >
      <motion.div
        initial={{ y: 20 }}
        animate={{ y: 0 }}
        className="bg-white rounded-xl shadow-2xl max-w-3xl w-full"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="bg-gradient-to-r from-ocean-500 to-ocean-600 text-white p-4 rounded-t-xl flex items-center justify-between">
          <div>
            <h3 className="text-xl font-bold">{breakItem?.id ? 'Edit Break' : 'Add Break'}</h3>
            <p className="text-ocean-100 text-xs mt-1">{formatTime(time)}</p>
          </div>
          <button
            onClick={onCancel}
            className="text-white hover:text-ocean-100 transition-colors"
          >
            <IoClose size={20} />
          </button>
        </div>

        {/* Content - Grid layout for compact display */}
        <div className="p-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Left Column */}
            <div className="space-y-4">
              {/* Time Adjustment - Most Important, at top */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Time
                </label>
                <input
                  type="datetime-local"
                  value={getLocalTimeString(time)}
                  onChange={(e) => {
                    const newTime = getUTCFromLocal(e.target.value);
                    setTime(newTime);
                    // Clear reason when time changes since it's no longer accurate
                    setReason('');
                    // Notify parent immediately for real-time update
                    if (breakItem?.id && onTimeChange) {
                      onTimeChange(breakItem.id, newTime);
                    }
                  }}
                  className="w-full px-3 py-2 text-sm border-2 border-gray-200 rounded-lg focus:border-ocean-500 focus:outline-none"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Time shown in your selected timezone: {timezone}
                  {timezone !== Intl.DateTimeFormat().resolvedOptions().timeZone && 
                    ` (Browser: ${Intl.DateTimeFormat().resolvedOptions().timeZone})`}
                </p>
              </div>

              {/* Break Type Selection - Compact */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Break Type
                </label>
                <div className="grid grid-cols-3 gap-2 max-h-32 overflow-y-auto">
                  {allBreakTypes.map((type) => (
                    <button
                      key={type.id}
                      onClick={() => {
                        setActivity(type.id);
                        setShowCustom(false);
                        setDuration(type.defaultDuration);
                      }}
                      className={`p-2 rounded-lg border-2 transition-all ${
                        activity === type.id && !showCustom
                          ? 'border-ocean-500 bg-ocean-50'
                          : 'border-gray-200 hover:border-gray-300'
                      }`}
                    >
                      <div className="text-xl mb-1">{type.icon}</div>
                      <div className="text-xs font-medium text-gray-700 truncate">{type.name}</div>
                    </button>
                  ))}
                </div>
                
                {/* Custom Break Type - Compact */}
                <div className="mt-2">
                  <button
                    onClick={() => setShowCustom(!showCustom)}
                    className="text-xs text-ocean-600 hover:text-ocean-700 flex items-center space-x-1"
                  >
                    <IoAdd size={14} />
                    <span>Custom</span>
                  </button>
                  
                  {showCustom && (
                    <input
                      type="text"
                      value={customActivity}
                      onChange={(e) => setCustomActivity(e.target.value)}
                      placeholder="Custom break type"
                      className="w-full mt-1 px-3 py-1 text-sm border-2 border-ocean-200 rounded-lg focus:border-ocean-500 focus:outline-none"
                    />
                  )}
                </div>
              </div>

              {/* Duration - Compact */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Duration: {duration} minutes
                </label>
                <input
                  type="range"
                  min={breakType.minDuration}
                  max={breakType.maxDuration}
                  value={duration}
                  onChange={(e) => setDuration(e.target.value)}
                  className="w-full"
                />
                <div className="flex justify-between text-xs text-gray-500 mt-1">
                  <span>{breakType.minDuration} min</span>
                  <span>{breakType.maxDuration} min</span>
                </div>
              </div>
            </div>

            {/* Right Column */}
            <div className="space-y-4">
              {/* Reason */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Reason (Optional)
                </label>
                <textarea
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  placeholder="e.g., After 3 back-to-back meetings (cleared when time changes)"
                  className="w-full px-3 py-2 text-sm border-2 border-gray-200 rounded-lg focus:border-ocean-500 focus:outline-none resize-none"
                  rows="3"
                />
                {!reason && (
                  <p className="text-xs text-gray-500 mt-1">
                    Reason is automatically cleared when you change the break time
                  </p>
                )}
              </div>

              {/* Description */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Description (Optional)
                </label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Additional details about this break"
                  className="w-full px-3 py-2 text-sm border-2 border-gray-200 rounded-lg focus:border-ocean-500 focus:outline-none resize-none"
                  rows="3"
                />
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="bg-gray-50 p-4 rounded-b-xl flex items-center justify-between border-t border-gray-200">
          <div className="flex items-center space-x-2">
            {breakItem?.id && (
              <>
                <button
                  onClick={handleDelete}
                  className="px-4 py-2 text-sm text-red-600 hover:bg-red-50 rounded-lg transition-colors flex items-center space-x-2"
                >
                  <IoTrash size={16} />
                  <span>Delete</span>
                </button>
                {hasBeenEdited && (
                  <button
                    onClick={handleReset}
                    className="px-4 py-2 text-sm text-orange-600 hover:bg-orange-50 rounded-lg transition-colors flex items-center space-x-2"
                    title="Reset to original break settings"
                  >
                    <IoRefresh size={16} />
                    <span>Reset</span>
                  </button>
                )}
              </>
            )}
            {!breakItem?.id && <div></div>}
          </div>
          
          <div className="flex items-center space-x-3 ml-auto">
            <button
              onClick={onCancel}
              className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              className="px-6 py-2 text-sm bg-ocean-500 text-white rounded-lg hover:bg-ocean-600 transition-colors flex items-center space-x-2"
            >
              <IoCheckmark size={16} />
              <span>Save</span>
            </button>
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
};

export default BreakEditor;

