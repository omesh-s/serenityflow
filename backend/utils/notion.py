"""Utility functions for Notion API."""
import requests
from typing import List, Dict, Optional, Any
from datetime import datetime
from config import settings
import json


def get_notion_pages(access_token: str, page_size: int = 100, max_pages: int = None, include_archived: bool = False) -> List[Dict]:
    """Fetch pages from Notion workspace with pagination support.
    
    Args:
        access_token: Notion API access token
        page_size: Number of pages per API request (max 100)
        max_pages: Maximum number of pages to fetch (None for all)
        include_archived: Whether to include archived pages
    
    Returns:
        List of formatted page dictionaries
    """
    try:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        }
        
        # Search for pages in the workspace
        url = "https://api.notion.com/v1/search"
        
        # Use maximum page size for efficiency (Notion API max is 100)
        request_page_size = min(page_size, 100)
        
        all_pages = []
        start_cursor = None
        has_more = True
        
        # Fetch all pages using pagination
        page_number = 1
        while has_more:
            payload = {
                "filter": {
                    "property": "object",
                    "value": "page"
                },
                "page_size": request_page_size,
                "sort": {
                    "direction": "descending",
                    "timestamp": "last_edited_time"
                }
            }
            
            # Add pagination cursor if we have one
            if start_cursor:
                payload["start_cursor"] = start_cursor
                print(f"Fetching page {page_number} with cursor: {start_cursor[:20]}...")
            else:
                print(f"Fetching page {page_number} (first batch)...")
            
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            pages = data.get("results", [])
            has_more_result = data.get("has_more", False)
            next_cursor = data.get("next_cursor")
            
            # Log detailed pagination info
            print(f"  → Received {len(pages)} pages, has_more: {has_more_result}")
            if next_cursor:
                print(f"  → Next cursor: {next_cursor[:30]}...")
            else:
                print(f"  → No next cursor (this is the last page)")
            
            # Log page IDs for debugging
            if pages:
                print(f"  → Page IDs in this batch: {[p.get('id', '')[:8] + '...' for p in pages[:5]]}")
            
            # Check if we should stop
            if max_pages and len(all_pages) + len(pages) >= max_pages:
                # Take only what we need
                pages = pages[:max_pages - len(all_pages)]
                all_pages.extend(pages)
                print(f"  → Reached max_pages limit ({max_pages}), stopping")
                break
            
            all_pages.extend(pages)
            
            # Check if there are more pages
            has_more = has_more_result
            start_cursor = next_cursor
            page_number += 1
            
            # Safety check: limit total pages fetched
            if page_number > 1000:
                print(f"  → Reached safety limit (1000 pages), stopping")
                break
        
        # Format pages
        formatted_pages = []
        archived_count = 0
        for page in all_pages:
            # Check if page is archived
            is_archived = page.get("archived", False)
            if not include_archived and is_archived:
                archived_count += 1
                continue
            
            # Extract title from properties
            title = "Untitled"
            if "properties" in page:
                for prop_name, prop_data in page["properties"].items():
                    if prop_data.get("type") == "title" and prop_data.get("title"):
                        title = prop_data["title"][0].get("plain_text", "Untitled")
                        break
            
            # Return full page data for wellness analysis, but also include formatted version
            formatted_page = {
                "id": page.get("id"),
                "title": title,
                "url": page.get("url", ""),
                "created_time": page.get("created_time", ""),
                "last_edited_time": page.get("last_edited_time", ""),
                "archived": page.get("archived", False),
                # Include full page data for wellness analysis
                "properties": page.get("properties", {}),
                "raw_data": page  # Keep full raw data for advanced analysis
            }
            formatted_pages.append(formatted_page)
        
        print(f"✅ Total: Fetched {len(formatted_pages)} pages from Notion")
        print(f"   - Raw pages from API: {len(all_pages)}")
        print(f"   - Archived pages filtered: {archived_count}")
        print(f"   - Final page count: {len(formatted_pages)}")
        
        if len(all_pages) < 10:
            print(f"⚠️  WARNING: Only {len(all_pages)} pages found. This might indicate:")
            print(f"   1. The Notion integration doesn't have access to all pages")
            print(f"   2. Pages are in a different workspace/database")
            print(f"   3. Pages need to be shared with the integration")
            print(f"   → Check Notion integration permissions and share pages with the integration")
        
        return formatted_pages
    except Exception as e:
        print(f"Error fetching Notion pages: {str(e)}")
        raise


