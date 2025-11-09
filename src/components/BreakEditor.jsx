import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { IoClose, IoCheckmark, IoTrash, IoAdd } from 'react-icons/io5';
import { BREAK_TYPES, getBreakType, getAllBreakTypes } from '../utils/breakTypes';
import axios from 'axios';
import { API_BASE_URL } from '../utils/constants';

/**
 * Break Editor Component - Edit break details inline
 */
const BreakEditor = ({ breakItem, onSave, onDelete, onCancel, events = [] }) => {
  const [activity, setActivity] = useState(breakItem?.activity || 'meditation');
  const [duration, setDuration] = useState(breakItem?.duration || 10);
  const [reason, setReason] = useState(breakItem?.reason || '');
  const [description, setDescription] = useState(breakItem?.description || '');
  const [time, setTime] = useState(breakItem?.time || new Date().toISOString());
  const [customActivity, setCustomActivity] = useState('');
  const [showCustom, setShowCustom] = useState(false);

  const breakType = getBreakType(activity);
  const allBreakTypes = getAllBreakTypes();

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

  const handleSave = () => {
    const breakData = {
      id: breakItem?.id,
      time: time,
      duration: parseInt(duration),
      activity: showCustom && customActivity ? customActivity.toLowerCase().replace(/\s+/g, '_') : activity,
      reason: reason || breakType.description,
      description: description || breakType.description,
      icon: breakType.icon,
      custom: showCustom && customActivity ? true : false,
    };

    onSave(breakData);
  };

  const handleDelete = () => {
    if (window.confirm('Are you sure you want to delete this break?')) {
      onDelete(breakItem?.id);
    }
  };

  const formatTime = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleTimeString('en-US', { 
      hour: 'numeric', 
      minute: '2-digit', 
      hour12: true 
    });
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
        className="bg-white rounded-xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="sticky top-0 bg-gradient-to-r from-ocean-500 to-ocean-600 text-white p-6 rounded-t-xl flex items-center justify-between">
          <div>
            <h3 className="text-2xl font-bold">Edit Break</h3>
            <p className="text-ocean-100 text-sm mt-1">{formatTime(time)}</p>
          </div>
          <button
            onClick={onCancel}
            className="text-white hover:text-ocean-100 transition-colors"
          >
            <IoClose size={24} />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Break Type Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-3">
              Break Type
            </label>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3 max-h-48 overflow-y-auto">
              {allBreakTypes.map((type) => (
                <button
                  key={type.id}
                  onClick={() => {
                    setActivity(type.id);
                    setShowCustom(false);
                    setDuration(type.defaultDuration);
                  }}
                  className={`p-4 rounded-lg border-2 transition-all ${
                    activity === type.id && !showCustom
                      ? 'border-ocean-500 bg-ocean-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <div className="text-2xl mb-1">{type.icon}</div>
                  <div className="text-xs font-medium text-gray-700">{type.name}</div>
                </button>
              ))}
            </div>
            
            {/* Custom Break Type */}
            <div className="mt-4">
              <button
                onClick={() => setShowCustom(!showCustom)}
                className="text-sm text-ocean-600 hover:text-ocean-700 flex items-center space-x-1"
              >
                <IoAdd size={16} />
                <span>Add Custom Break Type</span>
              </button>
              
              {showCustom && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  className="mt-2"
                >
                  <input
                    type="text"
                    value={customActivity}
                    onChange={(e) => setCustomActivity(e.target.value)}
                    placeholder="e.g., Power Nap, Mindfulness Sketch"
                    className="w-full px-4 py-2 border-2 border-ocean-200 rounded-lg focus:border-ocean-500 focus:outline-none"
                  />
                </motion.div>
              )}
            </div>
          </div>

          {/* Duration */}
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

          {/* Reason */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Reason
            </label>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="e.g., After 3 back-to-back meetings"
              className="w-full px-4 py-2 border-2 border-gray-200 rounded-lg focus:border-ocean-500 focus:outline-none resize-none"
              rows="2"
            />
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
              className="w-full px-4 py-2 border-2 border-gray-200 rounded-lg focus:border-ocean-500 focus:outline-none resize-none"
              rows="2"
            />
          </div>

          {/* Time Adjustment */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Time
            </label>
            <input
              type="datetime-local"
              value={new Date(time).toISOString().slice(0, 16)}
              onChange={(e) => setTime(new Date(e.target.value).toISOString())}
              className="w-full px-4 py-2 border-2 border-gray-200 rounded-lg focus:border-ocean-500 focus:outline-none"
            />
          </div>
        </div>

        {/* Footer */}
        <div className="sticky bottom-0 bg-gray-50 p-6 rounded-b-xl flex items-center justify-between border-t border-gray-200">
          <button
            onClick={handleDelete}
            className="px-4 py-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors flex items-center space-x-2"
          >
            <IoTrash size={18} />
            <span>Delete</span>
          </button>
          
          <div className="flex items-center space-x-3">
            <button
              onClick={onCancel}
              className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              className="px-6 py-2 bg-ocean-500 text-white rounded-lg hover:bg-ocean-600 transition-colors flex items-center space-x-2"
            >
              <IoCheckmark size={18} />
              <span>Save</span>
            </button>
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
};

export default BreakEditor;

