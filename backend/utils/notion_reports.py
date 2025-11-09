"""Notion report generation utilities for comprehensive meeting reports."""
import json
from typing import List, Dict, Optional, Any
from datetime import datetime
from utils.notion import create_page_under_parent, add_blocks_to_page, find_notion_database, create_notion_page, get_notion_pages
import requests


def create_comprehensive_report_page(
    access_token: str,
    parent_page_id: str,
    meeting_name: str,
    meeting_date: str,
    agent_outputs: Dict[str, Any],
    stories: List[Any],
    report_url: Optional[str] = None
) -> Optional[Dict]:
    """Create a comprehensive meeting report page in Notion.
    
    Args:
        access_token: Notion API access token
        parent_page_id: Parent page ID (meeting note page)
        meeting_name: Name of the meeting
        meeting_date: Date of the meeting
        agent_outputs: Dictionary containing outputs from all 6 agents
        stories: List of Story objects
        report_url: Optional URL to link back to the report
    
    Returns:
        Created page data or None if error
    """
    try:
        # Format date
        try:
            from dateutil import parser as date_parser
            date_obj = date_parser.isoparse(meeting_date) if isinstance(meeting_date, str) else meeting_date
            date_str = date_obj.strftime("%B %d, %Y") if hasattr(date_obj, 'strftime') else str(meeting_date)
        except:
            date_str = str(meeting_date)
        
        # Create report page title
        report_title = f"Meeting Ended Report - {meeting_name} - {date_str}"
        
        # Create the page
        print(f"📄 Creating comprehensive report page: {report_title}")
        report_page = create_page_under_parent(access_token, parent_page_id, report_title)
        report_page_id = report_page.get("id")
        report_page_url = report_page.get("url", "")
        
        if not report_page_id:
            print("❌ Failed to create report page")
            return None
        
        print(f"✅ Created report page: {report_page_id}")
        print(f"📄 Report page URL: {report_page_url}")
        
        # Build blocks for the report
        blocks = []
        
        # 1. Executive Summary
        blocks.append({
            "object": "block",
            "type": "heading_1",
            "heading_1": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": "📊 Executive Summary"
                        }
                    }
                ]
            }
        })
        
        # Extract summary data
        story_extraction = agent_outputs.get("story_extraction", {})
        backlog_grooming = agent_outputs.get("backlog_grooming", {})
        meeting_insights = agent_outputs.get("meeting_insights", {})
        customer_research = agent_outputs.get("customer_research", {})
        cross_team = agent_outputs.get("cross_team_updates", {})
        reporting = agent_outputs.get("reporting", {})
        sprint_planning = agent_outputs.get("sprint_planning", {})
        
        stories_extracted = story_extraction.get("stories_extracted", 0)
        stories_auto_approved = len([s for s in stories if s.status == "approved"])
        stories_pending = len([s for s in stories if s.status == "pending"])
        duplicates_found = backlog_grooming.get("duplicate_count", 0)
        action_items = meeting_insights.get("total_action_items", 0)
        
        summary_text = f"""
✅ {stories_extracted} stories extracted from meeting notes
✅ {stories_auto_approved} stories auto-approved (confidence ≥ 80%)
⚠️ {stories_pending} stories need review
🔍 {duplicates_found} duplicate stories found
📝 {action_items} action items identified
        """.strip()
        
        blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": summary_text
                        }
                    }
                ]
            }
        })
        
        # 2. Customer Research Insights (Toggle)
        if customer_research.get("success"):
            blocks.append({
                "object": "block",
                "type": "heading_1",
                "heading_1": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "🔍 Customer Research Insights"
                            }
                        }
                    ]
                }
            })
            
            # Executive brief
            executive_brief = customer_research.get("executive_brief", "")
            if executive_brief:
                blocks.append({
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": "Executive Brief"
                                }
                            }
                        ]
                    }
                })
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": executive_brief
                                }
                            }
                        ]
                    }
                })
            
            # Customer themes
            themes = customer_research.get("customer_themes", [])
            if themes:
                blocks.append({
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": f"Customer Themes ({len(themes)})"
                                }
                            }
                        ]
                    }
                })
                for theme in themes[:5]:  # Limit to 5 themes
                    blocks.append({
                        "object": "block",
                        "type": "bulleted_list_item",
                        "bulleted_list_item": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": f"{theme.get('theme', 'Unknown')} - Frequency: {theme.get('frequency', 0)}"
                                    }
                                }
                            ]
                        }
                    })
            
            # Product bets
            product_bets = customer_research.get("product_bets", [])
            if product_bets:
                blocks.append({
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": "Product Bets"
                                }
                            }
                        ]
                    }
                })
                for bet in product_bets:
                    blocks.append({
                        "object": "block",
                        "type": "bulleted_list_item",
                        "bulleted_list_item": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": bet
                                    }
                                }
                            ]
                        }
                    })
        
        # 3. Extracted Stories (Toggle with auto-approved and pending sections)
        if stories:
            blocks.append({
                "object": "block",
                "type": "heading_1",
                "heading_1": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "📋 Extracted Stories"
                            }
                        }
                    ]
                }
            })
            
            # Auto-approved stories
            auto_approved_stories = [s for s in stories if s.status == "approved"]
            if auto_approved_stories:
                # Sort by Priority (High → Medium → Low) then by Story Points (descending)
                priority_order = {"high": 1, "medium": 2, "low": 3}
                auto_approved_stories.sort(
                    key=lambda s: (
                        priority_order.get(s.priority, 2),
                        -(s.story_points if s.story_points else 0)
                    )
                )
                
                blocks.append({
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": f"✅ Auto-Approved Stories ({len(auto_approved_stories)})"
                                }
                            }
                        ]
                    }
                })
                # Add story blocks
                story_blocks = _format_stories_as_blocks(auto_approved_stories)
                blocks.extend(story_blocks)
            
            # Pending review stories
            pending_stories = [s for s in stories if s.status == "pending"]
            if pending_stories:
                # Sort by Priority (High → Medium → Low) then by Story Points (descending)
                priority_order = {"high": 1, "medium": 2, "low": 3}
                pending_stories.sort(
                    key=lambda s: (
                        priority_order.get(s.priority, 2),
                        -(s.story_points if s.story_points else 0)
                    )
                )
                
                blocks.append({
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": f"⚠️ Pending Review ({len(pending_stories)})"
                                }
                            }
                        ]
                    }
                })
                # Add story blocks
                story_blocks = _format_stories_as_blocks(pending_stories)
                blocks.extend(story_blocks)
        
        # 4. Backlog Health & Duplicates
        if backlog_grooming.get("success"):
            blocks.append({
                "object": "block",
                "type": "heading_1",
                "heading_1": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "🏥 Backlog Health & Duplicates"
                            }
                        }
                    ]
                }
            })
            
            health_score = backlog_grooming.get("health_score", 0)
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": f"Health Score: {health_score:.1f}/100"
                            }
                        }
                    ]
                }
            })
            
            duplicates = backlog_grooming.get("duplicates", [])
            if duplicates:
                blocks.append({
                    "object": "block",
                    "type": "toggle",
                    "toggle": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": f"Duplicate Stories ({len(duplicates)})"
                                }
                            }
                        ],
                        "children": [
                            {
                                "object": "block",
                                "type": "bulleted_list_item",
                                "bulleted_list_item": {
                                    "rich_text": [
                                        {
                                            "type": "text",
                                            "text": {
                                                "content": dup.get("title", "Unknown") if isinstance(dup, dict) else str(dup)
                                            }
                                        }
                                    ]
                                }
                            } for dup in duplicates[:10]  # Limit to 10 duplicates
                        ]
                    }
                })
            
            # Clusters
            clusters = backlog_grooming.get("clusters", [])
            if clusters:
                blocks.append({
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": f"Story Clusters ({len(clusters)})"
                                }
                            }
                        ]
                    }
                })
                for cluster in clusters[:5]:  # Limit to 5 clusters
                    blocks.append({
                        "object": "block",
                        "type": "heading_3",
                        "heading_3": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": cluster.get("cluster_name", "Unknown")
                                    }
                                }
                            ]
                        }
                    })
                    blocks.append({
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": f"User Need: {cluster.get('user_need', 'N/A')}"
                                    }
                                }
                            ]
                        }
                    })
        
        # 5. Cross-Team Status
        if cross_team.get("success"):
            blocks.append({
                "object": "block",
                "type": "heading_1",
                "heading_1": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "👥 Cross-Team Status"
                            }
                        }
                    ]
                }
            })
            
            overall_status = cross_team.get("overall_status", "")
            if overall_status:
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": overall_status
                                }
                            }
                        ]
                    }
                })
            
            # Team highlights
            team_highlights = cross_team.get("team_highlights", [])
            if team_highlights:
                for team in team_highlights[:5]:  # Limit to 5 teams
                    blocks.append({
                        "object": "block",
                        "type": "toggle",
                        "toggle": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": team.get("team", "Unknown Team")
                                    }
                                }
                            ],
                            "children": [
                                {
                                    "object": "block",
                                    "type": "heading_3",
                                    "heading_3": {
                                        "rich_text": [
                                            {
                                                "type": "text",
                                                "text": {
                                                    "content": "Wins"
                                                }
                                            }
                                        ]
                                    }
                                },
                                *[
                                    {
                                        "object": "block",
                                        "type": "bulleted_list_item",
                                        "bulleted_list_item": {
                                            "rich_text": [
                                                {
                                                    "type": "text",
                                                    "text": {
                                                        "content": win
                                                    }
                                                }
                                            ]
                                        }
                                    } for win in team.get("wins", [])[:3]
                                ],
                                {
                                    "object": "block",
                                    "type": "heading_3",
                                    "heading_3": {
                                        "rich_text": [
                                            {
                                                "type": "text",
                                                "text": {
                                                    "content": "Blockers"
                                                }
                                            }
                                        ]
                                    }
                                },
                                *[
                                    {
                                        "object": "block",
                                        "type": "bulleted_list_item",
                                        "bulleted_list_item": {
                                            "rich_text": [
                                                {
                                                    "type": "text",
                                                    "text": {
                                                        "content": blocker
                                                    }
                                                }
                                            ]
                                        }
                                    } for blocker in team.get("blockers", [])[:3]
                                ]
                            ]
                        }
                    })
            
            # Dependencies and risks
            dependencies = cross_team.get("dependencies", [])
            if dependencies:
                blocks.append({
                    "object": "block",
                    "type": "toggle",
                    "toggle": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": f"Dependencies ({len(dependencies)})"
                                }
                            }
                        ],
                        "children": [
                            {
                                "object": "block",
                                "type": "bulleted_list_item",
                                "bulleted_list_item": {
                                    "rich_text": [
                                        {
                                            "type": "text",
                                            "text": {
                                                "content": dep
                                            }
                                        }
                                    ]
                                }
                            } for dep in dependencies[:10]
                        ]
                    }
                })
            
            risks = cross_team.get("risks", [])
            if risks:
                blocks.append({
                    "object": "block",
                    "type": "toggle",
                    "toggle": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": f"Risks ({len(risks)})"
                                }
                            }
                        ],
                        "children": [
                            {
                                "object": "block",
                                "type": "bulleted_list_item",
                                "bulleted_list_item": {
                                    "rich_text": [
                                        {
                                            "type": "text",
                                            "text": {
                                                "content": risk
                                            }
                                        }
                                    ]
                                }
                            } for risk in risks[:10]
                        ]
                    }
                })
        
        # 6. Meeting Insights
        if meeting_insights.get("success"):
            blocks.append({
                "object": "block",
                "type": "heading_1",
                "heading_1": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "💡 Meeting Insights"
                            }
                        }
                    ]
                }
            })
            
            meetings = meeting_insights.get("meetings", [])
            for meeting in meetings[:5]:  # Limit to 5 meetings
                meeting_title = meeting.get("meeting_title", "Unknown Meeting")
                blocks.append({
                    "object": "block",
                    "type": "toggle",
                    "toggle": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": meeting_title
                                }
                            }
                        ],
                        "children": [
                            # Summary
                            {
                                "object": "block",
                                "type": "heading_3",
                                "heading_3": {
                                    "rich_text": [
                                        {
                                            "type": "text",
                                            "text": {
                                                "content": "Summary"
                                            }
                                        }
                                    ]
                                }
                            },
                            *[
                                {
                                    "object": "block",
                                    "type": "bulleted_list_item",
                                    "bulleted_list_item": {
                                        "rich_text": [
                                            {
                                                "type": "text",
                                                "text": {
                                                    "content": point
                                                }
                                            }
                                        ]
                                    }
                                } for point in meeting.get("summary", [])[:5]
                            ],
                            # Decisions
                            {
                                "object": "block",
                                "type": "heading_3",
                                "heading_3": {
                                    "rich_text": [
                                        {
                                            "type": "text",
                                            "text": {
                                                "content": "Decisions"
                                            }
                                        }
                                    ]
                                }
                            },
                            *[
                                {
                                    "object": "block",
                                    "type": "bulleted_list_item",
                                    "bulleted_list_item": {
                                        "rich_text": [
                                            {
                                                "type": "text",
                                                "text": {
                                                    "content": decision
                                                }
                                            }
                                        ]
                                    }
                                } for decision in meeting.get("decisions", [])[:5]
                            ],
                            # Action items
                            {
                                "object": "block",
                                "type": "heading_3",
                                "heading_3": {
                                    "rich_text": [
                                        {
                                            "type": "text",
                                            "text": {
                                                "content": "Action Items"
                                            }
                                        }
                                    ]
                                }
                            },
                            *[
                                {
                                    "object": "block",
                                    "type": "bulleted_list_item",
                                    "bulleted_list_item": {
                                        "rich_text": [
                                            {
                                                "type": "text",
                                                "text": {
                                                    "content": f"{item.get('description', 'N/A')} (Owner: {item.get('owner', 'Unassigned')})"
                                                }
                                            }
                                        ]
                                    }
                                } for item in meeting.get("action_items", [])[:10]
                            ]
                        ]
                    }
                })
        
        # 7. Sprint Plan Recommendation
        if sprint_planning.get("success"):
            blocks.append({
                "object": "block",
                "type": "heading_1",
                "heading_1": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "🎯 Sprint Plan Recommendation"
                            }
                        }
                    ]
                }
            })
            
            sprint_goal = sprint_planning.get("sprint_goal", "")
            if sprint_goal:
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": f"Sprint Goal: {sprint_goal}"
                                }
                            }
                        ]
                    }
                })
            
            sprint_scope = sprint_planning.get("sprint_scope", [])
            if sprint_scope:
                blocks.append({
                    "object": "block",
                    "type": "toggle",
                    "toggle": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": f"Sprint Scope ({sprint_planning.get('total_points', 0)} points)"
                                }
                            }
                        ],
                        "children": [
                            {
                                "object": "block",
                                "type": "bulleted_list_item",
                                "bulleted_list_item": {
                                    "rich_text": [
                                        {
                                            "type": "text",
                                            "text": {
                                                "content": f"{item.get('title', 'Unknown')} ({item.get('points', 0)} pts, Priority: {item.get('priority', 'Medium')})"
                                            }
                                        }
                                    ]
                                }
                            } for item in sprint_scope
                        ]
                    }
                })
            
            # Risks
            major_risks = sprint_planning.get("major_risks", [])
            if major_risks:
                blocks.append({
                    "object": "block",
                    "type": "toggle",
                    "toggle": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": "Major Risks"
                                }
                            }
                        ],
                        "children": [
                            {
                                "object": "block",
                                "type": "bulleted_list_item",
                                "bulleted_list_item": {
                                    "rich_text": [
                                        {
                                            "type": "text",
                                            "text": {
                                                "content": risk
                                            }
                                        }
                                    ]
                                }
                            } for risk in major_risks
                        ]
                    }
                })
        
        # 8. Release Notes Draft
        if reporting.get("success"):
            blocks.append({
                "object": "block",
                "type": "heading_1",
                "heading_1": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "📝 Release Notes Draft"
                            }
                        }
                    ]
                }
            })
            
            release_notes = reporting.get("release_notes", {})
            if release_notes:
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": f"Version: {release_notes.get('version', 'N/A')}"
                                }
                            }
                        ]
                    }
                })
                
                summary = release_notes.get("summary", "")
                if summary:
                    blocks.append({
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": summary
                                    }
                                }
                            ]
                        }
                    })
                
                highlights = release_notes.get("highlights", [])
                if highlights:
                    blocks.append({
                        "object": "block",
                        "type": "toggle",
                        "toggle": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": "Highlights"
                                    }
                                }
                            ],
                            "children": [
                                {
                                    "object": "block",
                                    "type": "bulleted_list_item",
                                    "bulleted_list_item": {
                                        "rich_text": [
                                            {
                                                "type": "text",
                                                "text": {
                                                    "content": highlight
                                                }
                                            }
                                        ]
                                    }
                                } for highlight in highlights
                            ]
                        }
                    })
            
            # Weekly executive update
            executive_update = reporting.get("weekly_executive_update", "")
            if executive_update:
                blocks.append({
                    "object": "block",
                    "type": "toggle",
                    "toggle": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": "Weekly Executive Update"
                                }
                            }
                        ],
                        "children": [
                            {
                                "object": "block",
                                "type": "paragraph",
                                "paragraph": {
                                    "rich_text": [
                                        {
                                            "type": "text",
                                            "text": {
                                                "content": executive_update
                                            }
                                        }
                                    ]
                                }
                            }
                        ]
                    }
                })
        
        # Add Notion page link at the end
        if report_page_url:
            blocks.append({
                "object": "block",
                "type": "divider",
                "divider": {}
            })
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "📄 View this report in Notion: "
                            }
                        },
                        {
                            "type": "text",
                            "text": {
                                "content": report_page_url,
                                "link": {
                                    "url": report_page_url
                                }
                            }
                        }
                    ]
                }
            })
        
        # Add all blocks to the page
        success = add_blocks_to_page(access_token, report_page_id, blocks)
        
        if success:
            print(f"✅ Successfully created comprehensive report page with {len(blocks)} blocks")
            print(f"📄 Report page URL: {report_page_url}")
            return {
                "id": report_page_id,
                "url": report_page_url,
                "title": report_title
            }
        else:
            print(f"⚠️ Report page created but some blocks may have failed to add")
            print(f"📄 Report page URL: {report_page_url}")
            return {
                "id": report_page_id,
                "url": report_page_url,
                "title": report_title
            }
        
    except Exception as e:
        print(f"❌ Error creating comprehensive report page: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def _format_stories_as_blocks(stories: List[Any]) -> List[Dict]:
    """Format stories as Notion blocks for toggle children.
    
    Args:
        stories: List of Story objects
    
    Returns:
        List of block dictionaries
    """
    blocks = []
    
    for idx, story in enumerate(stories):
        story_num = idx + 1
        
        # Parse tags
        tags_list = []
        if story.tags:
            try:
                tags_list = json.loads(story.tags) if isinstance(story.tags, str) else story.tags
            except:
                tags_list = []
        
        # Format priority
        priority_map = {"high": "High", "medium": "Medium", "low": "Low"}
        priority_display = priority_map.get(story.priority, "Medium")
        
        # Story heading
        blocks.append({
            "object": "block",
            "type": "heading_3",
            "heading_3": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": f"Story {story_num}: {story.title}"
                        }
                    }
                ]
            }
        })
        
        # Story details as bulleted list
        story_details = [
            f"Priority: {priority_display}",
            f"Owner: {story.owner or 'Unassigned'}",
            f"Status: {story.status}",
            f"Story Points: {story.story_points or 5}",
            f"Confidence: {story.confidence or 70}%",
            f"Tags: {', '.join(tags_list) if tags_list else 'None'}",
            f"Product: {story.product or 'SerenityFlow'}"
        ]
        
        if story.description:
            story_details.insert(0, f"Description: {story.description}")
        
        for detail in story_details:
            blocks.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": detail
                            }
                        }
                    ]
                }
            })
    
    return blocks


