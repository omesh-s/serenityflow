import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { IoChevronDown, IoChevronUp, IoCheckmarkCircle, IoAlertCircle, IoInformationCircle } from 'react-icons/io5';
import { useTheme } from '../hooks/useTheme.jsx';
import { hexToRgba } from '../utils/hexToRgb';

/**
 * Meeting Ended Results Component
 * Displays results from all 6 PM workflow agents
 */
const MeetingEndedResults = ({ results, onClose }) => {
  const { themeColors } = useTheme();
  const [expandedCards, setExpandedCards] = useState({});

  const toggleCard = (cardId) => {
    setExpandedCards(prev => ({
      ...prev,
      [cardId]: !prev[cardId]
    }));
  };

  if (!results || !results.outputs) {
    return null;
  }

  const outputs = results.outputs;
  const summary = results.summary || {};

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className="glass-card p-6 max-w-6xl w-full max-h-[90vh] overflow-y-auto"
        style={{
          background: themeColors 
            ? `linear-gradient(135deg, ${hexToRgba(themeColors.backgroundStart, 0.95)} 0%, ${hexToRgba(themeColors.backgroundEnd, 0.95)} 100%)`
            : 'rgba(255, 255, 255, 0.95)',
        }}
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <h2 
            className="text-2xl font-bold"
            style={{ color: themeColors?.text || '#075985' }}
          >
            🏁 Meeting Ended - Automation Complete
          </h2>
          <button
            onClick={onClose}
            className="text-2xl hover:opacity-70 transition-opacity"
            style={{ color: themeColors?.textLight || '#0284c7' }}
          >
            ×
          </button>
        </div>

        {/* Summary Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <StatCard 
            label="Stories Extracted" 
            value={summary.stories_extracted || 0}
            themeColors={themeColors}
          />
          <StatCard 
            label="Database Entries" 
            value={summary.database_entries_created || 0}
            themeColors={themeColors}
          />
          <StatCard 
            label="Action Items" 
            value={summary.action_items_total || 0}
            themeColors={themeColors}
          />
          <StatCard 
            label="Processing Time" 
            value={`${results.processing_time_seconds || 0}s`}
            themeColors={themeColors}
          />
        </div>

        {/* Report Page Link and Status */}
        {summary.report_page_url && (
          <div className="mb-6 p-4 rounded-lg" style={{ backgroundColor: hexToRgba(themeColors?.primaryLight || '#e0f2fe', 0.2) }}>
            <div className="flex items-center justify-between">
              <div>
                <p className="font-semibold mb-1" style={{ color: themeColors?.text || '#075985' }}>
                  📄 Full Report Page
                </p>
                <a 
                  href={summary.report_page_url} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="text-sm underline"
                  style={{ color: themeColors?.primary || '#0284c7' }}
                >
                  {summary.report_page_title || 'Meeting Ended Report'}
                </a>
              </div>
              {summary.database_entries_created > 0 && (
                <div className="text-right">
                  <p className="font-semibold" style={{ color: themeColors?.text || '#075985' }}>
                    ✅ {summary.database_entries_created} stories auto-created in Backlog Database
                  </p>
                </div>
              )}
            </div>
            {summary.stories_pending_review > 0 && (
              <p className="mt-2 text-sm" style={{ color: themeColors?.textLight || '#0284c7' }}>
                ⚠️ {summary.stories_pending_review} stories need review (see report page)
              </p>
            )}
          </div>
        )}

        {/* Result Cards */}
        <div className="space-y-4">
          {/* 1. Customer & Market Research */}
          {outputs.customer_research && outputs.customer_research.success !== false && (
            <ResultCard
              title="Customer & Market Research"
              icon={<IoInformationCircle />}
              data={outputs.customer_research}
              themeColors={themeColors}
              isExpanded={expandedCards.customer_research}
              onToggle={() => toggleCard('customer_research')}
            >
              <CustomerResearchView data={outputs.customer_research} themeColors={themeColors} />
            </ResultCard>
          )}

          {/* 2. Backlog Grooming */}
          {outputs.backlog_grooming && outputs.backlog_grooming.success && (
            <ResultCard
              title="Backlog Grooming"
              icon={<IoCheckmarkCircle />}
              data={outputs.backlog_grooming}
              themeColors={themeColors}
              isExpanded={expandedCards.backlog_grooming}
              onToggle={() => toggleCard('backlog_grooming')}
            >
              <BacklogGroomingView data={outputs.backlog_grooming} themeColors={themeColors} />
            </ResultCard>
          )}

          {/* 3. Cross-Team Updates */}
          {outputs.cross_team_updates && outputs.cross_team_updates.success && (
            <ResultCard
              title="Cross-Team Updates"
              icon={<IoInformationCircle />}
              data={outputs.cross_team_updates}
              themeColors={themeColors}
              isExpanded={expandedCards.cross_team_updates}
              onToggle={() => toggleCard('cross_team_updates')}
            >
              <CrossTeamView data={outputs.cross_team_updates} themeColors={themeColors} />
            </ResultCard>
          )}

          {/* 4. Meeting Insights */}
          {outputs.meeting_insights && outputs.meeting_insights.success && (
            <ResultCard
              title="Meeting Insights"
              icon={<IoInformationCircle />}
              data={outputs.meeting_insights}
              themeColors={themeColors}
              isExpanded={expandedCards.meeting_insights}
              onToggle={() => toggleCard('meeting_insights')}
            >
              <MeetingInsightsView data={outputs.meeting_insights} themeColors={themeColors} />
            </ResultCard>
          )}

          {/* 5. Reporting & Release Notes */}
          {outputs.reporting && outputs.reporting.success && (
            <ResultCard
              title="Reports & Release Notes"
              icon={<IoCheckmarkCircle />}
              data={outputs.reporting}
              themeColors={themeColors}
              isExpanded={expandedCards.reporting}
              onToggle={() => toggleCard('reporting')}
            >
              <ReportingView data={outputs.reporting} themeColors={themeColors} />
            </ResultCard>
          )}

          {/* 6. Sprint Planning */}
          {outputs.sprint_planning && outputs.sprint_planning.success !== false && (
            <ResultCard
              title="Sprint Planning"
              icon={<IoCheckmarkCircle />}
              data={outputs.sprint_planning}
              themeColors={themeColors}
              isExpanded={expandedCards.sprint_planning}
              onToggle={() => toggleCard('sprint_planning')}
            >
              <SprintPlanningView data={outputs.sprint_planning} themeColors={themeColors} />
            </ResultCard>
          )}
        </div>
      </motion.div>
    </div>
  );
};

