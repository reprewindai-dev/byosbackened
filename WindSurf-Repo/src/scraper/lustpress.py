"""LustPress scraper for content aggregation."""

import httpx
import re
import json
from typing import List, Dict, Optional, Any
from urllib.parse import urlencode, quote, urljoin
import logging
from datetime import datetime
from src.scraper.utils import extract_video_id, clean_title, parse_duration, normalize_category
from src.scraper.privacy import PrivacyManager, AnonymousClient
from src.scraper.rate_limiter import ScraperConfig
from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class LustPressScraper:
    """LustPress scraper with web scraping capabilities."""

    def __init__(self):
        self.base_url = "https://lustpress.com"
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
        self.client = self.anonymous_client

    async def search(
        self,
        query: str,
        category: Optional[str] = None,
        page: int = 1,
        limit: int = 50,
        min_duration: Optional[int] = None,
        max_duration: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search LustPress videos.

        Args:
            query: Search query
            category: Category filter
            page: Page number
            limit: Maximum results to return
            min_duration: Minimum duration in seconds
            max_duration: Maximum duration in seconds
        """
        try:
            # Build search URL
            if query:
                search_path = f"/search/{quote(query)}"
                if page > 1:
                    search_path += f"/{page}"
            elif category:
                search_path = f"/category/{category}"
                if page > 1:
                    search_path += f"/{page}"
            else:
                search_path = "/"
                if page > 1:
                    search_path = f"/page/{page}"

            url = urljoin(self.base_url, search_path)

            response = await self.client.get(url)

            if response.status_code == 200:
                html = response.text
                videos = self._parse_html_videos(html, limit)

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
            logger.error(f"LustPress search error: {e}", exc_info=True)

        return []

    def _parse_html_videos(self, html: str, limit: int) -> List[Dict[str, Any]]:
        """Parse videos from HTML page."""
        videos = []

        # Try to find embedded JSON data
        script_patterns = [
            r"<script[^>]*>window\.__INITIAL_STATE__\s*=\s*({.+?});</script>",
            r"<script[^>]*>window\.__DATA__\s*=\s*({.+?});</script>",
            r"var\s+videos\s*=\s*(\[.+?\]);",
        ]

        for pattern in script_patterns:
            match = re.search(pattern, html, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(1))
                    if isinstance(data, list):
                        videos.extend([self._parse_video_data(v) for v in data[:limit]])
                    elif isinstance(data, dict):
                        video_list = data.get("videos", data.get("items", []))
                        videos.extend([self._parse_video_data(v) for v in video_list[:limit]])
                    if videos:
                        break
                except (json.JSONDecodeError, KeyError) as e:
                    logger.debug(f"Failed to parse JSON pattern: {e}")
                    continue

        # Fallback: Parse HTML structure
        if not videos:
            videos = self._parse_html_structure(html, limit)

        return videos

    def _parse_html_structure(self, html: str, limit: int) -> List[Dict[str, Any]]:
        """Parse videos from HTML structure."""
        videos = []

        # Common video container patterns
        container_patterns = [
            r'<article[^>]*class="[^"]*video[^"]*"[^>]*>(.*?)</article>',
            r'<div[^>]*class="[^"]*video-item[^"]*"[^>]*>(.*?)</div>',
            r'<div[^>]*class="[^"]*post[^"]*"[^>]*>(.*?)</div>',
        ]

        for pattern in container_patterns:
            matches = re.finditer(pattern, html, re.DOTALL)
            for match in matches[:limit]:
                video_html = match.group(1)
                video = self._parse_video_block(video_html)
                if video:
                    videos.append(video)
            if videos:
                break

        return videos

    def _parse_video_block(self, html: str) -> Optional[Dict[str, Any]]:
        """Parse a single video block from HTML."""
        try:
            # Extract title
            title_match = re.search(
                r'<a[^>]*href="([^"]+)"[^>]*>.*?<h[23][^>]*>([^<]+)</h[23]>', html, re.DOTALL
            )
            if not title_match:
                title_match = re.search(r'<a[^>]*href="([^"]+)"[^>]*title="([^"]+)"', html)

            if not title_match:
                return None

            url = urljoin(self.base_url, title_match.group(1))
            title = clean_title(title_match.group(2))

            # Extract thumbnail
            thumb_match = re.search(r'<img[^>]*src="([^"]+)"[^>]*>', html)
            thumbnail = ""
            if thumb_match:
                thumbnail = urljoin(self.base_url, thumb_match.group(1))

            # Extract duration
            duration_match = re.search(
                r'<span[^>]*class="[^"]*duration[^"]*"[^>]*>([^<]+)</span>', html
            )
            duration = 0
            if duration_match:
                duration = parse_duration(duration_match.group(1))

            # Extract views
            views_match = re.search(r'<span[^>]*class="[^"]*views[^"]*"[^>]*>([^<]+)</span>', html)
            views = 0
            if views_match:
                views_str = re.sub(r"[^\d]", "", views_match.group(1))
                views = int(views_str) if views_str else 0

            # Extract video ID from URL
            video_id = extract_video_id(url) or ""

            return {
                "title": title,
                "url": url,
                "thumbnail": thumbnail,
                "duration": duration,
                "views": views,
                "rating": 0.0,
                "tags": [],
                "performers": [],
                "source_api": "lustpress",
                "source_id": video_id,
                "quality": "HD",
            }
        except Exception as e:
            logger.debug(f"Failed to parse video block: {e}")
            return None

    def _parse_video_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse video data from JSON."""
        return {
            "title": clean_title(data.get("title", data.get("name", ""))),
            "url": urljoin(self.base_url, data.get("url", data.get("link", ""))),
            "thumbnail": urljoin(
                self.base_url, data.get("thumb", data.get("thumbnail", data.get("image", "")))
            ),
            "duration": parse_duration(str(data.get("duration", data.get("length", 0)))),
            "views": int(data.get("views", data.get("view_count", 0))),
            "rating": float(data.get("rating", data.get("score", 0))),
            "tags": data.get("tags", data.get("categories", [])),
            "performers": data.get("performers", data.get("pornstars", data.get("actors", []))),
            "source_api": "lustpress",
            "source_id": str(data.get("id", data.get("video_id", ""))),
            "quality": "HD" if data.get("hd", data.get("high_quality", False)) else "SD",
            "created_at": data.get("date", data.get("published_at", "")),
        }

    async def get_categories(self) -> List[Dict[str, Any]]:
        """Get available categories."""
        try:
            # Try to fetch categories page
            response = await self.client.get(f"{self.base_url}/categories")

            if response.status_code == 200:
                html = response.text
                categories = self._parse_categories_html(html)
                if categories:
                    return categories
        except Exception as e:
            logger.debug(f"Failed to fetch categories: {e}")

        # Fallback: Return common categories
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

    def _parse_categories_html(self, html: str) -> List[Dict[str, Any]]:
        """Parse categories from HTML."""
        categories = []

        # Look for category links
        category_pattern = r'<a[^>]*href="[^"]*category[^"]*/([^"/]+)"[^>]*>([^<]+)</a>'
        matches = re.finditer(category_pattern, html, re.IGNORECASE)

        seen_slugs = set()
        for match in matches:
            slug = normalize_category(match.group(1))
            name = clean_title(match.group(2))

            if slug and slug not in seen_slugs:
                seen_slugs.add(slug)
                categories.append(
                    {
                        "name": name,
                        "slug": slug,
                        "description": f"{name} content",
                    }
                )

        return categories

    async def get_video_details(self, video_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific video."""
        try:
            # Try different URL patterns
            url_patterns = [
                f"{self.base_url}/video/{video_id}",
                f"{self.base_url}/videos/{video_id}",
                f"{self.base_url}/watch/{video_id}",
            ]

            for url in url_patterns:
                response = await self.client.get(url)

                if response.status_code == 200:
                    html = response.text

                    # Try to extract embedded JSON
                    script_patterns = [
                        r"<script[^>]*>window\.__VIDEO_DATA__\s*=\s*({.+?});</script>",
                        r"<script[^>]*>var\s+videoData\s*=\s*({.+?});</script>",
                        r'data-video="({.+?})"',
                    ]

                    for pattern in script_patterns:
                        match = re.search(pattern, html, re.DOTALL)
                        if match:
                            try:
                                data = json.loads(match.group(1))
                                return self._parse_video_data(data)
                            except json.JSONDecodeError:
                                continue

                    # Fallback: Parse HTML
                    return self._parse_video_page_html(html, video_id)

        except Exception as e:
            logger.error(f"Failed to get video details: {e}")

        return None

    def _parse_video_page_html(self, html: str, video_id: str) -> Dict[str, Any]:
        """Parse video details from video page HTML."""
        # Extract title
        title_match = re.search(r"<h1[^>]*>([^<]+)</h1>", html)
        title = clean_title(title_match.group(1)) if title_match else "Untitled"

        # Extract description
        desc_match = re.search(
            r'<div[^>]*class="[^"]*description[^"]*"[^>]*>(.*?)</div>', html, re.DOTALL
        )
        description = ""
        if desc_match:
            description = re.sub(r"<[^>]+>", "", desc_match.group(1)).strip()

        # Extract tags
        tags = []
        tag_matches = re.finditer(r'<a[^>]*href="[^"]*tag[^"]*"[^>]*>([^<]+)</a>', html)
        tags = [clean_title(m.group(1)) for m in tag_matches]

        # Extract performers
        performers = []
        performer_matches = re.finditer(r'<a[^>]*href="[^"]*performer[^"]*"[^>]*>([^<]+)</a>', html)
        performers = [clean_title(m.group(1)) for m in performer_matches]

        return {
            "title": title,
            "url": f"{self.base_url}/video/{video_id}",
            "thumbnail": "",
            "duration": 0,
            "views": 0,
            "rating": 0.0,
            "tags": tags,
            "performers": performers,
            "description": description,
            "source_api": "lustpress",
            "source_id": video_id,
            "quality": "HD",
        }

    async def get_trending(
        self,
        category: Optional[str] = None,
        period: str = "daily",  # daily, weekly, monthly, alltime
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get trending videos."""
        try:
            # Build trending URL
            if category:
                url = f"{self.base_url}/trending/{category}"
            else:
                url = f"{self.base_url}/trending"

            if period != "daily":
                url += f"?period={period}"

            response = await self.client.get(url)

            if response.status_code == 200:
                html = response.text
                return self._parse_html_videos(html, limit)
        except Exception as e:
            logger.error(f"Failed to get trending: {e}")

        return []

    async def get_category_videos(
        self,
        category: str,
        page: int = 1,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get videos from a specific category."""
        return await self.search("", category=category, page=page, limit=limit)

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
