import React from 'react';
import { motion } from 'framer-motion';

/**
 * Break Timeline Component - visualizes recommended break windows
 * TODO: Connect to backend /breaks/timeline endpoint
 */
const BreakTimeline = () => {
  // Mock data for development
  const mockTimeSlots = [
    { time: '9:00 AM', type: 'meeting', duration: 60, title: 'Sprint Planning' },
    { time: '10:00 AM', type: 'break', duration: 10, title: 'Recommended Break', recommended: true },
    { time: '10:30 AM', type: 'work', duration: 90, title: 'Focus Time' },
    { time: '12:00 PM', type: 'meeting', duration: 30, title: 'Client Demo' },
    { time: '12:30 PM', type: 'break', duration: 15, title: 'Serenity Break', recommended: true },
    { time: '1:00 PM', type: 'meeting', duration: 30, title: '1:1 Meeting' },
    { time: '2:00 PM', type: 'work', duration: 120, title: 'Deep Work' },
    { time: '4:00 PM', type: 'break', duration: 10, title: 'Quick Break', recommended: true },
  ];

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

  return (
    <div className="glass-card p-6">
      <h3 className="text-xl font-semibold text-ocean-800 mb-6">Today's Flow & Break Windows</h3>

      <div className="relative">
        {/* Timeline line */}
        <div className="absolute left-6 top-0 bottom-0 w-0.5 bg-ocean-200"></div>

        {/* Time slots */}
        <div className="space-y-1">
          {mockTimeSlots.map((slot, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.05 }}
              className="relative flex items-center"
            >
              {/* Time marker */}
              <div className="w-24 flex-shrink-0">
                <span className="text-sm font-medium text-ocean-600">{slot.time}</span>
              </div>

              {/* Timeline dot */}
              <div className={`absolute left-[22px] w-3 h-3 rounded-full ${
                slot.recommended ? 'bg-serenity-dark animate-pulse' : 'bg-ocean-400'
              }`}></div>

              {/* Slot card */}
              <div className="flex-1 ml-4">
                <div className={`${getSlotColor(slot.type, slot.recommended)} rounded-lg px-4 py-2 
                               ${slot.recommended ? 'shadow-lg border-2 border-serenity-dark' : 'shadow-sm'}`}>
                  <div className="flex items-center justify-between">
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
                    <span className={`text-xs ${
                      slot.type === 'meeting' ? 'text-white/80' : 
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
        <div className="flex items-center justify-center space-x-6 text-sm">
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 rounded-full bg-ocean-500"></div>
            <span className="text-ocean-600">Meeting</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 rounded-full bg-gradient-to-r from-serenity to-serenity-dark"></div>
            <span className="text-ocean-600">Recommended Break</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 rounded-full bg-ocean-100"></div>
            <span className="text-ocean-600">Focus Time</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default BreakTimeline;