def create_backlog_database_entries(
    access_token: str,
    stories: List[Any],
    report_page_url: Optional[str] = None
) -> Dict[str, Any]:
    """Create database entries for auto-approved stories in Backlog database.
    
    Args:
        access_token: Notion API access token
        stories: List of Story objects (only auto-approved stories with confidence ≥ 80%)
        report_page_url: URL of the report page to link as source
    
    Returns:
        Dictionary with success status, created count, and errors
    """
    try:
        # Filter to only auto-approved stories (confidence ≥ 80%)
        auto_approved_stories = [s for s in stories if s.status == "approved" and (s.confidence or 0) >= 80]
        
        if not auto_approved_stories:
            print("No auto-approved stories to create in database")
            return {
                "success": True,
                "created_count": 0,
                "errors": []
            }
        
        # Find or create Backlog database
        database_id = find_notion_database(access_token, "Backlog")
        
        if not database_id:
            print("⚠️ Backlog database not found. Stories will not be created in database.")
            return {
                "success": False,
                "error": "Backlog database not found. Please create a 'Backlog' database in Notion.",
                "created_count": 0,
                "errors": []
            }
        
        print(f"📊 Found Backlog database: {database_id}")
        
        # Sort stories by priority and story points
        priority_order = {"high": 1, "medium": 2, "low": 3}
        auto_approved_stories.sort(
            key=lambda s: (
                priority_order.get(s.priority, 2),
                -(s.story_points if s.story_points else 0)
            )
        )
        
        # Create database entries
        created_count = 0
        errors = []
        
        for idx, story in enumerate(auto_approved_stories):
            try:
                # Parse tags
                tags_list = []
                if story.tags:
                    try:
                        tags_list = json.loads(story.tags) if isinstance(story.tags, str) else story.tags
                    except:
                        tags_list = []
                
                # Build properties
                properties = {
                    "priority": story.priority or "medium",
                    "status": "Backlog",
                    "owner": story.owner,
                    "tags": tags_list,
                    "story_points": story.story_points or 5,
                    "product": story.product or "SerenityFlow",
                    "sort_ranking": idx + 1
                }
                
                # Add source link if report page URL is provided
                if report_page_url:
                    properties["source"] = report_page_url
                
                # Create database entry
                notion_page = create_notion_page(
                    access_token=access_token,
                    database_id=database_id,
                    title=story.title,
                    description=story.description,
                    properties=properties
                )
                
                # Update story with Notion page ID
                story.notion_page_id = notion_page.get("id")
                created_count += 1
                
                print(f"✅ Created database entry: {story.title}")
                
            except Exception as e:
                error_msg = f"Error creating database entry for '{story.title}': {str(e)}"
                print(f"❌ {error_msg}")
                errors.append(error_msg)
                continue
        
        print(f"✅ Created {created_count}/{len(auto_approved_stories)} stories in Backlog database")
        
        return {
            "success": True,
            "created_count": created_count,
            "total_stories": len(auto_approved_stories),
            "errors": errors,
            "database_id": database_id
        }
        
    except Exception as e:
        print(f"❌ Error creating backlog database entries: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e),
            "created_count": 0,
            "errors": []
        }

