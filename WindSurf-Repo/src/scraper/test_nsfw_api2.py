"""Test script for NSFW-API2 client."""

import asyncio
import sys
from pathlib import Path

import pytest

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.scraper.nsfw_api2 import NSFWAPI2Client

pytestmark = pytest.mark.skip(reason="integration scraper test")


async def test_client():
    """Test the NSFW-API2 client."""
    client = NSFWAPI2Client()

    try:
        print("=" * 60)
        print("NSFW-API2 Client Test")
        print("=" * 60)
        print()

        # Test 1: Get available tags
        print("1. Getting available tags...")
        tags = await client.get_available_tags()
        print(f"   Found {len(tags)} tags:")
        for tag in tags[:10]:
            print(f"   - {tag}")
        print()

        # Test 2: Search hentai videos
        print("2. Searching hentai videos...")
        hentai_videos = await client.search_hentai_videos("lesbian", limit=5)
        print(f"   Found {len(hentai_videos)} hentai videos:")
        for i, video in enumerate(hentai_videos[:3], 1):
            print(f"   {i}. {video.get('title', 'N/A')[:60]}")
        print()

        # Test 3: Search real videos
        print("3. Searching real videos...")
        real_videos = await client.search_real_videos("lesbian", limit=5)
        print(f"   Found {len(real_videos)} real videos:")
        for i, video in enumerate(real_videos[:3], 1):
            print(f"   {i}. {video.get('title', 'N/A')[:60]}")
        print()

        # Test 4: Search images by tag
        print("4. Searching images by tag...")
        images = await client.search_real_images_by_tag("lesbian", limit=5)
        print(f"   Found {len(images)} images:")
        for i, image in enumerate(images[:3], 1):
            print(f"   {i}. {image.get('title', 'N/A')[:60]}")
        print()

        # Test 5: Search all
        print("5. Searching all content types...")
        all_content = await client.search_all("lesbian", limit_per_type=3)
        print(f"   Found {len(all_content)} total items")
        print()

        print("=" * 60)
        print("All tests completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(test_client())
