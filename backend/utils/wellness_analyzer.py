"""Wellness analytics for Notion notes with Gemini AI analysis."""
import re
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
from collections import Counter, defaultdict
import json
from dateutil import parser as date_parser
from dateutil import tz
from config import settings
import google.generativeai as genai


# Stress-indicating keywords
STRESS_KEYWORDS = [
    'blocked', 'urgent', 'deadline', 'overdue', 'stuck', 'problem', 'issue',
    'error', 'bug', 'broken', 'failed', 'worry', 'anxious', 'stress', 'pressure',
    'difficult', 'challenge', 'trouble', 'conflict', 'frustrated', 'overwhelmed',
    'exhausted', 'tired', 'burnout', 'hectic', 'chaos', 'mess', 'disaster'
]

# Positive keywords
POSITIVE_KEYWORDS = [
    'completed', 'done', 'finished', 'achieved', 'success', 'great', 'excellent',
    'progress', 'improved', 'solved', 'resolved', 'accomplished', 'happy', 'excited',
    'pleased', 'satisfied', 'grateful', 'productive', 'efficient', 'organized',
    'clear', 'focused', 'motivated', 'energized', 'optimistic', 'confident'
]

# Status weights for wellness score (higher = better)
STATUS_WEIGHTS = {
    'completed': 1.0,
    'done': 1.0,
    'finished': 1.0,
    'under review': 0.7,
    'in progress': 0.6,
    'todo': 0.4,
    'unfinished': 0.3,
    'pending': 0.3,
    'urgent': 0.2,
    'blocked': 0.1,
    'cancelled': 0.5,
}


def extract_note_content(page: Dict) -> str:
    """Extract text content from a Notion page."""
    content_parts = []
    
    # Try to get title from properties
    if 'properties' in page:
        for prop_name, prop_data in page['properties'].items():
            if prop_data.get('type') == 'title' and prop_data.get('title'):
                content_parts.append(' '.join([rt.get('plain_text', '') for rt in prop_data['title']]))
    
    # Try to get rich text properties
    if 'properties' in page:
        for prop_name, prop_data in page['properties'].items():
            if prop_data.get('type') == 'rich_text' and prop_data.get('rich_text'):
                content_parts.append(' '.join([rt.get('plain_text', '') for rt in prop_data['rich_text']]))
    
    return ' '.join(content_parts).lower()


def extract_note_status(page: Dict) -> str:
    """Extract status from a Notion page."""
    if 'properties' in page:
        for prop_name, prop_data in page['properties'].items():
            # Check for status property
            if prop_data.get('type') == 'status' and prop_data.get('status'):
                return prop_data['status'].get('name', '').lower()
            
            # Check for select property (often used for status)
            if prop_data.get('type') == 'select' and prop_data.get('select'):
                return prop_data['select'].get('name', '').lower()
            
            # Check for checkbox (completed/done)
            if prop_data.get('type') == 'checkbox' and prop_data.get('checkbox'):
                return 'completed' if prop_data['checkbox'] else 'unfinished'
    
    # Default status based on archived state
    if page.get('archived', False):
        return 'completed'
    
    return 'unfinished'


def extract_note_timestamp(page: Dict) -> datetime:
    """Extract timestamp from a Notion page."""
    # Try created_time first
    if 'created_time' in page:
        try:
            return datetime.fromisoformat(page['created_time'].replace('Z', '+00:00'))
        except:
            pass
    
    # Fallback to last_edited_time
    if 'last_edited_time' in page:
        try:
            return datetime.fromisoformat(page['last_edited_time'].replace('Z', '+00:00'))
        except:
            pass
    
    # Default to now
    return datetime.utcnow()


def count_keywords(text: str, keywords: List[str]) -> int:
    """Count occurrences of keywords in text."""
    text_lower = text.lower()
    count = 0
    for keyword in keywords:
        # Use word boundaries to match whole words
        pattern = r'\b' + re.escape(keyword) + r'\b'
        count += len(re.findall(pattern, text_lower))
    return count


