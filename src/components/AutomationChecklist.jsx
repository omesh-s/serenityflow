import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  IoCheckmarkCircle, IoCloseCircle, IoAlertCircle, IoInformationCircle, 
  IoRefresh, IoArchive, IoCheckmark, IoClose, IoDocumentText, IoDocuments,
  IoPeople, IoStatsChart, IoFlash, IoTrash, IoCheckmarkDone, IoHelpCircle,
  IoArrowForward, IoTime
} from 'react-icons/io5';
import axios from 'axios';
import { API_BASE_URL } from '../utils/constants';
import { useTheme } from '../hooks/useTheme.jsx';
import { useEventSounds } from '../hooks/useEventSounds';

/**
 * Automation Checklist Component
 * Displays automated actions, warnings, and suggestions from background agents
 */
const AutomationChecklist = () => {
  const [checklist, setChecklist] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [summary, setSummary] = useState(null);
  const [runningAgents, setRunningAgents] = useState(new Set());
  const [notifications, setNotifications] = useState([]);
  const { themeColors } = useTheme();
  const { playAccept, playError } = useEventSounds();

  useEffect(() => {
    loadChecklist();
    loadSummary();
    
    // Refresh every 30 seconds
    const interval = setInterval(() => {
      loadChecklist();
      loadSummary();
    }, 30000);
    
    return () => clearInterval(interval);
  }, []);

  const loadChecklist = async () => {
    try {
      // Get pending items by default
      const response = await axios.get(`${API_BASE_URL}/api/checklist?status=pending`);
      // Response is now a list directly, not an object with items property
      setChecklist(Array.isArray(response.data) ? response.data : []);
      setError(null);
    } catch (err) {
      console.error('Error loading checklist:', err);
      setError('Failed to load checklist');
      setChecklist([]);
    } finally {
      setLoading(false);
    }
  };

  const loadSummary = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/checklist/summary`);
      setSummary(response.data);
    } catch (err) {
      console.error('Error loading summary:', err);
    }
  };

  // Notification system
  const addNotification = (message, type = 'info', duration = 5000) => {
    const id = Date.now();
    const notification = { id, message, type };
    setNotifications(prev => [...prev, notification]);
    
    if (duration > 0) {
      setTimeout(() => {
        setNotifications(prev => prev.filter(n => n.id !== id));
      }, duration);
    }
    
    return id;
  };

  const removeNotification = (id) => {
    setNotifications(prev => prev.filter(n => n.id !== id));
  };

  const triggerAgent = async (agentName, forceReprocess = false) => {
    try {
      // Show loading state for this specific agent
      setRunningAgents(prev => new Set(prev).add(agentName));
      setError(null);
      
      // Add force_reprocess as query parameter if needed
      const url = `${API_BASE_URL}/api/checklist/agents/run/${agentName}${forceReprocess ? '?force_reprocess=true' : ''}`;
      const response = await axios.post(url);
      console.log(`${agentName} result:`, response.data);
      
      // Show success message with details
      const result = response.data;
      if (result.success !== false) {
        // Play accept sound when task completes successfully
        playAccept();
        
        let message = '';
        if (result.message) {
          message = result.message;
          if (result.stats && agentName === 'story_extraction') {
            message = `✅ ${result.stats.stories_extracted || 0} story${result.stats.stories_extracted !== 1 ? 'ies' : 'y'} extracted from ${result.stats.pages_processed || 0} page${result.stats.pages_processed !== 1 ? 's' : ''}`;
          }
        } else if (result.count > 0) {
          message = `✅ Success! ${result.count} item${result.count !== 1 ? 's' : ''} processed.`;
        } else if (agentName === 'story_extraction') {
          message = `ℹ️ Processed ${result.pages_processed || 0} page${result.pages_processed !== 1 ? 's' : ''}. No stories found. Make sure your pages contain meeting notes with action items.`;
        } else {
          message = `✅ ${agentName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())} completed successfully.`;
        }
        
        addNotification(message, 'success');
      } else {
        // Show error message
        playError();
        const errorMsg = result.error || `Failed to run ${agentName}`;
        addNotification(`❌ ${errorMsg}`, 'error');
      }
      
      // Reload checklist after a short delay to see results
      setTimeout(() => {
        loadChecklist();
        loadSummary();
        setRunningAgents(prev => {
          const newSet = new Set(prev);
          newSet.delete(agentName);
          return newSet;
        });
      }, 2000);
      return response.data;
    } catch (err) {
      console.error(`Error triggering ${agentName}:`, err);
      playError();
      const errorMsg = err.response?.data?.detail || err.response?.data?.error || err.message || `Failed to run ${agentName}. Check console for details.`;
      addNotification(`❌ ${errorMsg}`, 'error');
      setError(errorMsg);
      setRunningAgents(prev => {
        const newSet = new Set(prev);
        newSet.delete(agentName);
        return newSet;
      });
      throw err;
    }
  };

  const handleItemAction = async (itemId, action, actionData = {}) => {
    try {
      if (action === 'approve' && actionData.story_ids) {
        // Approve stories using the new /stories/action endpoint
        await axios.post(`${API_BASE_URL}/api/checklist/stories/action`, {
          story_ids: actionData.story_ids,
          action: 'approve'
        });
      } else if (action === 'archive' && actionData.story_ids) {
        // Archive stories
        await axios.post(`${API_BASE_URL}/api/checklist/stories/action`, {
          story_ids: actionData.story_ids,
          action: 'archive'
        });
      } else if (action === 'reject' && actionData.story_ids) {
        // Reject stories
        await axios.post(`${API_BASE_URL}/api/checklist/stories/action`, {
          story_ids: actionData.story_ids,
          action: 'reject'
        });
      }
      
      // Resolve checklist item
      await axios.post(`${API_BASE_URL}/api/checklist/items/${itemId}/action`, {
        action: 'resolve'
      });
      
      // Play accept sound when approving tasks
      if (action === 'approve') {
        playAccept();
        addNotification('✅ Items approved successfully!', 'success');
      } else if (action === 'archive') {
        addNotification('📦 Items archived successfully!', 'success');
      } else if (action === 'reject') {
        addNotification('❌ Items rejected.', 'info');
      }
      
      // Reload checklist after a short delay
      setTimeout(() => {
        loadChecklist();
        loadSummary();
      }, 500);
    } catch (err) {
      console.error('Error handling item action:', err);
      playError();
      const errorMsg = err.response?.data?.detail || err.message || 'Failed to process action. Please try again.';
      addNotification(`❌ ${errorMsg}`, 'error');
    }
  };

  const handleDismiss = async (itemId) => {
    try {
      await axios.post(`${API_BASE_URL}/api/checklist/items/${itemId}/action`, {
        action: 'dismiss'
      });
      
      addNotification('Item dismissed', 'info', 3000);
      loadChecklist();
      loadSummary();
    } catch (err) {
      console.error('Error dismissing item:', err);
      addNotification('❌ Failed to dismiss item. Please try again.', 'error');
    }
  };

  const handleClearAll = async () => {
    try {
      const response = await axios.post(`${API_BASE_URL}/api/checklist/clear-all`);
      if (response.data.success) {
        loadChecklist();
        loadSummary();
      }
    } catch (err) {
      console.error('Error clearing all items:', err);
      alert('Failed to clear all items. Please try again.');
    }
  };

  const getItemIcon = (type, priority) => {
    if (type === 'story_approval') {
      return <IoCheckmarkCircle size={20} className="text-blue-500" />;
    } else if (type === 'backlog_cleanup') {
      return <IoArchive size={20} className="text-orange-500" />;
    } else if (type === 'release_report') {
      return <IoInformationCircle size={20} className="text-green-500" />;
    } else if (type === 'stakeholder_action') {
      return <IoAlertCircle size={20} className="text-red-500" />;
    } else if (type === 'integration_status') {
      return <IoInformationCircle size={20} className="text-gray-500" />;
    }
    return <IoInformationCircle size={20} />;
  };

  const getPriorityColor = (priority) => {
    if (priority === 'high') {
      return themeColors ? themeColors.primary : '#ef4444';
    } else if (priority === 'medium') {
      return themeColors ? themeColors.primaryLight : '#f59e0b';
    }
    return themeColors ? themeColors.textLight : '#6b7280';
  };

  if (loading) {
    return (
      <div className="glass-card p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 
            className="text-xl font-semibold"
            style={themeColors ? { color: themeColors.text } : {}}
          >
            Automation Checklist
          </h3>
        </div>
        <div className="animate-pulse space-y-3">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-16 bg-gray-200 rounded-lg"></div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="glass-card p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 
            className="text-xl font-semibold"
            style={themeColors ? { color: themeColors.text } : {}}
          >
            Automation Checklist
          </h3>
        </div>
        <div className="text-center py-8 text-red-500">
          <p>{error}</p>
          <button
            onClick={loadChecklist}
            className="mt-4 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  // Checklist is now a list directly, not an object with items property
  const items = Array.isArray(checklist) ? checklist : (checklist?.items || []);

  return (
    <div className="glass-card p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 
          className="text-xl font-semibold"
          style={themeColors ? { color: themeColors.text } : {}}
        >
          Automation Checklist
        </h3>
        <div className="flex items-center space-x-2">
          {items.length > 0 && (
            <button
              onClick={handleClearAll}
              className="px-3 py-1 text-sm rounded-lg transition-colors flex items-center space-x-1"
              style={themeColors ? {
                backgroundColor: themeColors.primaryLight + '40',
                color: themeColors.text
              } : {
                backgroundColor: '#e5e7eb',
                color: '#374151'
              }}
              title="Clear all pending items"
            >
              <IoArchive size={16} />
              <span>Clear All</span>
            </button>
          )}
          <button
            onClick={() => { loadChecklist(); loadSummary(); }}
            className="p-2 rounded-lg transition-colors"
            style={themeColors ? { color: themeColors.textLight } : {}}
            title="Refresh"
          >
            <IoRefresh size={20} />
          </button>
        </div>
      </div>

      {/* Notifications - Stacked */}
      <div className="fixed top-20 right-4 z-50 flex flex-col gap-2 max-w-md pointer-events-none">
        <AnimatePresence>
          {notifications.map((notification, index) => (
            <motion.div
              key={notification.id}
              initial={{ opacity: 0, x: 100, scale: 0.95 }}
              animate={{ opacity: 1, x: 0, scale: 1 }}
              exit={{ opacity: 0, x: 100, scale: 0.95 }}
              transition={{ duration: 0.2, delay: index * 0.05 }}
              className="pointer-events-auto"
            >
              <div
                className="p-4 rounded-lg shadow-lg flex items-start space-x-3"
                style={{
                  backgroundColor: notification.type === 'error' 
                    ? '#fee2e2' 
                    : notification.type === 'success'
                    ? '#d1fae5'
                    : '#dbeafe',
                  borderLeft: `4px solid ${
                    notification.type === 'error'
                      ? '#ef4444'
                      : notification.type === 'success'
                      ? '#10b981'
                      : '#3b82f6'
                  }`
                }}
              >
                <div className="flex-1">
                  <p className="text-sm font-medium" style={{ color: '#1f2937' }}>
                    {notification.message}
                  </p>
                </div>
                <button
                  onClick={() => removeNotification(notification.id)}
                  className="text-gray-500 hover:text-gray-700 flex-shrink-0"
                >
                  <IoClose size={18} />
                </button>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      {/* Summary */}
      {summary && (
        <div className="mb-4 p-4 rounded-lg" style={themeColors ? { backgroundColor: themeColors.primaryLight + '20' } : { backgroundColor: '#f3f4f6' }}>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div className="relative group">
              <div 
                className="font-medium flex items-center space-x-1 cursor-help"
                style={themeColors ? { color: themeColors.text } : {}}
              >
                <span>Pending Items</span>
                <IoHelpCircle size={14} className="opacity-50" />
              </div>
              <div 
                className="text-2xl font-bold"
                style={themeColors ? { color: themeColors.primary } : {}}
              >
                {summary.pending_items || 0}
              </div>
              <div className="absolute left-0 top-full mt-2 w-48 p-2 bg-gray-800 text-white text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
                Items waiting for your review or action
              </div>
            </div>
            <div className="relative group">
              <div 
                className="font-medium flex items-center space-x-1 cursor-help"
                style={themeColors ? { color: themeColors.text } : {}}
              >
                <span>Backlog Health</span>
                <IoHelpCircle size={14} className="opacity-50" />
              </div>
              <div 
                className="text-2xl font-bold flex items-center space-x-1"
                style={themeColors ? { color: themeColors.primary } : {}}
              >
                <span>{Math.round(summary.backlog_health_score || 100)}</span>
                <span className="text-sm">%</span>
              </div>
              <div className="absolute left-0 top-full mt-2 w-48 p-2 bg-gray-800 text-white text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
                Overall health score based on duplicates, priority, and organization
              </div>
            </div>
            <div className="relative group">
              <div 
                className="font-medium flex items-center space-x-1 cursor-help"
                style={themeColors ? { color: themeColors.text } : {}}
              >
                <span>Stakeholders</span>
                <IoHelpCircle size={14} className="opacity-50" />
              </div>
              <div 
                className="text-2xl font-bold"
                style={themeColors ? { color: themeColors.primary } : {}}
              >
                {summary.stakeholders_needing_attention || 0}
              </div>
              <div className="absolute left-0 top-full mt-2 w-48 p-2 bg-gray-800 text-white text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
                Stakeholders who need attention or updates
              </div>
            </div>
            <div className="relative group">
              <div 
                className="font-medium flex items-center space-x-1 cursor-help"
                style={themeColors ? { color: themeColors.text } : {}}
              >
                <span>Reports Ready</span>
                <IoHelpCircle size={14} className="opacity-50" />
              </div>
              <div 
                className="text-2xl font-bold"
                style={themeColors ? { color: themeColors.primary } : {}}
              >
                {summary.ready_reports || 0}
              </div>
              <div className="absolute left-0 top-full mt-2 w-48 p-2 bg-gray-800 text-white text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
                Release reports ready for review
              </div>
            </div>
          </div>
          
          {/* Agent Actions - Show when everything is 0 or when there are items */}
          {(summary.pending_items === 0 && summary.stakeholders_needing_attention === 0 && summary.ready_reports === 0) && (
            <div className="mt-6 pt-4 border-t" style={themeColors ? { borderColor: themeColors.primaryLight + '40' } : { borderColor: '#e5e7eb' }}>
              <div className="mb-4">
                <h4 
                  className="text-sm font-semibold mb-1 flex items-center space-x-2"
                  style={themeColors ? { color: themeColors.text } : {}}
                >
                  <IoFlash size={16} />
                  <span>Quick Start Workflow</span>
                </h4>
                <p 
                  className="text-xs mb-4"
                  style={themeColors ? { color: themeColors.textLight } : {}}
                >
                  Follow these steps to get started with automation:
                </p>
              </div>

              {/* Workflow Steps */}
              <div className="space-y-3 mb-4">
                {/* Step 1: Extract */}
                <div className="flex items-start space-x-3">
                  <div className="flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold text-white" style={{ backgroundColor: themeColors?.primary || '#3b82f6' }}>
                    1
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center space-x-2 mb-1">
                      <span className="text-sm font-medium" style={themeColors ? { color: themeColors.text } : {}}>Extract Stories</span>
                      <span className="text-xs px-2 py-0.5 rounded" style={{ backgroundColor: themeColors?.primaryLight + '40' || '#e5e7eb', color: themeColors?.textLight || '#6b7280' }}>Start Here</span>
                    </div>
                    <p className="text-xs mb-2" style={themeColors ? { color: themeColors.textLight } : {}}>
                      Extract action items and stories from your Notion meeting notes
                    </p>
                    <div className="flex flex-wrap gap-2">
                      <button
                        onClick={() => triggerAgent('story_extraction', false)}
                        disabled={runningAgents.has('story_extraction')}
                        className="px-3 py-1.5 text-xs rounded-lg transition-all flex items-center space-x-1.5 disabled:opacity-50 disabled:cursor-not-allowed"
                        style={themeColors ? {
                          backgroundColor: themeColors.primary,
                          color: '#ffffff',
                        } : {
                          backgroundColor: '#3b82f6',
                          color: '#ffffff',
                        }}
                        title="Extract stories from new/updated Notion pages"
                      >
                        {runningAgents.has('story_extraction') ? (
                          <>
                            <IoTime size={14} className="animate-spin" />
                            <span>Processing...</span>
                          </>
                        ) : (
                          <>
                            <IoDocumentText size={14} />
                            <span>Extract Stories</span>
                          </>
                        )}
                      </button>
                      <button
                        onClick={() => triggerAgent('story_extraction', true)}
                        disabled={runningAgents.has('story_extraction')}
                        className="px-3 py-1.5 text-xs rounded-lg transition-all flex items-center space-x-1.5 disabled:opacity-50 disabled:cursor-not-allowed"
                        style={themeColors ? {
                          backgroundColor: themeColors.primaryLight + '60',
                          color: themeColors.text,
                        } : {
                          backgroundColor: '#e5e7eb',
                          color: '#374151',
                        }}
                        title="Force reprocess all pages (even if already processed)"
                      >
                        <IoFlash size={14} />
                        <span>Force Reprocess</span>
                      </button>
                    </div>
                  </div>
                </div>

                {/* Step 2: Analyze & Clean */}
                <div className="flex items-start space-x-3">
                  <div className="flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold" style={{ backgroundColor: themeColors?.primaryLight + '40' || '#e5e7eb', color: themeColors?.text || '#374151' }}>
                    2
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center space-x-2 mb-1">
                      <span className="text-sm font-medium" style={themeColors ? { color: themeColors.text } : {}}>Analyze & Clean</span>
                    </div>
                    <p className="text-xs mb-2" style={themeColors ? { color: themeColors.textLight } : {}}>
                      Audit backlog and identify stakeholders from extracted stories
                    </p>
                    <div className="flex flex-wrap gap-2">
                      <button
                        onClick={() => triggerAgent('noise_clearing')}
                        disabled={runningAgents.has('noise_clearing')}
                        className="px-3 py-1.5 text-xs rounded-lg transition-all flex items-center space-x-1.5 disabled:opacity-50 disabled:cursor-not-allowed"
                        style={themeColors ? {
                          backgroundColor: themeColors.primaryLight + '40',
                          color: themeColors.text,
                        } : {
                          backgroundColor: '#e5e7eb',
                          color: '#374151',
                        }}
                        title="Audit backlog for duplicates and low-priority items"
                      >
                        {runningAgents.has('noise_clearing') ? (
                          <>
                            <IoTime size={14} className="animate-spin" />
                            <span>Processing...</span>
                          </>
                        ) : (
                          <>
                            <IoTrash size={14} />
                            <span>Audit Backlog</span>
                          </>
                        )}
                      </button>
                      <button
                        onClick={() => triggerAgent('stakeholder_mapping')}
                        disabled={runningAgents.has('stakeholder_mapping')}
                        className="px-3 py-1.5 text-xs rounded-lg transition-all flex items-center space-x-1.5 disabled:opacity-50 disabled:cursor-not-allowed"
                        style={themeColors ? {
                          backgroundColor: themeColors.primaryLight + '40',
                          color: themeColors.text,
                        } : {
                          backgroundColor: '#e5e7eb',
                          color: '#374151',
                        }}
                        title="Map stakeholders from stories"
                      >
                        {runningAgents.has('stakeholder_mapping') ? (
                          <>
                            <IoTime size={14} className="animate-spin" />
                            <span>Processing...</span>
                          </>
                        ) : (
                          <>
                            <IoPeople size={14} />
                            <span>Map Stakeholders</span>
                          </>
                        )}
                      </button>
                    </div>
                  </div>
                </div>

                {/* Step 3: Monitor */}
                <div className="flex items-start space-x-3">
                  <div className="flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold" style={{ backgroundColor: themeColors?.primaryLight + '40' || '#e5e7eb', color: themeColors?.text || '#374151' }}>
                    3
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center space-x-2 mb-1">
                      <span className="text-sm font-medium" style={themeColors ? { color: themeColors.text } : {}}>Monitor Health</span>
                    </div>
                    <p className="text-xs mb-2" style={themeColors ? { color: themeColors.textLight } : {}}>
                      Check integration health and system status
                    </p>
                    <button
                      onClick={() => triggerAgent('integration_health')}
                      disabled={runningAgents.has('integration_health')}
                      className="px-3 py-1.5 text-xs rounded-lg transition-all flex items-center space-x-1.5 disabled:opacity-50 disabled:cursor-not-allowed"
                      style={themeColors ? {
                        backgroundColor: themeColors.primaryLight + '40',
                        color: themeColors.text,
                      } : {
                        backgroundColor: '#e5e7eb',
                        color: '#374151',
                      }}
                      title="Check integration health (Notion, Google Calendar, Gemini)"
                    >
                      {runningAgents.has('integration_health') ? (
                        <>
                          <IoTime size={14} className="animate-spin" />
                          <span>Processing...</span>
                        </>
                      ) : (
                        <>
                          <IoStatsChart size={14} />
                          <span>Check Health</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>
              </div>

              <div className="mt-4 p-3 rounded-lg" style={{ backgroundColor: themeColors?.primaryLight + '20' || '#eff6ff', borderLeft: `3px solid ${themeColors?.primary || '#3b82f6'}` }}>
                <p 
                  className="text-xs flex items-start space-x-2"
                  style={themeColors ? { color: themeColors.textLight } : {}}
                >
                  <IoInformationCircle size={16} className="mt-0.5 flex-shrink-0" />
                  <span>
                    <strong>Note:</strong> Story extraction requires Notion pages with meeting notes. Make sure Notion is connected in Settings.
                  </span>
                </p>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Checklist Items */}
      <div className="space-y-3">
        {items.length === 0 ? (
          <motion.div 
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="text-center py-12"
          >
            <div className="mb-4">
              <IoCheckmarkDone size={48} className="mx-auto mb-3" style={{ color: themeColors?.primary || '#10b981' }} />
            </div>
            <p 
              className="text-lg font-semibold mb-2"
              style={themeColors ? { color: themeColors.text } : {}}
            >
              All caught up! 🎉
            </p>
            <p 
              className="text-sm"
              style={themeColors ? { color: themeColors.textLight } : {}}
            >
              No pending items. Your automation is running smoothly.
            </p>
          </motion.div>
        ) : (
          items.map((item) => (
            <motion.div
              key={item.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="p-4 rounded-lg border-2 transition-all"
              style={{
                borderColor: getPriorityColor(item.priority) + '40',
                backgroundColor: themeColors ? themeColors.primaryLight + '10' : '#ffffff'
              }}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-start space-x-3 flex-1">
                  {getItemIcon(item.type, item.priority)}
                  <div className="flex-1">
                    <div className="flex items-center space-x-2 mb-1">
                      <h4 
                        className="font-semibold"
                        style={themeColors ? { color: themeColors.text } : {}}
                      >
                        {item.title}
                      </h4>
                      <span
                        className="px-2 py-1 text-xs font-medium rounded-full"
                        style={{
                          backgroundColor: getPriorityColor(item.priority) + '20',
                          color: getPriorityColor(item.priority)
                        }}
                      >
                        {item.priority}
                      </span>
                    </div>
                    {item.description && (
                      <p 
                        className="text-sm mb-2"
                        style={themeColors ? { color: themeColors.textLight } : {}}
                      >
                        {item.description}
                      </p>
                    )}
                    
                    {/* Action Buttons */}
                    {item.action_type === 'approve' && item.action_data?.story_ids && (
                      <div className="flex items-center space-x-2 mt-2">
                        <button
                          onClick={() => handleItemAction(item.id, 'approve', item.action_data)}
                          className="px-3 py-1 text-sm rounded-lg transition-colors flex items-center space-x-1"
                          style={themeColors ? {
                            backgroundColor: themeColors.primary,
                            color: '#ffffff'
                          } : {
                            backgroundColor: '#3b82f6',
                            color: '#ffffff'
                          }}
                        >
                          <IoCheckmark size={16} />
                          <span>Approve</span>
                        </button>
                        <button
                          onClick={() => handleItemAction(item.id, 'archive', item.action_data)}
                          className="px-3 py-1 text-sm rounded-lg transition-colors flex items-center space-x-1"
                          style={themeColors ? {
                            backgroundColor: themeColors.primaryLight + '40',
                            color: themeColors.text
                          } : {
                            backgroundColor: '#e5e7eb',
                            color: '#374151'
                          }}
                        >
                          <IoArchive size={16} />
                          <span>Archive</span>
                        </button>
                        <button
                          onClick={() => handleDismiss(item.id)}
                          className="px-3 py-1 text-sm text-gray-500 hover:text-gray-700 rounded-lg transition-colors"
                        >
                          <IoClose size={16} />
                        </button>
                      </div>
                    )}
                    
                    {item.action_type === 'review' && (
                      <div className="flex items-center space-x-2 mt-2">
                        {item.action_data?.story_ids && (
                          <>
                            <button
                              onClick={() => handleItemAction(item.id, 'approve', item.action_data)}
                              className="px-3 py-1 text-sm rounded-lg transition-colors flex items-center space-x-1"
                              style={themeColors ? {
                                backgroundColor: themeColors.primary,
                                color: '#ffffff'
                              } : {
                                backgroundColor: '#3b82f6',
                                color: '#ffffff'
                              }}
                            >
                              <IoCheckmark size={16} />
                              <span>Approve</span>
                            </button>
                            <button
                              onClick={() => handleItemAction(item.id, 'archive', item.action_data)}
                              className="px-3 py-1 text-sm rounded-lg transition-colors flex items-center space-x-1"
                              style={themeColors ? {
                                backgroundColor: themeColors.primaryLight + '40',
                                color: themeColors.text
                              } : {
                                backgroundColor: '#e5e7eb',
                                color: '#374151'
                              }}
                            >
                              <IoArchive size={16} />
                              <span>Archive</span>
                            </button>
                          </>
                        )}
                        <button
                          onClick={() => handleDismiss(item.id)}
                          className="px-3 py-1 text-sm text-gray-500 hover:text-gray-700 rounded-lg transition-colors flex items-center space-x-1"
                        >
                          <IoClose size={16} />
                          <span>Dismiss</span>
                        </button>
                      </div>
                    )}
                    
                    {item.action_type === 're_authenticate' && (
                      <div className="flex items-center space-x-2 mt-2">
                        <a
                          href={item.action_data?.service === 'notion' 
                            ? '/auth/notion' 
                            : '/auth/google'}
                          className="px-3 py-1 text-sm rounded-lg transition-colors"
                          style={themeColors ? {
                            backgroundColor: themeColors.primary,
                            color: '#ffffff'
                          } : {
                            backgroundColor: '#3b82f6',
                            color: '#ffffff'
                          }}
                        >
                          Re-authenticate
                        </a>
                        <button
                          onClick={() => handleDismiss(item.id)}
                          className="px-3 py-1 text-sm text-gray-500 hover:text-gray-700 rounded-lg transition-colors flex items-center space-x-1"
                        >
                          <IoClose size={16} />
                          <span>Dismiss</span>
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </motion.div>
          ))
        )}
      </div>
    </div>
  );
};

export default AutomationChecklist;

