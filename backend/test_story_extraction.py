"""Test script for story extraction - helps debug issues."""
import sys
from database import SessionLocal, init_db
from utils.token_manager import get_token
from utils.notion import get_notion_pages, get_page_content
from utils.agents.story_extraction_agent import StoryExtractionAgent

def test_story_extraction():
    """Test story extraction with detailed logging."""
    print("=" * 60)
    print("Testing Story Extraction")
    print("=" * 60)
    
    # Initialize database
    print("\n1. Initializing database...")
    init_db()
    
    # Get database session
    db = SessionLocal()
    
    try:
        # Check Notion token
        print("\n2. Checking Notion token...")
        notion_token = get_token(db, "notion")
        if not notion_token:
            print("❌ ERROR: Notion not connected!")
            print("   Please connect Notion in the settings first.")
            return
        print("✅ Notion token found")
        
        # Fetch Notion pages
        print("\n3. Fetching Notion pages...")
        try:
            pages = get_notion_pages(notion_token.access_token, page_size=50)
            print(f"✅ Found {len(pages)} Notion pages")
            
            if len(pages) == 0:
                print("❌ ERROR: No Notion pages found!")
                print("   Make sure you have pages in your workspace.")
                return
            
            # Show page titles
            print("\n4. Pages found:")
            for i, page in enumerate(pages[:10], 1):
                print(f"   {i}. {page.get('title', 'Untitled')} (ID: {page.get('id', 'N/A')[:8]}...)")
                print(f"      Last edited: {page.get('last_edited_time', 'N/A')}")
            
            # Test extracting content from first page
            if len(pages) > 0:
                print("\n5. Testing content extraction from first page...")
                first_page = pages[0]
                try:
                    content = get_page_content(notion_token.access_token, first_page.get("id"))
                    print(f"✅ Page content fetched")
                    print(f"   Title: {content.get('title', 'Untitled')}")
                    print(f"   Content blocks: {len(content.get('content', []))}")
                    
                    # Extract text
                    text_parts = []
                    title = content.get("title", "")
                    if title:
                        text_parts.append(f"Title: {title}")
                    for block in content.get("content", []):
                        block_text = block.get("text", "")
                        if block_text:
                            text_parts.append(block_text)
                    page_text = "\n".join(text_parts)
                    print(f"   Extracted text length: {len(page_text)} characters")
                    
                    if len(page_text) < 50:
                        print("⚠️  WARNING: Page content is very short. Make sure your pages have content.")
                    else:
                        print(f"   First 200 chars: {page_text[:200]}...")
                        
                except Exception as e:
                    print(f"❌ ERROR: Failed to fetch page content: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    return
            
            # Test story extraction agent
            print("\n6. Testing story extraction agent...")
            agent = StoryExtractionAgent(db, "default")
            
            # Run extraction on first few pages
            test_pages = pages[:5]  # Test first 5 pages
            print(f"   Processing {len(test_pages)} pages...")
            
            result = agent.run(notion_pages=test_pages)
            
            print(f"\n7. Extraction results:")
            print(f"   Success: {result.get('success', False)}")
            print(f"   Stories extracted: {result.get('count', 0)}")
            print(f"   Pages processed: {result.get('pages_processed', 0)}")
            print(f"   Pages skipped (already processed): {result.get('pages_skipped_already_processed', 0)}")
            print(f"   Pages skipped (too old): {result.get('pages_skipped_too_old', 0)}")
            print(f"   Total pages: {result.get('total_pages', 0)}")
            
            if result.get('message'):
                print(f"   Message: {result.get('message')}")
            
            if result.get('error'):
                print(f"   Error: {result.get('error')}")
            
            if result.get('count', 0) > 0:
                print(f"\n✅ Success! Extracted {result.get('count')} stories:")
                for story in result.get('stories', [])[:5]:
                    print(f"   - {story.get('title')} (Priority: {story.get('priority')})")
            else:
                print("\n⚠️  No stories extracted.")
                print("   This could mean:")
                print("   - Pages don't contain extractable action items")
                print("   - Pages are too old (older than 30 days)")
                print("   - Pages have already been processed")
                print("   - Gemini API failed to extract stories")
                print("\n   Check the backend logs for more details.")
                
        except Exception as e:
            print(f"❌ ERROR: Failed to fetch Notion pages: {str(e)}")
            import traceback
            traceback.print_exc()
            
    finally:
        db.close()
    
    print("\n" + "=" * 60)
    print("Test complete!")
    print("=" * 60)

if __name__ == "__main__":
    test_story_extraction()

