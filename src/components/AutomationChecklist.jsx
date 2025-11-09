import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { IoCheckmarkCircle, IoCloseCircle, IoAlertCircle, IoInformationCircle, IoRefresh, IoArchive, IoCheckmark, IoClose } from 'react-icons/io5';
import axios from 'axios';
import { API_BASE_URL } from '../utils/constants';
import { useTheme } from '../hooks/useTheme.jsx';

/**
 * Automation Checklist Component
 * Displays automated actions, warnings, and suggestions from background agents
 */
const AutomationChecklist = () => {
  const [checklist, setChecklist] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [summary, setSummary] = useState(null);
  const { themeColors } = useTheme();

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

  const triggerAgent = async (agentName, forceReprocess = false) => {
    try {
      // Show loading state
      setLoading(true);
      setError(null);
      
      // Add force_reprocess as query parameter if needed
      const url = `${API_BASE_URL}/api/checklist/agents/run/${agentName}${forceReprocess ? '?force_reprocess=true' : ''}`;
      const response = await axios.post(url);
      console.log(`${agentName} result:`, response.data);
      
      // Show success message with details
      const result = response.data;
      if (result.success !== false) {
        if (result.message) {
          // Show informational message with stats if available
          let message = result.message;
          if (result.stats && agentName === 'story_extraction') {
            message += `\n\n📊 Stats:\n- Total pages: ${result.stats.total_pages}\n- Pages processed: ${result.stats.pages_processed}\n- Stories extracted: ${result.stats.stories_extracted}`;
            if (result.stats.pages_skipped_already_processed > 0) {
              message += `\n- Pages skipped (already processed): ${result.stats.pages_skipped_already_processed}`;
            }
            if (result.stats.pages_skipped_too_old > 0) {
              message += `\n- Pages skipped (too old): ${result.stats.pages_skipped_too_old}`;
            }
          }
          alert(message);
        } else if (result.count > 0) {
          alert(`Success! ${result.count} story(s) extracted.`);
        } else if (agentName === 'story_extraction') {
          // For story extraction, show detailed info
          const message = result.message || `Processed ${result.pages_processed || 0} page(s). No stories found. Make sure your pages contain meeting notes with action items.`;
          alert(message);
        }
      } else {
        // Show error message
        alert(result.error || `Failed to run ${agentName}`);
      }
      
      // Reload checklist after a short delay to see results
      setTimeout(() => {
        loadChecklist();
        loadSummary();
        setLoading(false);
      }, 2000);
      return response.data;
    } catch (err) {
      console.error(`Error triggering ${agentName}:`, err);
      setLoading(false);
      const errorMsg = err.response?.data?.detail || err.response?.data?.error || err.message || `Failed to run ${agentName}. Check console for details.`;
      alert(errorMsg);
      setError(errorMsg);
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
      
      // Reload checklist after a short delay
      setTimeout(() => {
        loadChecklist();
        loadSummary();
      }, 500);
    } catch (err) {
      console.error('Error handling item action:', err);
      const errorMsg = err.response?.data?.detail || err.message || 'Failed to process action. Please try again.';
      alert(errorMsg);
    }
  };

  const handleDismiss = async (itemId) => {
    try {
      await axios.post(`${API_BASE_URL}/api/checklist/items/${itemId}/action`, {
        action: 'dismiss'
      });
      
      loadChecklist();
      loadSummary();
    } catch (err) {
      console.error('Error dismissing item:', err);
      alert('Failed to dismiss item. Please try again.');
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

      {/* Summary */}
      {summary && (
        <div className="mb-4 p-4 rounded-lg" style={themeColors ? { backgroundColor: themeColors.primaryLight + '20' } : { backgroundColor: '#f3f4f6' }}>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <div 
                className="font-medium"
                style={themeColors ? { color: themeColors.text } : {}}
              >
                Pending Items
              </div>
              <div 
                className="text-2xl font-bold"
                style={themeColors ? { color: themeColors.primary } : {}}
              >
                {summary.pending_items || 0}
              </div>
            </div>
            <div>
              <div 
                className="font-medium"
                style={themeColors ? { color: themeColors.text } : {}}
              >
                Backlog Health
              </div>
              <div 
                className="text-2xl font-bold"
                style={themeColors ? { color: themeColors.primary } : {}}
              >
                {Math.round(summary.backlog_health_score || 100)}
              </div>
            </div>
            <div>
              <div 
                className="font-medium"
                style={themeColors ? { color: themeColors.text } : {}}
              >
                Stakeholders
              </div>
              <div 
                className="text-2xl font-bold"
                style={themeColors ? { color: themeColors.primary } : {}}
              >
                {summary.stakeholders_needing_attention || 0}
              </div>
            </div>
            <div>
              <div 
                className="font-medium"
                style={themeColors ? { color: themeColors.text } : {}}
              >
                Reports Ready
              </div>
              <div 
                className="text-2xl font-bold"
                style={themeColors ? { color: themeColors.primary } : {}}
              >
                {summary.ready_reports || 0}
              </div>
            </div>
          </div>
          
          {/* Test Agents Button - Show when everything is 0 */}
          {(summary.pending_items === 0 && summary.stakeholders_needing_attention === 0 && summary.ready_reports === 0) && (
            <div className="mt-4 pt-4 border-t" style={themeColors ? { borderColor: themeColors.primaryLight + '40' } : { borderColor: '#e5e7eb' }}>
              <p 
                className="text-sm mb-2"
                style={themeColors ? { color: themeColors.textLight } : {}}
              >
                No data yet. Trigger agents to test the system:
              </p>
              <div className="flex flex-wrap gap-2">
                <button
                  onClick={() => triggerAgent('story_extraction', false)}
                  className="px-3 py-1 text-xs rounded-lg transition-colors"
                  style={themeColors ? {
                    backgroundColor: themeColors.primaryLight + '40',
                    color: themeColors.text,
                  } : {
                    backgroundColor: '#e5e7eb',
                    color: '#374151',
                  }}
                  title="Extract stories from new/updated Notion pages"
                >
                  Extract Stories
                </button>
                <button
                  onClick={() => triggerAgent('story_extraction', true)}
                  className="px-3 py-1 text-xs rounded-lg transition-colors font-semibold"
                  style={themeColors ? {
                    backgroundColor: themeColors.primary,
                    color: '#ffffff',
                  } : {
                    backgroundColor: '#3b82f6',
                    color: '#ffffff',
                  }}
                  title="Force reprocess all pages (even if already processed) - will extract all stories again"
                >
                  Force Reprocess
                </button>
                <button
                  onClick={() => triggerAgent('noise_clearing')}
                  className="px-3 py-1 text-xs rounded-lg transition-colors"
                  style={themeColors ? {
                    backgroundColor: themeColors.primaryLight + '40',
                    color: themeColors.text,
                  } : {
                    backgroundColor: '#e5e7eb',
                    color: '#374151',
                  }}
                  title="Audit backlog for duplicates and low-priority items"
                >
                  Audit Backlog
                </button>
                <button
                  onClick={() => triggerAgent('stakeholder_mapping')}
                  className="px-3 py-1 text-xs rounded-lg transition-colors"
                  style={themeColors ? {
                    backgroundColor: themeColors.primaryLight + '40',
                    color: themeColors.text,
                  } : {
                    backgroundColor: '#e5e7eb',
                    color: '#374151',
                  }}
                  title="Map stakeholders from stories"
                >
                  Map Stakeholders
                </button>
                <button
                  onClick={() => triggerAgent('integration_health')}
                  className="px-3 py-1 text-xs rounded-lg transition-colors"
                  style={themeColors ? {
                    backgroundColor: themeColors.primaryLight + '40',
                    color: themeColors.text,
                  } : {
                    backgroundColor: '#e5e7eb',
                    color: '#374151',
                  }}
                  title="Check integration health (Notion, Google Calendar, Gemini)"
                >
                  Check Health
                </button>
              </div>
              <p 
                className="text-xs mt-2"
                style={themeColors ? { color: themeColors.textLight } : {}}
              >
                Note: Story extraction requires Notion pages with meeting notes. Make sure Notion is connected.
              </p>
            </div>
          )}
        </div>
      )}

      {/* Checklist Items */}
      <div className="space-y-3">
        {items.length === 0 ? (
          <div 
            className="text-center py-8"
            style={themeColors ? { color: themeColors.textLight } : {}}
          >
            <p>No pending items. All caught up! 🎉</p>
          </div>
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