def get_page_content(access_token: str, page_id: str) -> Dict:
    """Get content of a specific Notion page."""
    try:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        }
        
        # Get page
        url = f"https://api.notion.com/v1/pages/{page_id}"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        page = response.json()
        
        # Get page blocks (handle pagination)
        blocks = []
        blocks_url = f"https://api.notion.com/v1/blocks/{page_id}/children"
        has_more = True
        start_cursor = None
        
        while has_more:
            params = {}
            if start_cursor:
                params["start_cursor"] = start_cursor
            
            blocks_response = requests.get(blocks_url, headers=headers, params=params)
            blocks_response.raise_for_status()
            
            data = blocks_response.json()
            blocks.extend(data.get("results", []))
            has_more = data.get("has_more", False)
            start_cursor = data.get("next_cursor")

        
        # Extract text content from blocks
        content = []
        for block in blocks:
            block_type = block.get("type")
            # Handle more block types for better content extraction
            if block_type in ["paragraph", "heading_1", "heading_2", "heading_3", "heading_4", 
                            "bulleted_list_item", "numbered_list_item", "to_do", "toggle"]:
                block_data = block.get(block_type, {})
                rich_text = block_data.get("rich_text", [])
                if rich_text:
                    text = " ".join([rt.get("plain_text", "") for rt in rich_text])
                    if text.strip():  # Only add non-empty text
                        # Preserve list structure
                        if block_type in ["bulleted_list_item", "numbered_list_item"]:
                            prefix = "- " if block_type == "bulleted_list_item" else "1. "
                            text = prefix + text
                        elif block_type == "to_do":
                            checked = block_data.get("checked", False)
                            prefix = "[x] " if checked else "[ ] "
                            text = prefix + text
                        elif block_type.startswith("heading"):
                            # Add heading markers for structure
                            level = block_type.split("_")[1]
                            text = "#" * int(level) + " " + text
                        
                        content.append({
                            "type": block_type,
                            "text": text
                        })
            
            # Handle nested children (for toggle blocks, etc.) - handle pagination
            if "has_children" in block and block.get("has_children"):
                children_blocks = []
                children_url = f"https://api.notion.com/v1/blocks/{block.get('id')}/children"
                children_has_more = True
                children_cursor = None
                
                while children_has_more:
                    children_params = {}
                    if children_cursor:
                        children_params["start_cursor"] = children_cursor
                    
                    children_response = requests.get(children_url, headers=headers, params=children_params)
                    children_response.raise_for_status()
                    children_data = children_response.json()
                    children_blocks.extend(children_data.get("results", []))
                    children_has_more = children_data.get("has_more", False)
                    children_cursor = children_data.get("next_cursor")
                
                # Process children blocks
                for child_block in children_blocks:
                    child_type = child_block.get("type")
                    if child_type in ["paragraph", "heading_1", "heading_2", "heading_3", "bulleted_list_item", "numbered_list_item"]:
                        child_data = child_block.get(child_type, {})
                        child_rich_text = child_data.get("rich_text", [])
                        if child_rich_text:
                            child_text = " ".join([rt.get("plain_text", "") for rt in child_rich_text])
                            if child_text.strip():
                                content.append({
                                    "type": child_type,
                                    "text": "  " + child_text  # Indent child content
                                })
        
        return {
            "page_id": page_id,
            "content": content,
            "blocks": blocks
        }
        
    except Exception as e:
        print(f"Error fetching Notion page content: {str(e)}")
        raise


