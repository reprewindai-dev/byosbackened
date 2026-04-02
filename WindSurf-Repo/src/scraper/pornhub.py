"""PornHub scraper for content aggregation."""

import httpx
import re
import json
import asyncio
from typing import List, Dict, Optional, Any
from urllib.parse import urlencode, quote
import logging
from datetime import datetime
from src.scraper.rate_limiter import ScraperConfig, safe_request
from src.scraper.privacy import PrivacyManager, AnonymousClient
from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class PornHubScraper:
    """Advanced PornHub scraper with multiple methods."""

    def __init__(self):
        self.base_url = "https://www.pornhub.com"
        self.api_url = "https://www.pornhub.com/webmasters/search"
        self.rate_limiter = ScraperConfig.get_rate_limiter()

        # Use privacy manager for anonymity (mobile mode enabled)
        self.privacy_manager = PrivacyManager(
            use_proxy=settings.use_proxy and bool(settings.proxy_url),
            proxy_url=settings.proxy_url if settings.use_proxy else None,
            rotate_user_agent=settings.rotate_user_agents,
            random_referer=settings.random_referers,
            mobile_mode=getattr(settings, "mobile_mode", True),  # Mobile mode by default
            location_randomization=getattr(
                settings, "location_randomization", True
            ),  # Location randomization by default
            session_rotation_minutes=getattr(
                settings, "session_rotation_minutes", 60
            ),  # Rotate every 60 minutes
        )

        # Use anonymous client wrapper
        self.anonymous_client = AnonymousClient(privacy_manager=self.privacy_manager)
        # Use anonymous client for requests
        self.client = self.anonymous_client

    async def search(
        self,
        query: str,
        category: Optional[str] = None,
        page: int = 1,
        limit: int = 50,
        min_duration: Optional[int] = None,
        max_duration: Optional[int] = None,
        ordering: str = "mostviewed",  # mostviewed, mostrelevant, rating, newest
    ) -> List[Dict[str, Any]]:
        """
        Search PornHub videos.

        Args:
            query: Search query
            category: Category filter (e.g., 'lesbian', 'solo-female')
            page: Page number
            limit: Maximum results to return
            min_duration: Minimum duration in seconds
            max_duration: Maximum duration in seconds
            ordering: Sort order (mostviewed, mostrelevant, rating, newest)
        """
        try:
            # Method 1: Try webmasters API first (official API)
            videos = await self._search_api(query, category, page, limit, ordering)

            # If API fails or returns few results, try web scraping
            if len(videos) < limit:
                scraped = await self._search_scrape(query, category, page, limit - len(videos))
                # Merge and deduplicate
                existing_ids = {v.get("source_id") for v in videos}
                for video in scraped:
                    if video.get("source_id") not in existing_ids:
                        videos.append(video)

            # Filter by duration if specified
            if min_duration or max_duration:
                filtered = []
                for video in videos:
                    duration = video.get("duration", 0)
                    if min_duration and duration < min_duration:
                        continue
                    if max_duration and duration > max_duration:
                        continue
                    filtered.append(video)
                videos = filtered

            return videos[:limit]

        except Exception as e:
            logger.error(f"PornHub search error: {e}", exc_info=True)
            return []

    async def _search_api(
        self,
        query: str,
        category: Optional[str],
        page: int,
        limit: int,
        ordering: str,
    ) -> List[Dict[str, Any]]:
        """Search using PornHub webmasters API."""
        try:
            params = {
                "q": query,
                "page": page,
                "thumbsize": "large",
                "ordering": ordering,
            }

            if category:
                params["category"] = category

            response = await self.client.get(self.api_url, params=params)

            if response.status_code == 200:
                data = response.json()
                videos = data.get("videos", [])

                return [self._parse_api_video(v) for v in videos]
        except Exception as e:
            logger.warning(f"API search failed: {e}")

        return []

    async def _search_scrape(
        self,
        query: str,
        category: Optional[str],
        page: int,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """Scrape search results from HTML."""
        try:
            # Build search URL
            search_path = "/video/search"
            params = {
                "search": query,
                "page": page,
            }

            if category:
                search_path = f"/video/search/category/{category}"

            url = f"{self.base_url}{search_path}?{urlencode(params)}"

            response = await self.client.get(url)

            if response.status_code == 200:
                html = response.text
                return self._parse_html_videos(html, limit)
        except Exception as e:
            logger.warning(f"Scrape search failed: {e}")

        return []

    def _parse_api_video(self, video_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse video data from API response."""
        return {
            "title": video_data.get("title", ""),
            "url": self._build_video_url(video_data.get("url", "")),
            "thumbnail": video_data.get("thumb", ""),
            "duration": int(video_data.get("duration", 0)),
            "views": int(video_data.get("views", 0)),
            "rating": float(video_data.get("rating", 0)),
            "tags": [tag.get("tag_name", "") for tag in video_data.get("tags", [])],
            "performers": [p.get("performer_name", "") for p in video_data.get("pornstars", [])],
            "source_api": "pornhub",
            "source_id": str(video_data.get("video_id", "")),
            "quality": video_data.get("hd", False) and "HD" or "SD",
            "created_at": video_data.get("publish_date", ""),
        }

    def _parse_html_videos(self, html: str, limit: int) -> List[Dict[str, Any]]:
        """Parse videos from HTML page."""
        videos = []

        # Extract video data from embedded JSON
        # PornHub embeds video data in script tags
        script_pattern = r"<script[^>]*>window\.__INITIAL_STATE__\s*=\s*({.+?});</script>"
        match = re.search(script_pattern, html, re.DOTALL)

        if match:
            try:
                data = json.loads(match.group(1))
                # Navigate through the data structure to find videos
                # This structure may vary, so we'll also try regex fallback
                video_list = data.get("video", {}).get("list", [])
                for video_data in video_list[:limit]:
                    videos.append(self._parse_html_video(video_data))
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Failed to parse embedded JSON: {e}")

        # Fallback: Extract from HTML structure
        if not videos:
            videos = self._parse_html_fallback(html, limit)

        return videos

    def _parse_html_video(self, video_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse single video from HTML data."""
        return {
            "title": video_data.get("title", ""),
            "url": self._build_video_url(video_data.get("url", "")),
            "thumbnail": video_data.get("thumb", ""),
            "duration": int(video_data.get("duration", 0)),
            "views": int(video_data.get("views", 0)),
            "rating": float(video_data.get("rating", 0)),
            "tags": video_data.get("tags", []),
            "performers": video_data.get("pornstars", []),
            "source_api": "pornhub",
            "source_id": str(video_data.get("id", "")),
            "quality": "HD" if video_data.get("hd", False) else "SD",
        }

    def _parse_html_fallback(self, html: str, limit: int) -> List[Dict[str, Any]]:
        """Fallback HTML parsing using regex."""
        videos = []

        # Pattern to match video links
        video_pattern = r'<a[^>]*href="(/view_video\.php\?viewkey=[^"]+)"[^>]*>'
        matches = re.findall(video_pattern, html)

        for match in matches[:limit]:
            video_url = f"{self.base_url}{match}"
            # Extract title from surrounding HTML
            title_match = re.search(
                r'<span[^>]*class="title"[^>]*>([^<]+)</span>',
                html[html.find(match) : html.find(match) + 2000],
            )
            title = title_match.group(1) if title_match else "Untitled"

            videos.append(
                {
                    "title": title.strip(),
                    "url": video_url,
                    "thumbnail": "",
                    "duration": 0,
                    "views": 0,
                    "rating": 0,
                    "tags": [],
                    "performers": [],
                    "source_api": "pornhub",
                    "source_id": match.split("viewkey=")[-1] if "viewkey=" in match else "",
                    "quality": "SD",
                }
            )

        return videos

    def _build_video_url(self, url: str) -> str:
        """Build full video URL."""
        if not url:
            return ""
        if url.startswith("http"):
            return url
        if url.startswith("/"):
            return f"{self.base_url}{url}"
        return f"{self.base_url}/{url}"

    async def get_categories(self) -> List[Dict[str, Any]]:
        """Get available categories."""
        return [
            {"name": "Lesbian", "slug": "lesbian", "description": "Lesbian content"},
            {
                "name": "Solo Female",
                "slug": "solo-female",
                "description": "Solo female masturbation",
            },
            {"name": "Squirting", "slug": "squirting", "description": "Squirting content"},
            {"name": "Masturbation", "slug": "masturbation", "description": "Masturbation videos"},
            {"name": "Kissing", "slug": "kissing", "description": "Kissing and making out"},
            {"name": "PMV", "slug": "pmv", "description": "Porn Music Videos"},
            {"name": "Long Session", "slug": "long-session", "description": "Long session videos"},
            {"name": "Sloppy", "slug": "sloppy", "description": "Sloppy kissing and more"},
            {"name": "Cam Girls", "slug": "cam-girls", "description": "Cam girl content"},
            {"name": "Gooning", "slug": "gooning", "description": "Gooning content"},
        ]

    async def get_video_details(self, video_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific video."""
        try:
            url = f"{self.base_url}/webmasters/video_by_id"
            params = {"id": video_id}

            response = await self.client.get(url, params=params)

            if response.status_code == 200:
                data = response.json()
                video = data.get("video", {})

                return {
                    "title": video.get("title", ""),
                    "url": self._build_video_url(video.get("url", "")),
                    "thumbnail": video.get("thumb", ""),
                    "duration": int(video.get("duration", 0)),
                    "views": int(video.get("views", 0)),
                    "rating": float(video.get("rating", 0)),
                    "tags": [tag.get("tag_name", "") for tag in video.get("tags", [])],
                    "performers": [p.get("performer_name", "") for p in video.get("pornstars", [])],
                    "description": video.get("description", ""),
                    "source_api": "pornhub",
                    "source_id": str(video.get("video_id", "")),
                    "quality": "HD" if video.get("hd", False) else "SD",
                    "created_at": video.get("publish_date", ""),
                }
        except Exception as e:
            logger.error(f"Failed to get video details: {e}")

        return None

    async def get_trending(
        self,
        category: Optional[str] = None,
        period: str = "daily",  # daily, weekly, monthly, yearly, alltime
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get trending videos."""
        try:
            url = f"{self.base_url}/webmasters/videos"
            params = {
                "period": period,
                "thumbsize": "large",
            }

            if category:
                params["category"] = category

            response = await self.client.get(url, params=params)

            if response.status_code == 200:
                data = response.json()
                videos = data.get("videos", [])[:limit]

                return [self._parse_api_video(v) for v in videos]
        except Exception as e:
            logger.error(f"Failed to get trending: {e}")

        return []

    async def get_category_videos(
        self,
        category: str,
        page: int = 1,
        limit: int = 50,
        ordering: str = "mostviewed",
    ) -> List[Dict[str, Any]]:
        """Get videos from a specific category."""
        return await self.search("", category=category, page=page, limit=limit, ordering=ordering)

    async def close(self):
        """Close HTTP client."""
        await self.anonymous_client.close()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