// Stat Card Component
const StatCard = ({ label, value, themeColors }) => (
  <div 
    className="p-4 rounded-lg text-center"
    style={{
      backgroundColor: themeColors ? hexToRgba(themeColors.primaryLight, 0.2) : '#e0f2fe',
      border: `1px solid ${themeColors ? hexToRgba(themeColors.primary, 0.3) : '#7dd3fc'}`
    }}
  >
    <div 
      className="text-2xl font-bold mb-1"
      style={{ color: themeColors?.primary || '#0284c7' }}
    >
      {value}
    </div>
    <div 
      className="text-xs"
      style={{ color: themeColors?.textLight || '#0ea5e9' }}
    >
      {label}
    </div>
  </div>
);

// Result Card Component
const ResultCard = ({ title, icon, data, themeColors, isExpanded, onToggle, children }) => (
  <div 
    className="rounded-lg border overflow-hidden"
    style={{
      borderColor: themeColors ? hexToRgba(themeColors.primary, 0.3) : '#7dd3fc',
      backgroundColor: themeColors ? hexToRgba(themeColors.backgroundStart, 0.5) : '#f8fafc'
    }}
  >
    <button
      onClick={onToggle}
      className="w-full p-4 flex items-center justify-between hover:opacity-80 transition-opacity"
      style={{
        backgroundColor: themeColors ? hexToRgba(themeColors.primaryLight, 0.1) : '#e0f2fe'
      }}
    >
      <div className="flex items-center space-x-3">
        <div style={{ color: themeColors?.primary || '#0284c7' }}>
          {icon}
        </div>
        <h3 
          className="text-lg font-semibold"
          style={{ color: themeColors?.text || '#075985' }}
        >
          {title}
        </h3>
      </div>
      {isExpanded ? <IoChevronUp /> : <IoChevronDown />}
    </button>
    <AnimatePresence>
      {isExpanded && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: 'auto', opacity: 1 }}
          exit={{ height: 0, opacity: 0 }}
          className="overflow-hidden"
        >
          <div className="p-4">
            {children}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  </div>
);