def create_notion_page(
    access_token: str,
    database_id: Optional[str],
    title: str,
    description: Optional[str] = None,
    properties: Optional[Dict[str, Any]] = None
) -> Dict:
    """Create a new page in a Notion database.
    
    Args:
        access_token: Notion API access token
        database_id: Notion database ID (if None, creates a standalone page)
        title: Page title
        description: Page description/content
        properties: Additional properties for database pages (priority, status, owner, etc.)
    
    Returns:
        Created page data
    """
    try:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        }
        
        # Build page properties
        page_properties = {}
        
        if database_id:
            # Create page in database
            # Title property
            page_properties["Title"] = {
                "title": [
                    {
                        "text": {
                            "content": title
                        }
                    }
                ]
            }
            
            # Add custom properties if provided
            if properties:
                # Priority property
                if "priority" in properties:
                    priority_map = {"high": "High", "medium": "Medium", "low": "Low"}
                    page_properties["Priority"] = {
                        "select": {
                            "name": priority_map.get(properties["priority"], "Medium")
                        }
                    }
                
                # Status property
                if "status" in properties:
                    # Map status values
                    status_value = properties["status"]
                    if status_value == "Backlog":
                        status_name = "Backlog"
                    elif status_value in ["approved", "In Progress"]:
                        status_name = "In Progress"
                    elif status_value == "done":
                        status_name = "Done"
                    else:
                        status_name = "Not Started"
                    
                    page_properties["Status"] = {
                        "select": {
                            "name": status_name
                        }
                    }
                
                # Owner/Assignee property
                if "owner" in properties and properties["owner"]:
                    page_properties["Owner"] = {
                        "rich_text": [
                            {
                                "text": {
                                    "content": properties["owner"]
                                }
                            }
                        ]
                    }
                
                # Tags property
                if "tags" in properties and properties["tags"]:
                    tags_list = properties["tags"] if isinstance(properties["tags"], list) else json.loads(properties["tags"]) if isinstance(properties["tags"], str) else []
                    page_properties["Tags"] = {
                        "multi_select": [
                            {"name": tag} for tag in tags_list[:10]  # Limit to 10 tags
                        ]
                    }
                
                # Story Points property
                if "story_points" in properties and properties["story_points"]:
                    page_properties["Story Points"] = {
                        "number": properties["story_points"]
                    }
                
                # Product property
                if "product" in properties and properties["product"]:
                    page_properties["Product"] = {
                        "rich_text": [
                            {
                                "text": {
                                    "content": properties["product"]
                                }
                            }
                        ]
                    }
                
                # Sort Ranking property (for sorting in Notion)
                if "sort_ranking" in properties and properties["sort_ranking"]:
                    page_properties["Sort Ranking"] = {
                        "number": properties["sort_ranking"]
                    }
                
                # Source property (link to report page)
                if "source" in properties and properties["source"]:
                    page_properties["Source"] = {
                        "url": properties["source"]
                    }
            
            payload = {
                "parent": {
                    "database_id": database_id
                },
                "properties": page_properties
            }
            
            url = "https://api.notion.com/v1/pages"
            
            # Create page
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            page = response.json()
            
            # Add description as content blocks if provided
            if description:
                page_id = page.get("id")
                if page_id:
                    blocks_url = f"https://api.notion.com/v1/blocks/{page_id}/children"
                    blocks_payload = {
                        "children": [
                            {
                                "object": "block",
                                "type": "paragraph",
                                "paragraph": {
                                    "rich_text": [
                                        {
                                            "type": "text",
                                            "text": {
                                                "content": description
                                            }
                                        }
                                    ]
                                }
                            }
                        ]
                    }
                    
                    blocks_response = requests.patch(blocks_url, json=blocks_payload, headers=headers)
                    blocks_response.raise_for_status()
            
            return page
        else:
            # Create standalone page (no database) - must have a parent page
            # This function should not be called without database_id or parent_page_id
            raise ValueError("Cannot create standalone page without database_id or parent_page_id. Use create_page_under_parent instead.")
            
    except Exception as e:
        print(f"Error creating Notion page: {str(e)}")
        raise


def create_page_under_parent(access_token: str, parent_page_id: str, title: str) -> Dict:
    """Create a child page under a parent page.
    
    Args:
        access_token: Notion API access token
        parent_page_id: Parent page ID
        title: Page title
    
    Returns:
        Created page data
    """
    try:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        }
        
        payload = {
            "parent": {
                "page_id": parent_page_id
            },
            "properties": {
                "title": {
                    "title": [
                        {
                            "text": {
                                "content": title
                            }
                        }
                    ]
                }
            }
        }
        
        response = requests.post("https://api.notion.com/v1/pages", json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
        
    except Exception as e:
        print(f"Error creating page under parent: {str(e)}")
        raise


def add_blocks_to_page(access_token: str, page_id: str, blocks: List[Dict]) -> bool:
    """Add content blocks to a Notion page.
    
    Args:
        access_token: Notion API access token
        page_id: Page ID to add blocks to
        blocks: List of block objects to add
    
    Returns:
        True if successful, False otherwise
    """
    try:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        }
        
        blocks_url = f"https://api.notion.com/v1/blocks/{page_id}/children"
        
        # Add blocks in batches (Notion API limit is 100 blocks per request)
        batch_size = 100
        for i in range(0, len(blocks), batch_size):
            batch = blocks[i:i + batch_size]
            blocks_payload = {
                "children": batch
            }
            
            batch_response = requests.patch(blocks_url, json=blocks_payload, headers=headers)
            
            if batch_response.status_code != 200:
                error_text = batch_response.text
                print(f"❌ Error adding blocks to Notion page: {batch_response.status_code} - {error_text}")
                return False
        
        return True
        
    except Exception as e:
        print(f"Error adding blocks to page: {str(e)}")
        return False


def find_notion_database(access_token: str, database_name: Optional[str] = "Backlog") -> Optional[str]:
    """Find a Notion database by name.
    
    Args:
        access_token: Notion API access token
        database_name: Name of the database to find
    
    Returns:
        Database ID if found, None otherwise
    """
    try:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        }
        
        # Search for databases
        url = "https://api.notion.com/v1/search"
        payload = {
            "filter": {
                "property": "object",
                "value": "database"
            },
            "page_size": 100
        }
        
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        databases = data.get("results", [])
        
        # Find database by title
        for db in databases:
            title_prop = db.get("title", [])
            if title_prop:
                db_title = title_prop[0].get("plain_text", "")
                if database_name.lower() in db_title.lower():
                    return db.get("id")
        
        # If not found, return first database or None
        if databases:
            return databases[0].get("id")
        
        return None
        
    except Exception as e:
        print(f"Error finding Notion database: {str(e)}")
        return None