def calculate_wellness_score(notes: List[Dict]) -> float:
    """Calculate wellness score (0-100) based on notes."""
    if not notes:
        return 50.0  # Neutral score for no data
    
    total_score = 0.0
    max_possible_score = 0.0
    
    for note in notes:
        content = extract_note_content(note)
        status = extract_note_status(note)
        
        # Base score from status (0-1)
        status_score = STATUS_WEIGHTS.get(status, 0.5)
        
        # Adjust based on keywords
        stress_count = count_keywords(content, STRESS_KEYWORDS)
        positive_count = count_keywords(content, POSITIVE_KEYWORDS)
        
        # Keyword adjustment (-0.1 per stress keyword, +0.05 per positive keyword)
        keyword_adjustment = min(0.3, (positive_count * 0.05) - (stress_count * 0.1))
        status_score = max(0.0, min(1.0, status_score + keyword_adjustment))
        
        # Length factor (longer notes might indicate more thought/engagement)
        content_length = len(content)
        if content_length > 0:
            length_factor = min(1.0, content_length / 500)  # Normalize to 500 chars
            status_score = status_score * (0.7 + 0.3 * length_factor)
        
        total_score += status_score
        max_possible_score += 1.0
    
    # Calculate average and scale to 0-100
    if max_possible_score > 0:
        average_score = total_score / max_possible_score
        wellness_score = average_score * 100
    else:
        wellness_score = 50.0
    
    return round(wellness_score, 1)


def calculate_completion_rate(notes: List[Dict]) -> float:
    """Calculate completion rate as percentage."""
    if not notes:
        return 0.0
    
    completed_count = 0
    total_count = len(notes)
    
    for note in notes:
        status = extract_note_status(note)
        if status in ['completed', 'done', 'finished']:
            completed_count += 1
    
    completion_rate = (completed_count / total_count) * 100
    return round(completion_rate, 1)


def find_peak_productivity_hours(notes: List[Dict]) -> str:
    """Find the 2-hour window with most note entries."""
    if not notes:
        return "No data available"
    
    # Group notes by hour
    hour_counts = defaultdict(int)
    
    for note in notes:
        timestamp = extract_note_timestamp(note)
        hour = timestamp.hour
        hour_counts[hour] += 1
    
    if not hour_counts:
        return "No data available"
    
    # Find the 2-hour window with most entries
    # Try all possible 2-hour windows (can wrap around midnight)
    max_count = 0
    best_start_hour = 0
    
    # Try all 24 possible starting hours
    for start_hour in range(24):
        # Count notes in 2-hour window
        window_count = 0
        for offset in range(2):
            hour = (start_hour + offset) % 24
            window_count += hour_counts.get(hour, 0)
        
        if window_count > max_count:
            max_count = window_count
            best_start_hour = start_hour
    
    # Format as time range
    def format_hour(h):
        if h == 0:
            return "12:00 AM"
        elif h < 12:
            return f"{h}:00 AM"
        elif h == 12:
            return "12:00 PM"
        else:
            return f"{h - 12}:00 PM"
    
    start_str = format_hour(best_start_hour)
    end_hour = (best_start_hour + 2) % 24
    end_str = format_hour(end_hour)
    
    return f"{start_str} - {end_str}"


