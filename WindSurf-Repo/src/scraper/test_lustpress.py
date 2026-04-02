"""Test script for LustPress scraper."""

import asyncio
import sys
from pathlib import Path

import pytest

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.scraper.lustpress import LustPressScraper

pytestmark = pytest.mark.skip(reason="integration scraper test")


async def test_scraper():
    """Test the LustPress scraper."""
    scraper = LustPressScraper()

    try:
        print("=" * 60)
        print("LustPress Scraper Test")
        print("=" * 60)
        print()

        # Test 1: Get categories
        print("1. Getting categories...")
        categories = await scraper.get_categories()
        print(f"   Found {len(categories)} categories:")
        for cat in categories[:5]:
            print(f"   - {cat['name']} ({cat['slug']})")
        print()

        # Test 2: Search videos
        print("2. Searching videos...")
        videos = await scraper.search(
            query="lesbian",
            limit=10,
            min_duration=300,  # At least 5 minutes
        )
        print(f"   Found {len(videos)} videos:")
        for i, video in enumerate(videos[:5], 1):
            print(f"   {i}. {video.get('title', 'N/A')[:60]}")
            print(f"      Duration: {video.get('duration', 0)}s, Views: {video.get('views', 0)}")
        print()

        # Test 3: Get trending
        print("3. Getting trending videos...")
        trending = await scraper.get_trending(period="daily", limit=5)
        print(f"   Found {len(trending)} trending videos")
        print()

        # Test 4: Category browsing
        print("4. Browsing category...")
        category_videos = await scraper.get_category_videos(category="lesbian", page=1, limit=5)
        print(f"   Found {len(category_videos)} videos in category")
        print()

        print("=" * 60)
        print("All tests completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
    finally:
        await scraper.close()


if __name__ == "__main__":
    asyncio.run(test_scraper())