// View Components for each agent output
const CustomerResearchView = ({ data, themeColors }) => (
  <div className="space-y-4">
    {data.customer_themes && data.customer_themes.length > 0 && (
      <div>
        <h4 className="font-semibold mb-2" style={{ color: themeColors?.text }}>Customer Themes</h4>
        {data.customer_themes.slice(0, 3).map((theme, idx) => (
          <div key={idx} className="mb-3 p-3 rounded" style={{ backgroundColor: hexToRgba(themeColors?.primaryLight || '#e0f2fe', 0.2) }}>
            <div className="font-medium" style={{ color: themeColors?.text }}>{theme.theme}</div>
            {theme.pain_points && theme.pain_points.length > 0 && (
              <div className="text-sm mt-1" style={{ color: themeColors?.textLight }}>
                Pain points: {theme.pain_points.slice(0, 2).join(', ')}
              </div>
            )}
          </div>
        ))}
      </div>
    )}
    {data.executive_brief && (
      <div>
        <h4 className="font-semibold mb-2" style={{ color: themeColors?.text }}>Executive Brief</h4>
        <p className="text-sm" style={{ color: themeColors?.textLight }}>{data.executive_brief}</p>
      </div>
    )}
    {data.product_bets && data.product_bets.length > 0 && (
      <div>
        <h4 className="font-semibold mb-2" style={{ color: themeColors?.text }}>Product Bets</h4>
        <ul className="list-disc list-inside text-sm space-y-1" style={{ color: themeColors?.textLight }}>
          {data.product_bets.map((bet, idx) => (
            <li key={idx}>{bet}</li>
          ))}
        </ul>
      </div>
    )}
  </div>
);

const BacklogGroomingView = ({ data, themeColors }) => (
  <div className="space-y-4">
    <div className="grid grid-cols-3 gap-4">
      <StatItem label="Health Score" value={`${data.health_score || 0}/100`} themeColors={themeColors} />
      <StatItem label="Clusters" value={data.clusters?.length || 0} themeColors={themeColors} />
      <StatItem label="Duplicates" value={data.duplicate_count || 0} themeColors={themeColors} />
    </div>
    {data.clusters && data.clusters.length > 0 && (
      <div>
        <h4 className="font-semibold mb-2" style={{ color: themeColors?.text }}>Clustered Stories</h4>
        {data.clusters.slice(0, 3).map((cluster, idx) => (
          <div key={idx} className="mb-3 p-3 rounded" style={{ backgroundColor: hexToRgba(themeColors?.primaryLight || '#e0f2fe', 0.2) }}>
            <div className="font-medium" style={{ color: themeColors?.text }}>{cluster.cluster_name}</div>
            {cluster.canonical_story && (
              <div className="text-sm mt-1" style={{ color: themeColors?.textLight }}>
                {cluster.canonical_story.title}
              </div>
            )}
          </div>
        ))}
      </div>
    )}
  </div>
);

const CrossTeamView = ({ data, themeColors }) => (
  <div className="space-y-4">
    {data.overall_status && (
      <div>
        <h4 className="font-semibold mb-2" style={{ color: themeColors?.text }}>Overall Status</h4>
        <p className="text-sm" style={{ color: themeColors?.textLight }}>{data.overall_status}</p>
      </div>
    )}
    {data.team_highlights && data.team_highlights.length > 0 && (
      <div>
        <h4 className="font-semibold mb-2" style={{ color: themeColors?.text }}>Team Highlights</h4>
        {data.team_highlights.slice(0, 3).map((team, idx) => (
          <div key={idx} className="mb-3">
            <div className="font-medium" style={{ color: themeColors?.text }}>{team.team}</div>
            {team.wins && team.wins.length > 0 && (
              <div className="text-sm" style={{ color: themeColors?.textLight }}>
                Wins: {team.wins.slice(0, 2).join(', ')}
              </div>
            )}
          </div>
        ))}
      </div>
    )}
    {data.risks && data.risks.length > 0 && (
      <div>
        <h4 className="font-semibold mb-2" style={{ color: themeColors?.text }}>Risks</h4>
        <ul className="list-disc list-inside text-sm space-y-1" style={{ color: themeColors?.textLight }}>
          {data.risks.slice(0, 3).map((risk, idx) => (
            <li key={idx}>{risk}</li>
          ))}
        </ul>
      </div>
    )}
  </div>
);

