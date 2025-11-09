"""Noise Clearing Agent - audits backlog and flags duplicates/low-priority items."""
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from .base_agent import BaseAgent
import json
import uuid
from utils.gemini import initialize_gemini
import google.generativeai as genai
from config import settings


class NoiseClearingAgent(BaseAgent):
    """Agent that audits backlog, clusters items, and generates canonical stories."""
    
    def __init__(self, db_session, user_id: str = "default"):
        """Initialize the backlog grooming agent."""
        super().__init__(db_session, user_id)
        initialize_gemini()
        self.model = genai.GenerativeModel('gemini-2.5-flash')
    
    def run(self, **kwargs) -> Dict[str, Any]:
        """Run backlog grooming: cluster items, generate canonical stories, and flag duplicates.
        
        Returns:
            Dict with clusters, canonical stories, duplicates, and recommendations
        """
        from database import Story, BacklogHealth
        
        self.log_action("Starting backlog grooming")
        
        # Get all active stories (exclude archived and rejected)
        stories = self.db.query(Story).filter(
            Story.user_id == self.user_id,
            Story.status.in_(["pending", "approved"])
        ).order_by(Story.created_at.desc()).all()
        
        # Limit to recent stories to avoid processing too many duplicates
        # Only check duplicates among stories created in the last 90 days
        from datetime import datetime, timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=90)
        recent_stories = [s for s in stories if s.created_at and s.created_at >= cutoff_date]
        
        # If we have too many stories, only process recent ones for clustering
        # But still use all stories for duplicate detection
        if len(stories) > 500:
            self.log_action(f"Too many stories ({len(stories)}), limiting clustering to recent {len(recent_stories)} stories (last 90 days)")
            stories_for_clustering = recent_stories
        else:
            stories_for_clustering = stories
        
        if not stories:
            return {
                "success": True,
                "clusters": [],
                "duplicates": [],
                "health_score": 100,
                "recommendations": [],
                "checklist_items": []
            }
        
        # Convert stories to dict format for duplicate detection
        stories_data = [
            {
                "id": s.id,
                "title": s.title,
                "description": s.description or "",
                "priority": s.priority or "medium"
            }
            for s in stories
        ]
        
        # Convert stories_for_clustering to dict format for clustering
        stories_for_clustering_data = [
            {
                "id": s.id,
                "title": s.title,
                "description": s.description or "",
                "priority": s.priority or "medium"
            }
            for s in stories_for_clustering
        ]
        
        # Cluster stories and generate canonical stories
        clusters = self._cluster_stories(stories_for_clustering_data)
        
        # Find duplicates
        duplicates = self._find_duplicates(stories)
        
        # Analyze stories for issues
        low_priority = self._find_low_priority(stories)
        outdated = self._find_outdated(stories)
        
        # Calculate health score
        total_stories = len(stories)
        issues = len(duplicates) + len(low_priority) + len(outdated)
        health_score = max(0, 100 - (issues / total_stories * 100)) if total_stories > 0 else 100
        
        # Create backlog health record
        health = BacklogHealth(
            id=str(uuid.uuid4()),
            health_score=health_score,
            total_stories=total_stories,
            duplicate_count=len(duplicates),
            low_priority_count=len(low_priority),
            outdated_count=len(outdated),
            recommendations=json.dumps({
                "duplicates": duplicates,
                "low_priority": low_priority,
                "outdated": outdated
            }),
            user_id=self.user_id,
            audit_date=datetime.utcnow()
        )
        
        self.db.add(health)
        self.db.commit()
        
        # Create checklist items for recommendations
        checklist_item_ids = []
        
        if duplicates:
            checklist_id = self.create_checklist_item(
                item_type="backlog_cleanup",
                title=f"{len(duplicates)} duplicate story(s) found",
                description=f"Review and archive {len(duplicates)} duplicate story(s) to clean up backlog.",
                priority="medium",
                action_type="archive",
                action_data={
                    "story_ids": duplicates,
                    "reason": "duplicate"
                }
            )
            checklist_item_ids.append(checklist_id)
        
        if low_priority:
            checklist_id = self.create_checklist_item(
                item_type="backlog_cleanup",
                title=f"{len(low_priority)} low-priority story(s) found",
                description=f"Review {len(low_priority)} low-priority story(s) for potential archiving.",
                priority="low",
                action_type="review",
                action_data={
                    "story_ids": low_priority,
                    "reason": "low_priority"
                }
            )
            checklist_item_ids.append(checklist_id)
        
        if outdated:
            checklist_id = self.create_checklist_item(
                item_type="backlog_cleanup",
                title=f"{len(outdated)} outdated story(s) found",
                description=f"Review {len(outdated)} outdated story(s) that haven't been updated in 30+ days.",
                priority="medium",
                action_type="review",
                action_data={
                    "story_ids": outdated,
                    "reason": "outdated"
                }
            )
            checklist_item_ids.append(checklist_id)
        
        self.log_action(f"Backlog grooming complete - Health score: {health_score}, Clusters: {len(clusters)}")
        
        # Create checklist item for clusters
        if clusters:
            self.create_checklist_item(
                item_type="backlog_grooming",
                title=f"Backlog Groomed: {len(clusters)} cluster(s) identified",
                description=f"Generated {len(clusters)} canonical stories from {total_stories} items",
                priority="high",
                action_type="review",
                metadata={
                    "clusters": clusters,
                    "duplicates": duplicates
                }
            )
        
        return {
            "success": True,
            "clusters": clusters,
            "duplicates": [
                {"original": d[0] if isinstance(d, tuple) else d, "duplicate": d[1] if isinstance(d, tuple) else None, "similarity": 95}
                for d in duplicates[:10]  # Limit duplicates
            ],
            "health_score": health_score,
            "total_stories": total_stories,
            "duplicate_count": len(duplicates),
            "low_priority": len(low_priority),
            "outdated": len(outdated),
            "recommendations": {
                "duplicates": duplicates,
                "low_priority": low_priority,
                "outdated": outdated
            },
            "checklist_items": checklist_item_ids
        }
    
    def _cluster_stories(self, stories: List[Dict]) -> List[Dict]:
        """Cluster similar stories and generate canonical stories.
        
        Args:
            stories: List of story dictionaries
        
        Returns:
            List of clusters with canonical stories
        """
        if len(stories) < 2:
            self.log_action(f"Skipping clustering: need at least 2 stories, got {len(stories)}")
            return []
        
        # Limit to 100 stories max to avoid token limits and ensure response fits
        if len(stories) > 100:
            self.log_action(f"Limiting clustering to 100 stories (from {len(stories)} total)")
            stories = stories[:100]
        
        try:
            # Convert stories to JSON, limiting by story count (not character count)
            stories_json = json.dumps(stories, indent=2)
            
            # Log how many stories we're clustering
            self.log_action(f"Clustering {len(stories)} stories")
            
            # Limit stories JSON to reduce input size
            stories_json_limited = json.dumps(stories[:50], indent=2)  # Limit to 50 stories for clustering
            
            prompt = f"""Analyze the following backlog items and cluster them into groups of similar items. For each cluster, generate a canonical user story.

**Backlog Items:**
{stories_json_limited}

**Instructions:**
1. Group similar tickets/stories together (e.g., all checkout-related, all authentication-related)
2. For each cluster, identify:
   - Cluster name (e.g., "Checkout Performance")
   - Items in the cluster (list of story IDs)
   - User need (what problem does this cluster solve?)
   - Canonical story with title, description, priority, and impact score

3. Priority: High (critical/critical path), Medium (important), Low (nice-to-have)
4. Impact score: 0-100 (higher = more impact)
5. Limit to top 10 clusters maximum

**Output Format (JSON only):**
{{
  "clusters": [
    {{
      "cluster_name": "Checkout Performance",
      "items": ["story-id-1", "story-id-2", "story-id-3"],
      "user_need": "Users need a fast, error-free checkout experience",
      "canonical_story": {{
        "title": "Optimize checkout flow for speed and reliability",
        "description": "Improve checkout performance and fix coupon calculation bugs",
        "priority": "High",
        "impact_score": 85
      }}
    }}
  ]
}}

Return ONLY JSON, no markdown formatting. Keep responses concise. Limit to top 10 clusters."""
            
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=8192,  # Increased to handle larger responses
                )
            )
            
            # Get response text safely (avoid accessing finish_message)
            response_text = ""
            finish_reason = None
            try:
                # First try the standard .text property (this usually works even with MAX_TOKENS)
                if hasattr(response, 'text'):
                    try:
                        response_text = response.text
                        if response_text:
                            self.log_action(f"Extracted {len(response_text)} characters using response.text")
                    except Exception as e:
                        self.log_action(f"Error accessing response.text: {str(e)}")
                
                # If that didn't work, try extracting from candidates
                if not response_text and hasattr(response, 'candidates') and response.candidates:
                    candidate = response.candidates[0]
                    if hasattr(candidate, 'finish_reason'):
                        finish_reason = candidate.finish_reason
                        self.log_action(f"Response finish_reason: {finish_reason}")
                    
                    # Extract text from candidate
                    if hasattr(candidate, 'content'):
                        content = candidate.content
                        if hasattr(content, 'parts') and content.parts:
                            # Extract text from parts
                            text_parts = []
                            for part in content.parts:
                                if hasattr(part, 'text'):
                                    text_parts.append(part.text)
                            response_text = "".join(text_parts)
                            if response_text:
                                self.log_action(f"Extracted {len(response_text)} characters from candidate.content.parts")
                        elif hasattr(content, 'text'):
                            response_text = content.text
                            if response_text:
                                self.log_action(f"Extracted {len(response_text)} characters from candidate.content.text")
                
                # Last resort: try to convert to string (but this won't give us the actual text)
                if not response_text:
                    self.log_action("Warning: Could not extract text from response. Response structure:")
                    self.log_action(f"Response type: {type(response)}")
                    if hasattr(response, 'candidates') and response.candidates:
                        candidate = response.candidates[0]
                        self.log_action(f"Candidate type: {type(candidate)}")
                        self.log_action(f"Candidate attributes: {dir(candidate)}")
                    return []
                    
            except Exception as e:
                self.log_action(f"Error extracting response text: {str(e)}")
                return []
            
            # Log warning if response was truncated
            if finish_reason == "MAX_TOKENS":
                self.log_action(f"Warning: Response was truncated (MAX_TOKENS). Extracted {len(response_text)} characters. Will try to parse partial JSON.")
            
            if not response_text:
                self.log_action("No response text received from clustering model")
                return []
            
            # Parse response
            import re
            # Remove markdown code blocks if present
            json_match = re.search(r'```(?:json)?\s*(\{.*\})\s*```', response_text, re.DOTALL)
            if json_match:
                response_text = json_match.group(1)
            else:
                # Try to find JSON object directly
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    response_text = json_match.group(0)
            
            # Try to fix truncated JSON by finding balanced braces and brackets
            if response_text:
                # Find the start of the JSON object
                start_pos = response_text.find('{')
                if start_pos == -1:
                    self.log_action("No JSON object found in response")
                    return []
                
                # Track braces and brackets to find the end of valid JSON
                brace_count = 0
                bracket_count = 0
                in_string = False
                escape_next = False
                last_valid_pos = start_pos
                
                for i in range(start_pos, len(response_text)):
                    char = response_text[i]
                    
                    if escape_next:
                        escape_next = False
                        continue
                    
                    if char == '\\':
                        escape_next = True
                        continue
                    
                    if char == '"' and not escape_next:
                        in_string = not in_string
                        continue
                    
                    if not in_string:
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0 and bracket_count == 0:
                                last_valid_pos = i + 1
                                break
                        elif char == '[':
                            bracket_count += 1
                        elif char == ']':
                            bracket_count -= 1
                            if brace_count == 0 and bracket_count == 0:
                                last_valid_pos = i + 1
                                break
                
                if last_valid_pos > start_pos:
                    response_text = response_text[start_pos:last_valid_pos]
                else:
                    # If we couldn't find balanced braces, try to extract just the clusters array
                    clusters_match = re.search(r'"clusters"\s*:\s*\[(.*?)\]', response_text, re.DOTALL)
                    if clusters_match:
                        # Try to parse just the clusters array
                        try:
                            clusters_json = '[' + clusters_match.group(1) + ']'
                            # Find balanced brackets for the array
                            bracket_count = 0
                            last_valid_pos = 0
                            for i, char in enumerate(clusters_json):
                                if char == '[':
                                    bracket_count += 1
                                elif char == ']':
                                    bracket_count -= 1
                                    if bracket_count == 0:
                                        last_valid_pos = i + 1
                                        break
                            if last_valid_pos > 0:
                                clusters_json = clusters_json[:last_valid_pos]
                                clusters_list = json.loads(clusters_json)
                                result = {"clusters": clusters_list}
                                clusters = result.get("clusters", [])
                                self.log_action(f"Generated {len(clusters)} clusters from {len(stories)} stories (extracted from partial JSON)")
                                return clusters
                        except:
                            pass
            
            # Try to parse the full JSON
            try:
                result = json.loads(response_text)
                clusters = result.get("clusters", [])
                
                if not clusters:
                    self.log_action(f"No clusters found in response. Response keys: {list(result.keys()) if isinstance(result, dict) else 'not a dict'}")
                    # Log the full response for debugging
                    self.log_action(f"Full response: {response_text[:1000]}")
                else:
                    self.log_action(f"Generated {len(clusters)} clusters from {len(stories)} stories")
                
                return clusters
            except json.JSONDecodeError as e:
                self.log_action(f"JSON decode error: {str(e)}")
                self.log_action(f"Response text (first 1000 chars): {response_text[:1000]}")
                # Try to extract clusters using regex as a last resort
                clusters_match = re.search(r'"clusters"\s*:\s*\[(.*?)\]', response_text, re.DOTALL)
                if clusters_match:
                    self.log_action("Attempting to extract clusters using regex fallback")
                    # This is a last resort - try to manually parse cluster objects
                    cluster_objects = re.findall(r'\{\s*"cluster_name"\s*:\s*"[^"]*"\s*,\s*"items"\s*:\s*\[[^\]]*\]', response_text)
                    if cluster_objects:
                        self.log_action(f"Found {len(cluster_objects)} cluster objects using regex")
                        # Return empty list - we can't fully parse without proper JSON
                        return []
                return []
            
        except Exception as e:
            self.log_action(f"Error clustering stories: {str(e)}")
            import traceback
            self.log_action(f"Traceback: {traceback.format_exc()}")
            # Log first 1000 chars of response for debugging
            if 'response_text' in locals() and response_text:
                self.log_action(f"Response text (first 1000 chars): {response_text[:1000]}")
            return []
    
    def _find_duplicates(self, stories: List) -> List[str]:
        """Find duplicate stories using GenAI for semantic similarity.
        
        Args:
            stories: List of Story objects
        
        Returns:
            List of duplicate story IDs (keeping the first occurrence, flagging others)
        """
        if len(stories) < 2:
            return []
        
        # First, do a quick exact/close match check
        seen_titles = {}
        exact_duplicates = []
        
        for story in stories:
            title_lower = story.title.lower().strip()
            title_normalized = " ".join(title_lower.split())
            
            if title_normalized in seen_titles:
                exact_duplicates.append(story.id)
            else:
                seen_titles[title_normalized] = story.id
        
        # If we have many stories, use GenAI for semantic duplicate detection
        if len(stories) > 5:
            try:
                initialize_gemini()
                # Use gemini-2.5-flash for good balance of speed and quality
                model = genai.GenerativeModel('gemini-2.5-flash')
                
                # Prepare story list for GenAI
                stories_data = []
                for story in stories:
                    stories_data.append({
                        "id": story.id,
                        "title": story.title,
                        "description": story.description or "",
                        "priority": story.priority or "medium"
                    })
                
                # Build prompt for duplicate detection
                stories_json = json.dumps(stories_data, indent=2)
                prompt = f"""You are a backlog management assistant. Analyze the following stories and identify duplicates or near-duplicates.

**Stories:**
{stories_json[:8000]}  # Limit to avoid token limits

**Instructions:**
1. Identify stories that are duplicates or very similar (same feature, same bug, same requirement)
2. For each duplicate group, keep the FIRST story (by creation date or ID order) and flag the others
3. Consider semantic similarity, not just exact title matches
4. Return a JSON object with duplicate groups

**Output Format (JSON only):**
{{
  "duplicate_groups": [
    {{
      "keep_id": "story-id-1",
      "duplicate_ids": ["story-id-2", "story-id-3"],
      "reason": "All describe the same feature: user login"
    }}
  ]
}}

Return only valid JSON, no additional text.
"""
                
                response = model.generate_content(prompt)
                
                # Get response text safely (avoid accessing finish_message)
                response_text = ""
                try:
                    # First try the standard .text property
                    if hasattr(response, 'text'):
                        response_text = response.text
                    elif hasattr(response, 'candidates') and response.candidates:
                        # Extract from candidates if .text doesn't work
                        candidate = response.candidates[0]
                        if hasattr(candidate, 'content'):
                            content = candidate.content
                            if hasattr(content, 'parts') and content.parts:
                                # Extract text from parts
                                text_parts = []
                                for part in content.parts:
                                    if hasattr(part, 'text'):
                                        text_parts.append(part.text)
                                response_text = "".join(text_parts)
                            elif hasattr(content, 'text'):
                                response_text = content.text
                    
                    # Fallback: try to convert to string
                    if not response_text:
                        response_text = str(response)
                except Exception as e:
                    self.log_action(f"Error extracting response text: {str(e)}")
                    return []
                
                if not response_text:
                    return []
                
                # Parse response
                import re
                json_match = re.search(r'```(?:json)?\s*(\{.*\})\s*```', response_text, re.DOTALL)
                if json_match:
                    response_text = json_match.group(1)
                else:
                    json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                    if json_match:
                        response_text = json_match.group(0)
                
                result = json.loads(response_text)
                duplicate_groups = result.get("duplicate_groups", [])
                
                # Collect all duplicate IDs
                semantic_duplicates = []
                for group in duplicate_groups:
                    semantic_duplicates.extend(group.get("duplicate_ids", []))
                
                # Combine with exact duplicates (avoid duplicates in the list)
                all_duplicates = list(set(exact_duplicates + semantic_duplicates))
                
                self.log_action(f"Found {len(all_duplicates)} duplicates ({len(exact_duplicates)} exact, {len(semantic_duplicates)} semantic)")
                
                return all_duplicates
                
            except Exception as e:
                self.log_action(f"Error using GenAI for duplicate detection: {str(e)}, falling back to exact match")
                return exact_duplicates
        
        return exact_duplicates
    
    def _find_low_priority(self, stories: List) -> List[str]:
        """Find low-priority stories that might be candidates for archiving.
        
        Args:
            stories: List of Story objects
        
        Returns:
            List of low-priority story IDs
        """
        low_priority = []
        
        for story in stories:
            if story.priority == "low":
                # Check if it's been low priority for a while
                days_since_creation = (datetime.utcnow() - story.created_at).days
                if days_since_creation > 30:
                    low_priority.append(story.id)
        
        return low_priority
    
    def _find_outdated(self, stories: List) -> List[str]:
        """Find outdated stories that haven't been updated recently.
        
        Args:
            stories: List of Story objects
        
        Returns:
            List of outdated story IDs
        """
        outdated = []
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        
        for story in stories:
            # Check if story hasn't been updated in 30+ days
            last_update = story.updated_at or story.created_at
            if last_update < cutoff_date:
                outdated.append(story.id)
        
        return outdated

