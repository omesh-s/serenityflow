"""Utility functions for Notion API."""
import requests
from typing import List, Dict, Optional
from datetime import datetime
from config import settings


def get_notion_pages(access_token: str, page_size: int = 10) -> List[Dict]:
    """Fetch pages from Notion workspace."""
    try:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        }
        
        # Search for pages in the workspace
        url = "https://api.notion.com/v1/search"
        payload = {
            "filter": {
                "property": "object",
                "value": "page"
            },
            "page_size": page_size,
            "sort": {
                "direction": "descending",
                "timestamp": "last_edited_time"
            }
        }
        
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        pages = data.get("results", [])
        
        formatted_pages = []
        for page in pages:
            # Extract title from properties
            title = "Untitled"
            if "properties" in page:
                for prop_name, prop_data in page["properties"].items():
                    if prop_data.get("type") == "title" and prop_data.get("title"):
                        title = prop_data["title"][0].get("plain_text", "Untitled")
                        break
            
            formatted_pages.append({
                "id": page.get("id"),
                "title": title,
                "url": page.get("url", ""),
                "created_time": page.get("created_time", ""),
                "last_edited_time": page.get("last_edited_time", ""),
                "archived": page.get("archived", False),
            })
        
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
        
        # Get page blocks
        blocks_url = f"https://api.notion.com/v1/blocks/{page_id}/children"
        blocks_response = requests.get(blocks_url, headers=headers)
        blocks_response.raise_for_status()
        
        blocks = blocks_response.json().get("results", [])
        
        # Extract text content from blocks
        content = []
        for block in blocks:
            block_type = block.get("type")
            if block_type in ["paragraph", "heading_1", "heading_2", "heading_3"]:
                block_data = block.get(block_type, {})
                rich_text = block_data.get("rich_text", [])
                if rich_text:
                    text = " ".join([rt.get("plain_text", "") for rt in rich_text])
                    content.append({
                        "type": block_type,
                        "text": text
                    })
        
        # Extract title
        title = "Untitled"
        if "properties" in page:
            for prop_name, prop_data in page["properties"].items():
                if prop_data.get("type") == "title" and prop_data.get("title"):
                    title = prop_data["title"][0].get("plain_text", "Untitled")
                    break
        
        return {
            "id": page.get("id"),
            "title": title,
            "url": page.get("url", ""),
            "content": content,
            "created_time": page.get("created_time", ""),
            "last_edited_time": page.get("last_edited_time", ""),
        }
    except Exception as e:
        print(f"Error fetching Notion page content: {str(e)}")
        raise