def generate_insights(notes: List[Dict]) -> List[str]:
    """Generate informative but concise insights and trends from notes (fallback)."""
    insights = []
    
    if not notes:
        insights.append("No notes available for analysis. Start tracking tasks in Notion to get wellness insights.")
        return insights[:4]
    
    # Status distribution
    status_counts = Counter()
    total_stress_keywords = 0
    total_positive_keywords = 0
    total_content_length = 0
    
    for note in notes:
        status = extract_note_status(note)
        status_counts[status] += 1
        
        content = extract_note_content(note)
        total_stress_keywords += count_keywords(content, STRESS_KEYWORDS)
        total_positive_keywords += count_keywords(content, POSITIVE_KEYWORDS)
        total_content_length += len(content)
    
    # Completion rate insight (informative)
    completed = status_counts.get('completed', 0) + status_counts.get('done', 0) + status_counts.get('finished', 0)
    total = len(notes)
    completion_rate = (completed / total * 100) if total > 0 else 0
    
    if completion_rate >= 70:
        insights.append(f"Completion rate is strong at {completion_rate:.0f}%. Keep up the great work finishing tasks!")
    elif completion_rate >= 50:
        insights.append(f"Completion rate is moderate at {completion_rate:.0f}%. Focus on finishing more tasks to boost productivity.")
    else:
        insights.append(f"Completion rate is {completion_rate:.0f}%. Try to complete more tasks to improve your wellness score.")
    
    # Activity level insight (informative)
    if len(notes) >= 20:
        insights.append(f"High engagement with {len(notes)} notes this week. Your consistent tracking helps identify productivity patterns.")
    elif len(notes) >= 10:
        insights.append(f"Good note consistency with {len(notes)} notes. Continue tracking to build better insights over time.")
    else:
        insights.append(f"Only {len(notes)} notes tracked. Increase tracking frequency to get more meaningful wellness insights.")
    
    # Stress/positivity insight (informative)
    if total_positive_keywords > total_stress_keywords * 2:
        insights.append("Positive mindset detected in your notes. Your optimistic outlook supports better wellness and productivity.")
    elif total_stress_keywords > len(notes) * 0.5:
        stress_ratio = (total_stress_keywords / len(notes)) if len(notes) > 0 else 0
        insights.append(f"Stress indicators detected ({total_stress_keywords} stress keywords). Consider taking more breaks and practicing mindfulness.")
    else:
        insights.append("Your notes show a balanced tone. Maintain this balance for optimal wellness and productivity.")
    
    # Wellness score context
    avg_length = total_content_length / len(notes) if len(notes) > 0 else 0
    if avg_length > 100:
        insights.append(f"Your notes are detailed (avg {avg_length:.0f} chars), showing thoughtful tracking and engagement.")
    
    # Return top 4 insights, limit to 120 chars each
    return [insight[:120] for insight in insights[:4]]


def analyze_notes_batch_gemini(notes_content: List[Tuple[str, str]]) -> List[Tuple[float, float]]:
    """Use Gemini to analyze sentiment and clarity for multiple notes in a single batch call.
    
    Args:
        notes_content: List of tuples (note_id, note_content)
    
    Returns:
        List of tuples (sentiment, clarity) in same order as input
    """
    try:
        if not settings.gemini_api_key or not notes_content:
            # Fallback to keyword-based analysis
            return [(analyze_sentiment_keywords(content), analyze_clarity_keywords(content)) 
                   for _, content in notes_content]
        
        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel('gemini-2.5-flash-lite')
        
        # Prepare batch prompt with all notes
        notes_list = []
        for i, (note_id, content) in enumerate(notes_content[:10]):  # Limit to 10 notes per batch
            truncated_content = content[:500]  # Truncate each note to 500 chars
            notes_list.append(f"Note {i+1} (ID: {note_id[:8]}...): {truncated_content}")
        
        notes_text = "\n\n".join(notes_list)
        
        prompt = f"""Analyze the following notes and provide a JSON response with sentiment and clarity scores for each.

Notes:
{notes_text}

For each note, provide:
- sentiment: float between 0.0 (very negative/stressful) and 1.0 (very positive/calm)
- clarity: float between 0.0 (rushed/terse/disorganized) and 1.0 (detailed/clear/well-organized)

Return a JSON array with objects in the same order as the notes:
[
  {{"sentiment": 0.75, "clarity": 0.60}},
  {{"sentiment": 0.65, "clarity": 0.70}},
  ...
]

Return ONLY valid JSON array, no additional text."""
        
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        # Extract JSON from response
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        results = json.loads(response_text)
        if not isinstance(results, list):
            results = [results]
        
        # Process results
        analyzed = []
        for i, result in enumerate(results):
            if isinstance(result, dict):
                sentiment = float(result.get("sentiment", 0.5))
                clarity = float(result.get("clarity", 0.5))
                analyzed.append((max(0.0, min(1.0, sentiment)), max(0.0, min(1.0, clarity))))
            else:
                # Fallback for invalid result
                analyzed.append((0.5, 0.5))
        
        # Fill in missing results with keyword-based analysis
        while len(analyzed) < len(notes_content):
            idx = len(analyzed)
            if idx < len(notes_content):
                content = notes_content[idx][1]
                analyzed.append((analyze_sentiment_keywords(content), analyze_clarity_keywords(content)))
        
        return analyzed[:len(notes_content)]
    except Exception as e:
        print(f"Error in batch Gemini analysis: {str(e)}")
        # Fallback to keyword-based analysis for all notes
        return [(analyze_sentiment_keywords(content), analyze_clarity_keywords(content)) 
               for _, content in notes_content]


