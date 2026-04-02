"""Content API integration services for aggregating content from free APIs."""

import httpx
import asyncio
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime
from core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class ContentAPIClient:
    """Base class for content API clients."""

    def __init__(self, api_name: str, base_url: str, api_key: Optional[str] = None):
        self.api_name = api_name
        self.base_url = base_url
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=30.0)

    async def search(
        self, query: str, category: Optional[str] = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Search for content. Override in subclasses."""
        raise NotImplementedError

    async def get_categories(self) -> List[Dict[str, Any]]:
        """Get available categories. Override in subclasses."""
        raise NotImplementedError

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
        if hasattr(self, "scraper"):
            await self.scraper.close()


class PornHubAPIClient(ContentAPIClient):
    """PornHub API client (using advanced scraper)."""

    def __init__(self):
        super().__init__("pornhub", "https://www.pornhub.com")
        # Import scraper here to avoid circular imports
        from src.scraper.pornhub import PornHubScraper

        self.scraper = PornHubScraper()

    async def search(
        self, query: str, category: Optional[str] = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Search PornHub videos using advanced scraper."""
        try:
            videos = await self.scraper.search(
                query=query, category=category, limit=limit, ordering="mostviewed"
            )

            # Convert to standard format
            return [
                {
                    "title": v.get("title", ""),
                    "url": v.get("url", ""),
                    "thumbnail": v.get("thumbnail", ""),
                    "duration": v.get("duration", 0),
                    "views": v.get("views", 0),
                    "rating": v.get("rating", 0),
                    "tags": v.get("tags", []),
                    "source_api": "pornhub",
                    "source_id": v.get("source_id", ""),
                }
                for v in videos
            ]
        except Exception as e:
            print(f"PornHub scraper error: {e}")
        return []

    async def get_categories(self) -> List[Dict[str, Any]]:
        """Get PornHub categories."""
        try:
            return await self.scraper.get_categories()
        except Exception as e:
            print(f"Failed to get categories: {e}")
            return [
                {"name": "Lesbian", "slug": "lesbian"},
                {"name": "Solo Female", "slug": "solo-female"},
                {"name": "Squirting", "slug": "squirting"},
                {"name": "Masturbation", "slug": "masturbation"},
                {"name": "Kissing", "slug": "kissing"},
                {"name": "PMV", "slug": "pmv"},
            ]


class RedTubeAPIClient(ContentAPIClient):
    """RedTube API client."""

    def __init__(self):
        super().__init__("redtube", "https://api.redtube.com")

    async def search(
        self, query: str, category: Optional[str] = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Search RedTube videos."""
        try:
            url = f"{self.base_url}/"
            params = {
                "data": "redtube.Videos.searchVideos",
                "output": "json",
                "search": query,
                "thumbsize": "big",
                "page": 1,
            }
            if category:
                params["category"] = category

            response = await self.client.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                videos = data.get("videos", [])[:limit]

                return [
                    {
                        "title": v.get("title", ""),
                        "url": v.get("url", ""),
                        "thumbnail": v.get("thumb", ""),
                        "duration": v.get("duration", 0),
                        "views": v.get("views", 0),
                        "rating": v.get("rating", 0),
                        "tags": [t.get("tag_name", "") for t in v.get("tags", [])],
                        "source_api": "redtube",
                        "source_id": str(v.get("video_id", "")),
                    }
                    for v in videos
                ]
        except Exception as e:
            print(f"RedTube API error: {e}")
        return []


class XHamsterAPIClient(ContentAPIClient):
    """XHamster API client (using advanced scraper)."""

    def __init__(self):
        super().__init__("xhamster", "https://xhamster.com")
        from src.scraper.xhamster import XHamsterScraper

        self.scraper = XHamsterScraper()

    async def search(
        self, query: str, category: Optional[str] = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Search XHamster videos using advanced scraper."""
        try:
            videos = await self.scraper.search(
                query=query, category=category, limit=limit, ordering="mostviewed"
            )

            # Convert to standard format
            return [
                {
                    "title": v.get("title", ""),
                    "url": v.get("url", ""),
                    "thumbnail": v.get("thumbnail", ""),
                    "duration": v.get("duration", 0),
                    "views": v.get("views", 0),
                    "rating": v.get("rating", 0),
                    "tags": v.get("tags", []),
                    "source_api": "xhamster",
                    "source_id": v.get("source_id", ""),
                }
                for v in videos
            ]
        except Exception as e:
            print(f"XHamster scraper error: {e}")
        return []

    async def get_categories(self) -> List[Dict[str, Any]]:
        """Get XHamster categories."""
        try:
            return await self.scraper.get_categories()
        except Exception as e:
            print(f"Failed to get categories: {e}")
            return []

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
        if hasattr(self, "scraper"):
            await self.scraper.close()


class NSFWAPI2APIClient(ContentAPIClient):
    """NSFW-API2 client wrapper."""

    def __init__(self):
        super().__init__("nsfw-api2", "https://nsfw-api-p302.onrender.com")
        from src.scraper.nsfw_api2 import NSFWAPI2Client

        self.scraper = NSFWAPI2Client()

    async def search(
        self, query: str, category: Optional[str] = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Search NSFW-API2 videos."""
        try:
            # Search both real and hentai videos
            videos = await self.scraper.search_all(
                query=query,
                include_hentai=True,
                include_real=True,
                limit_per_type=limit // 2,
            )

            # Convert to standard format
            return [
                {
                    "title": v.get("title", ""),
                    "url": v.get("url", ""),
                    "thumbnail": v.get("thumbnail", ""),
                    "duration": v.get("duration", 0),
                    "views": v.get("views", 0),
                    "rating": v.get("rating", 0),
                    "tags": v.get("tags", []),
                    "source_api": "nsfw-api2",
                    "source_id": v.get("source_id", ""),
                }
                for v in videos[:limit]
            ]
        except Exception as e:
            print(f"NSFW-API2 error: {e}")
        return []

    async def get_categories(self) -> List[Dict[str, Any]]:
        """Get NSFW-API2 categories/tags."""
        try:
            tags = await self.scraper.get_available_tags()
            return [{"name": tag.title(), "slug": tag} for tag in tags]
        except Exception as e:
            print(f"Failed to get categories: {e}")
            return []

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
        if hasattr(self, "scraper"):
            await self.scraper.close()


class NSFWAPI2APIClient(ContentAPIClient):
    """NSFW-API2 client wrapper."""

    def __init__(self):
        super().__init__("nsfw-api2", "https://nsfw-api-p302.onrender.com")
        from src.scraper.nsfw_api2 import NSFWAPI2Client

        self.scraper = NSFWAPI2Client()

    async def search(
        self, query: str, category: Optional[str] = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Search NSFW-API2 videos."""
        try:
            # Search both real and hentai videos
            videos = await self.scraper.search_all(
                query=query,
                include_hentai=True,
                include_real=True,
                limit_per_type=limit // 2,
            )

            # Convert to standard format
            return [
                {
                    "title": v.get("title", ""),
                    "url": v.get("url", ""),
                    "thumbnail": v.get("thumbnail", ""),
                    "duration": v.get("duration", 0),
                    "views": v.get("views", 0),
                    "rating": v.get("rating", 0),
                    "tags": v.get("tags", []),
                    "source_api": "nsfw-api2",
                    "source_id": v.get("source_id", ""),
                }
                for v in videos[:limit]
            ]
        except Exception as e:
            print(f"NSFW-API2 error: {e}")
        return []

    async def get_categories(self) -> List[Dict[str, Any]]:
        """Get NSFW-API2 categories/tags."""
        try:
            tags = await self.scraper.get_available_tags()
            return [{"name": tag.title(), "slug": tag} for tag in tags]
        except Exception as e:
            print(f"Failed to get categories: {e}")
            return []

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
        if hasattr(self, "scraper"):
            await self.scraper.close()


class ContentAggregator:
    """Aggregates content from multiple APIs with rate limiting."""

    def __init__(self):
        self.clients = [
            PornHubAPIClient(),
            RedTubeAPIClient(),
            XHamsterAPIClient(),
            LustPressAPIClient(),
            NSFWAPI2APIClient(),
        ]
        # Import rate limiter
        from src.scraper.rate_limiter import ScraperConfig

        self.rate_limiter = ScraperConfig.get_rate_limiter()

    async def search_all(
        self, query: str, category: Optional[str] = None, limit_per_api: int = 20
    ) -> List[Dict[str, Any]]:
        """Search all APIs and aggregate results with rate limiting."""
        # Process clients sequentially with delays to avoid overwhelming servers
        all_videos = []

        for i, client in enumerate(self.clients):
            try:
                # Add delay between different API calls
                if i > 0:
                    await asyncio.sleep(3)  # 3 second delay between APIs

                videos = await client.search(query, category, limit_per_api)
                if isinstance(videos, list):
                    all_videos.extend(videos)

            except Exception as e:
                logger.warning(f"API search error from {client.api_name}: {e}")
                # Don't fail completely, just skip this API
                continue

        # Remove duplicates based on title similarity
        seen_titles = set()
        unique_videos = []
        for video in all_videos:
            title_lower = video.get("title", "").lower()
            if title_lower not in seen_titles:
                seen_titles.add(title_lower)
                unique_videos.append(video)

        return unique_videos

    async def get_all_categories(self) -> List[Dict[str, Any]]:
        """Get categories from all APIs."""
        tasks = [client.get_categories() for client in self.clients]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_categories = []
        seen_slugs = set()
        for result in results:
            if isinstance(result, list):
                for cat in result:
                    slug = cat.get("slug", "")
                    if slug and slug not in seen_slugs:
                        seen_slugs.add(slug)
                        all_categories.append(cat)

        return all_categories

    async def close(self):
        """Close all API clients."""
        for client in self.clients:
            await client.close()