const MeetingInsightsView = ({ data, themeColors }) => (
  <div className="space-y-4">
    {data.meetings && data.meetings.length > 0 && (
      <div>
        <h4 className="font-semibold mb-2" style={{ color: themeColors?.text }}>
          {data.total_meetings || data.meetings.length} Meeting(s) Analyzed
        </h4>
        {data.meetings.slice(0, 3).map((meeting, idx) => (
          <div key={idx} className="mb-3 p-3 rounded" style={{ backgroundColor: hexToRgba(themeColors?.primaryLight || '#e0f2fe', 0.2) }}>
            <div className="font-medium" style={{ color: themeColors?.text }}>{meeting.meeting_title}</div>
            {meeting.summary && meeting.summary.length > 0 && (
              <ul className="text-sm mt-1 list-disc list-inside" style={{ color: themeColors?.textLight }}>
                {meeting.summary.slice(0, 3).map((item, i) => (
                  <li key={i}>{item}</li>
                ))}
              </ul>
            )}
            {meeting.action_items && meeting.action_items.length > 0 && (
              <div className="text-sm mt-2" style={{ color: themeColors?.textLight }}>
                {meeting.action_items.length} action item(s)
              </div>
            )}
          </div>
        ))}
      </div>
    )}
  </div>
);

const ReportingView = ({ data, themeColors }) => (
  <div className="space-y-4">
    {data.weekly_executive_update && (
      <div>
        <h4 className="font-semibold mb-2" style={{ color: themeColors?.text }}>Weekly Executive Update</h4>
        <p className="text-sm" style={{ color: themeColors?.textLight }}>{data.weekly_executive_update}</p>
      </div>
    )}
    {data.release_notes && (
      <div>
        <h4 className="font-semibold mb-2" style={{ color: themeColors?.text }}>Release Notes</h4>
        <div className="text-sm" style={{ color: themeColors?.textLight }}>
          <div className="font-medium">{data.release_notes.version} - {data.release_notes.date}</div>
          <p className="mt-1">{data.release_notes.summary}</p>
          {data.release_notes.highlights && data.release_notes.highlights.length > 0 && (
            <ul className="list-disc list-inside mt-2 space-y-1">
              {data.release_notes.highlights.slice(0, 3).map((highlight, idx) => (
                <li key={idx}>{highlight}</li>
              ))}
            </ul>
          )}
        </div>
      </div>
    )}
  </div>
);

const SprintPlanningView = ({ data, themeColors }) => (
  <div className="space-y-4">
    {data.sprint_goal && (
      <div>
        <h4 className="font-semibold mb-2" style={{ color: themeColors?.text }}>Sprint Goal</h4>
        <p className="text-sm" style={{ color: themeColors?.textLight }}>{data.sprint_goal}</p>
      </div>
    )}
    {data.sprint_scope && data.sprint_scope.length > 0 && (
      <div>
        <h4 className="font-semibold mb-2" style={{ color: themeColors?.text }}>
          Sprint Scope ({data.total_points || 0} points)
        </h4>
        <ul className="list-disc list-inside text-sm space-y-1" style={{ color: themeColors?.textLight }}>
          {data.sprint_scope.map((item, idx) => (
            <li key={idx}>{item.title} ({item.points} pts)</li>
          ))}
        </ul>
      </div>
    )}
    {data.major_risks && data.major_risks.length > 0 && (
      <div>
        <h4 className="font-semibold mb-2" style={{ color: themeColors?.text }}>Major Risks</h4>
        <ul className="list-disc list-inside text-sm space-y-1" style={{ color: themeColors?.textLight }}>
          {data.major_risks.slice(0, 3).map((risk, idx) => (
            <li key={idx}>{risk}</li>
          ))}
        </ul>
      </div>
    )}
  </div>
);

const StatItem = ({ label, value, themeColors }) => (
  <div className="text-center">
    <div className="text-lg font-bold" style={{ color: themeColors?.primary || '#0284c7' }}>
      {value}
    </div>
    <div className="text-xs" style={{ color: themeColors?.textLight || '#0ea5e9' }}>
      {label}
    </div>
  </div>
);

export default MeetingEndedResults;