def analyze_sentiment_keywords(content: str) -> float:
    """Fallback sentiment analysis using keywords."""
    if not content:
        return 0.5
    
    stress_count = count_keywords(content, STRESS_KEYWORDS)
    positive_count = count_keywords(content, POSITIVE_KEYWORDS)
    
    # Base sentiment
    sentiment = 0.5
    sentiment += positive_count * 0.1
    sentiment -= stress_count * 0.15
    
    return max(0.0, min(1.0, sentiment))


def analyze_clarity_keywords(content: str) -> float:
    """Fallback clarity analysis using content characteristics."""
    if not content:
        return 0.5
    
    # Indicators of clarity
    clarity = 0.5
    
    # Length indicates thoughtfulness (but not too long = rambling)
    word_count = len(content.split())
    if 20 <= word_count <= 200:
        clarity += 0.2
    elif word_count < 10:
        clarity -= 0.3  # Very short = rushed/terse
    
    # Check for organization indicators
    if any(indicator in content.lower() for indicator in ['first', 'second', 'then', 'finally', 'step', 'task']):
        clarity += 0.1
    
    # Check for disorganization indicators
    if any(indicator in content.lower() for indicator in ['um', 'uh', 'idk', '???', '...']):
        clarity -= 0.2
    
    return max(0.0, min(1.0, clarity))


def calculate_engagement_score(notes: List[Dict]) -> float:
    """Calculate engagement score (0-100) based on activity patterns."""
    if not notes:
        return 0.0
    
    # Get timestamps for all notes
    timestamps = []
    for note in notes:
        ts = extract_note_timestamp(note)
        if ts:
            timestamps.append(ts)
    
    if not timestamps:
        return 0.0
    
    # Calculate active days (last 7 days)
    now = datetime.utcnow()
    seven_days_ago = now - timedelta(days=7)
    
    active_days = set()
    recent_notes = 0
    total_length = 0
    
    for ts in timestamps:
        # Make timezone-naive for comparison
        if ts.tzinfo:
            ts = ts.astimezone(tz.UTC).replace(tzinfo=None)
        
        if ts >= seven_days_ago:
            recent_notes += 1
            active_days.add(ts.date())
            # Get note content length
            for note in notes:
                note_ts = extract_note_timestamp(note)
                if note_ts and note_ts.date() == ts.date():
                    content = extract_note_content(note)
                    total_length += len(content)
                    break
    
    # Calculate components
    active_days_count = len(active_days)
    max_active_days = 7
    active_days_score = (active_days_count / max_active_days) * 30  # 30 points max
    
    # Frequency score (notes per day)
    if active_days_count > 0:
        avg_notes_per_day = recent_notes / active_days_count
        frequency_score = min(30, (avg_notes_per_day / 5) * 30)  # 30 points max, 5 notes/day = full score
    else:
        frequency_score = 0
    
    # Length score (average note length)
    if recent_notes > 0:
        avg_length = total_length / recent_notes
        length_score = min(20, (avg_length / 200) * 20)  # 20 points max, 200 chars = full score
    else:
        length_score = 0
    
    # Consistency score (how evenly distributed across days)
    if active_days_count >= 3:
        consistency_score = 20  # Full score if active 3+ days
    elif active_days_count == 2:
        consistency_score = 10
    elif active_days_count == 1:
        consistency_score = 5
    else:
        consistency_score = 0
    
    engagement_score = active_days_score + frequency_score + length_score + consistency_score
    return round(min(100.0, engagement_score), 1)


