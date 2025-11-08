import React from 'react';
import { IoCalendarOutline, IoTimeOutline, IoPeopleOutline } from 'react-icons/io5';

/**
 * Meeting List Component - displays upcoming meetings from Google Calendar
 * TODO: Connect to backend /calendar/meetings endpoint
 */
const MeetingList = ({ loading }) => {
  // Mock data for development
  const mockMeetings = [
    {
      id: '1',
      title: 'Sprint Planning',
      startTime: new Date(Date.now() + 30 * 60 * 1000),
      endTime: new Date(Date.now() + 90 * 60 * 1000),
      attendees: 5,
      location: 'Zoom',
    },
    {
      id: '2',
      title: 'Client Demo',
      startTime: new Date(Date.now() + 150 * 60 * 1000),
      endTime: new Date(Date.now() + 180 * 60 * 1000),
      attendees: 3,
      location: 'Conference Room A',
    },
    {
      id: '3',
      title: '1:1 with Manager',
      startTime: new Date(Date.now() + 240 * 60 * 1000),
      endTime: new Date(Date.now() + 270 * 60 * 1000),
      attendees: 2,
      location: 'Office',
    },
  ];

  const formatTime = (date) => {
    return date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true });
  };

  const getTimeUntil = (date) => {
    const minutes = Math.round((date - new Date()) / 60000);
    if (minutes < 60) return `in ${minutes}m`;
    const hours = Math.floor(minutes / 60);
    return `in ${hours}h ${minutes % 60}m`;
  };

  if (loading) {
    return (
      <div className="glass-card p-6">
        <div className="animate-pulse space-y-4">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-20 bg-ocean-100 rounded-lg"></div>
          ))}
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
        <span className="text-sm text-ocean-600">{mockMeetings.length} today</span>
      </div>

      <div className="space-y-3">
        {mockMeetings.length === 0 ? (
          <div className="text-center py-8 text-ocean-500">
            <p>No meetings scheduled. Enjoy your free time! 🎉</p>
          </div>
        ) : (
          mockMeetings.map((meeting, index) => (
            <div
              key={meeting.id}
              className="p-4 bg-white/50 hover:bg-white/80 rounded-xl transition-all cursor-pointer border border-ocean-100 hover:border-ocean-300 hover:shadow-md"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <h4 className="font-semibold text-ocean-800 mb-2">{meeting.title}</h4>
                  
                  <div className="flex flex-wrap gap-4 text-sm text-ocean-600">
                    <div className="flex items-center space-x-1">
                      <IoTimeOutline />
                      <span>{formatTime(meeting.startTime)} - {formatTime(meeting.endTime)}</span>
                    </div>
                    <div className="flex items-center space-x-1">
                      <IoPeopleOutline />
                      <span>{meeting.attendees} attendees</span>
                    </div>
                  </div>
                  
                  {meeting.location && (
                    <div className="mt-2 text-xs text-ocean-500">📍 {meeting.location}</div>
                  )}
                </div>

                <div className="ml-4 text-right">
                  <span className="inline-block px-3 py-1 bg-ocean-100 text-ocean-700 text-xs font-medium rounded-full">
                    {getTimeUntil(meeting.startTime)}
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