def calculate_active_days(notes: List[Dict], days: int = 7) -> int:
    """Calculate number of active days in the last N days."""
    if not notes:
        return 0
    
    now = datetime.utcnow()
    start_date = now - timedelta(days=days)
    
    active_days = set()
    for note in notes:
        ts = extract_note_timestamp(note)
        if ts:
            if ts.tzinfo:
                ts = ts.astimezone(tz.UTC).replace(tzinfo=None)
            if ts >= start_date:
                active_days.add(ts.date())
    
    return len(active_days)


def analyze_wellness_with_gemini(notes: List[Dict]) -> Dict:
    """Analyze notes using Gemini for sentiment and clarity, then calculate metrics."""
    if not notes:
        return {
            "wellness_score": 50.0,
            "completion_rate": 0.0,
            "peak_productivity_hours": "No data available",
            "insights": ["No notes available for analysis"],
            "engagement_score": 0.0,
            "active_days": 0,
            "total_notes": 0,
            "current_state": "neutral",
            "trend": "stable"
        }
    
    # Analyze sentiment and clarity for notes using Gemini (batched for efficiency)
    sentiment_scores = []
    clarity_scores = []
    
    # Limit to recent 10 notes to stay within Gemini rate limits (15 requests/min)
    # We'll analyze in 1 batch call instead of 10+ individual calls
    recent_notes = sorted(notes, key=lambda x: extract_note_timestamp(x), reverse=True)[:10]
    
    # Prepare notes for batch analysis
    notes_to_analyze = []
    for note in recent_notes:
        content = extract_note_content(note)
        if content and len(content) > 10:  # Only analyze notes with meaningful content
            note_id = note.get('id', 'unknown')
            notes_to_analyze.append((note_id, content))
    
    if notes_to_analyze:
        try:
            # Batch analyze all notes in a single Gemini API call
            results = analyze_notes_batch_gemini(notes_to_analyze)
            for sentiment, clarity in results:
                sentiment_scores.append(sentiment)
                clarity_scores.append(clarity)
        except Exception as e:
            print(f"Error in batch Gemini analysis: {str(e)}")
            # Fallback to keyword-based analysis
            for _, content in notes_to_analyze:
                sentiment_scores.append(analyze_sentiment_keywords(content))
                clarity_scores.append(analyze_clarity_keywords(content))
    else:
        # No notes to analyze, use defaults
        sentiment_scores = [0.5]
        clarity_scores = [0.5]
    
    # Calculate wellness score from sentiment and clarity
    avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0.5
    avg_clarity = sum(clarity_scores) / len(clarity_scores) if clarity_scores else 0.5
    
    # Wellness score: 60% sentiment, 40% clarity
    wellness_score = (avg_sentiment * 0.6 + avg_clarity * 0.4) * 100
    
    # Also consider status-based wellness
    status_wellness = calculate_wellness_score(notes)
    
    # Combine: 70% Gemini-based, 30% status-based
    final_wellness_score = (wellness_score * 0.7 + status_wellness * 0.3)
    
    # Calculate other metrics
    completion_rate = calculate_completion_rate(notes)
    peak_hours = find_peak_productivity_hours(notes)
    engagement_score = calculate_engagement_score(notes)
    active_days = calculate_active_days(notes, days=7)
    
    # Determine current state from wellness score
    if final_wellness_score >= 75:
        current_state = "energized"
    elif final_wellness_score >= 65:
        current_state = "focused"
    elif final_wellness_score >= 50:
        current_state = "calm"
    elif final_wellness_score >= 35:
        current_state = "stressed"
    else:
        current_state = "overwhelmed"
    
    # Generate insights using Gemini
    insights = generate_insights_with_gemini(notes, final_wellness_score, engagement_score, active_days, avg_sentiment, avg_clarity)
    
    # Determine trend (simplified - would need historical data for real trends)
    if final_wellness_score >= 70 and engagement_score >= 60:
        trend = "improving"
    elif final_wellness_score >= 50:
        trend = "stable"
    else:
        trend = "needs attention"
    
    return {
        "wellness_score": round(final_wellness_score, 1),
        "completion_rate": completion_rate,
        "peak_productivity_hours": peak_hours,
        "insights": insights,
        "engagement_score": engagement_score,
        "active_days": active_days,
        "total_notes": len(notes),
        "current_state": current_state,
        "trend": trend
    }


def generate_insights_with_gemini(notes: List[Dict], wellness_score: float, engagement_score: float, 
                                   active_days: int, avg_sentiment: float, avg_clarity: float) -> List[str]:
    """Generate insights using Gemini AI."""
    try:
        if not settings.gemini_api_key:
            return generate_insights(notes)
        
        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel('gemini-2.5-flash-lite')
        
        # Prepare summary
        notes_summary = f"Analyzed {len(notes)} notes"
        if notes:
            # Try to get titles from pages
            recent = sorted(notes, key=lambda x: extract_note_timestamp(x), reverse=True)[:5]
            recent_titles = []
            for note in recent:
                # Try to extract title from properties
                title = note.get('title', '')
                if not title and 'properties' in note:
                    for prop_name, prop_data in note['properties'].items():
                        if prop_data.get('type') == 'title' and prop_data.get('title'):
                            title = ' '.join([rt.get('plain_text', '') for rt in prop_data['title']])
                            break
                recent_titles.append(title or 'Untitled')
            if recent_titles:
                notes_summary += f". Recent notes: {', '.join(recent_titles[:3])}"
        
        prompt = f"""Based on the following wellness metrics, generate 3-4 informative but concise insights:

Metrics:
- Wellness Score: {wellness_score:.1f}/100
- Engagement Score: {engagement_score:.1f}/100
- Active Days (last 7 days): {active_days}
- Average Sentiment: {avg_sentiment:.2f} (0=negative, 1=positive)
- Average Clarity: {avg_clarity:.2f} (0=rushed, 1=clear)
- Total Notes: {len(notes)}

Generate insights that:
1. Are informative but concise (1-2 sentences, max 15-20 words each)
2. Provide actionable context and specific details
3. Highlight trends, patterns, or recommendations
4. Use an encouraging, helpful tone
5. Include specific numbers or metrics when relevant
6. Offer practical suggestions when appropriate

Examples of good insights:
- "Wellness score is moderate (65/100). Your sentiment is positive, but consider taking more breaks to maintain energy."
- "Engagement is low with only 2 active days this week. Try to track tasks more consistently for better insights."
- "Peak productivity hours are 10 AM-12 PM. Schedule important work during this window for better results."
- "Completion rate is 45%. Focus on finishing tasks to boost your wellness score and sense of accomplishment."

Format as a JSON array: ["insight 1", "insight 2", "insight 3"]
Return ONLY the JSON array, no additional text or explanations."""
        
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        # Extract JSON
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        insights = json.loads(response_text)
        if isinstance(insights, list):
            # Limit to 4 insights and ensure they're informative but concise
            formatted_insights = []
            for insight in insights[:4]:
                insight_str = str(insight).strip()
                # Limit to max 120 characters (about 20 words) for display
                # But allow full sentences for better context
                if len(insight_str) > 120:
                    # Try to truncate at a sentence boundary
                    sentences = insight_str.split('. ')
                    truncated = sentences[0]
                    if len(truncated) > 120:
                        # If first sentence is too long, truncate at word boundary
                        words = truncated.split()
                        truncated = ""
                        for word in words:
                            if len(truncated + " " + word) <= 117:
                                truncated += (" " if truncated else "") + word
                            else:
                                break
                        truncated += "..."
                    else:
                        # Include first sentence, add second if it fits
                        if len(sentences) > 1 and len(truncated + ". " + sentences[1]) <= 120:
                            truncated += ". " + sentences[1]
                    insight_str = truncated
                formatted_insights.append(insight_str)
            return formatted_insights if formatted_insights else generate_insights(notes)
        else:
            return generate_insights(notes)
    except Exception as e:
        print(f"Error generating Gemini insights: {str(e)}")
        return generate_insights(notes)


def analyze_wellness(notes: List[Dict]) -> Dict:
    """Analyze notes and generate wellness metrics (uses Gemini if available)."""
    return analyze_wellness_with_gemini(notes)

