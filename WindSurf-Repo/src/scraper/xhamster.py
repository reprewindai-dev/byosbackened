"""XHamster scraper for content aggregation."""

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


class XHamsterScraper:
    """Advanced XHamster scraper with multiple methods."""

    def __init__(self):
        self.base_url = "https://xhamster.com"
        self.api_url = "https://xhamster.com/api/videos/search"
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
        ordering: str = "mostviewed",  # mostviewed, newest, rating, duration
    ) -> List[Dict[str, Any]]:
        """
        Search XHamster videos.

        Args:
            query: Search query
            category: Category filter
            page: Page number
            limit: Maximum results to return
            min_duration: Minimum duration in seconds
            max_duration: Maximum duration in seconds
            ordering: Sort order (mostviewed, newest, rating, duration)
        """
        try:
            # Method 1: Try official API first
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
            logger.error(f"XHamster search error: {e}", exc_info=True)
            return []

    async def _search_api(
        self,
        query: str,
        category: Optional[str],
        page: int,
        limit: int,
        ordering: str,
    ) -> List[Dict[str, Any]]:
        """Search using XHamster API."""
        try:
            params = {
                "query": query,
                "page": page,
            }

            if category:
                params["category"] = category

            # Map ordering
            sort_map = {
                "mostviewed": "mostviewed",
                "newest": "newest",
                "rating": "rating",
                "duration": "duration",
            }
            if ordering in sort_map:
                params["sort"] = sort_map[ordering]

            response = await self.client.get(self.api_url, params=params)

            if response.status_code == 200:
                data = response.json()

                # Handle different response formats
                if isinstance(data, dict):
                    videos = data.get("videos", data.get("items", data.get("data", [])))
                elif isinstance(data, list):
                    videos = data
                else:
                    videos = []

                return [self._parse_api_video(v) for v in videos[:limit]]
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
            if query:
                search_path = f"/search/{quote(query)}"
                if page > 1:
                    search_path += f"/{page}"
            elif category:
                search_path = f"/categories/{category}"
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
                return self._parse_html_videos(html, limit)
        except Exception as e:
            logger.warning(f"Scrape search failed: {e}")

        return []

    def _parse_api_video(self, video_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse video data from API response."""
        return {
            "title": clean_title(video_data.get("title", video_data.get("name", ""))),
            "url": self._build_video_url(video_data.get("url", video_data.get("link", ""))),
            "thumbnail": self._build_image_url(
                video_data.get("thumb", video_data.get("thumbnail", video_data.get("poster", "")))
            ),
            "duration": parse_duration(
                str(video_data.get("duration", video_data.get("length", 0)))
            ),
            "views": int(video_data.get("views", video_data.get("view_count", 0))),
            "rating": float(video_data.get("rating", video_data.get("score", 0))),
            "tags": [
                tag.get("tag_name", tag) if isinstance(tag, dict) else tag
                for tag in video_data.get("tags", [])
            ],
            "performers": [
                p.get("performer_name", p) if isinstance(p, dict) else p
                for p in video_data.get("performers", video_data.get("pornstars", []))
            ],
            "source_api": "xhamster",
            "source_id": str(video_data.get("id", video_data.get("video_id", ""))),
            "quality": (
                "HD" if video_data.get("hd", video_data.get("high_quality", False)) else "SD"
            ),
            "created_at": video_data.get("date", video_data.get("published_at", "")),
        }

    def _parse_html_videos(self, html: str, limit: int) -> List[Dict[str, Any]]:
        """Parse videos from HTML page."""
        videos = []

        # Extract video data from embedded JSON
        script_patterns = [
            r"<script[^>]*>window\.__INITIAL_STATE__\s*=\s*({.+?});</script>",
            r"<script[^>]*>window\.__DATA__\s*=\s*({.+?});</script>",
            r"var\s+videos\s*=\s*(\[.+?\]);",
            r'<script[^>]*id="__NEXT_DATA__"[^>]*>({.+?})</script>',
        ]

        for pattern in script_patterns:
            match = re.search(pattern, html, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(1))
                    # Navigate through the data structure
                    video_list = self._extract_videos_from_json(data)
                    if video_list:
                        videos.extend([self._parse_api_video(v) for v in video_list[:limit]])
                        break
                except (json.JSONDecodeError, KeyError) as e:
                    logger.debug(f"Failed to parse embedded JSON: {e}")
                    continue

        # Fallback: Extract from HTML structure
        if not videos:
            videos = self._parse_html_structure(html, limit)

        return videos

    def _extract_videos_from_json(self, data: Any) -> List[Dict[str, Any]]:
        """Extract video list from JSON data structure."""
        videos = []

        # Try common paths
        paths = [
            ["videos"],
            ["items"],
            ["data", "videos"],
            ["data", "items"],
            ["props", "pageProps", "videos"],
            ["props", "pageProps", "data", "videos"],
        ]

        for path in paths:
            current = data
            try:
                for key in path:
                    if isinstance(current, dict):
                        current = current.get(key)
                    elif isinstance(current, list):
                        return current
                    else:
                        break
                if isinstance(current, list):
                    return current
            except (KeyError, TypeError):
                continue

        return videos

    def _parse_html_structure(self, html: str, limit: int) -> List[Dict[str, Any]]:
        """Parse videos from HTML structure."""
        videos = []

        # Pattern to match video containers
        container_patterns = [
            r'<div[^>]*class="[^"]*thumb-list__item[^"]*"[^>]*>(.*?)</div>',
            r'<article[^>]*class="[^"]*thumb-list__item[^"]*"[^>]*>(.*?)</article>',
            r'<a[^>]*href="(/videos/[^"]+)"[^>]*>',
        ]

        for pattern in container_patterns:
            matches = re.finditer(pattern, html, re.DOTALL)
            for match in matches[:limit]:
                if len(match.groups()) > 0:
                    video_html = match.group(1) if len(match.groups()) > 0 else ""
                    if video_html:
                        video = self._parse_video_block(video_html)
                    else:
                        # Direct URL match
                        url = match.group(1)
                        video = self._parse_video_from_url(url)

                    if video:
                        videos.append(video)

            if videos:
                break

        return videos

    def _parse_video_block(self, html: str) -> Optional[Dict[str, Any]]:
        """Parse a single video block from HTML."""
        try:
            # Extract URL
            url_match = re.search(r'<a[^>]*href="([^"]+)"', html)
            if not url_match:
                return None

            url = urljoin(self.base_url, url_match.group(1))

            # Extract title
            title_match = re.search(
                r'<a[^>]*>.*?<span[^>]*class="[^"]*video-thumb__image-title[^"]*"[^>]*>([^<]+)</span>',
                html,
                re.DOTALL,
            )
            if not title_match:
                title_match = re.search(r'<a[^>]*title="([^"]+)"', html)

            title = clean_title(title_match.group(1)) if title_match else "Untitled"

            # Extract thumbnail
            thumb_match = re.search(r'<img[^>]*src="([^"]+)"', html)
            thumbnail = ""
            if thumb_match:
                thumbnail = urljoin(self.base_url, thumb_match.group(1))

            # Extract duration
            duration_match = re.search(
                r'<span[^>]*class="[^"]*thumb-image-container__duration[^"]*"[^>]*>([^<]+)</span>',
                html,
            )
            duration = 0
            if duration_match:
                duration = parse_duration(duration_match.group(1))

            # Extract views
            views_match = re.search(
                r'<span[^>]*class="[^"]*thumb-image-container__views[^"]*"[^>]*>([^<]+)</span>',
                html,
            )
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
                "source_api": "xhamster",
                "source_id": video_id,
                "quality": "HD",
            }
        except Exception as e:
            logger.debug(f"Failed to parse video block: {e}")
            return None

    def _parse_video_from_url(self, url: str) -> Optional[Dict[str, Any]]:
        """Parse minimal video info from URL."""
        video_id = extract_video_id(url) or ""
        return {
            "title": "Untitled",
            "url": urljoin(self.base_url, url),
            "thumbnail": "",
            "duration": 0,
            "views": 0,
            "rating": 0.0,
            "tags": [],
            "performers": [],
            "source_api": "xhamster",
            "source_id": video_id,
            "quality": "SD",
        }

    def _build_video_url(self, url: str) -> str:
        """Build full video URL."""
        if not url:
            return ""
        if url.startswith("http"):
            return url
        if url.startswith("/"):
            return f"{self.base_url}{url}"
        return f"{self.base_url}/{url}"

    def _build_image_url(self, url: str) -> str:
        """Build full image URL."""
        if not url:
            return ""
        if url.startswith("http"):
            return url
        if url.startswith("//"):
            return f"https:{url}"
        if url.startswith("/"):
            return f"{self.base_url}{url}"
        return f"{self.base_url}/{url}"

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
        category_pattern = r'<a[^>]*href="[^"]*categories[^"]*/([^"/]+)"[^>]*>([^<]+)</a>'
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
            url = f"{self.base_url}/videos/{video_id}"

            response = await self.client.get(url)

            if response.status_code == 200:
                html = response.text

                # Try to extract embedded JSON
                script_patterns = [
                    r"<script[^>]*>window\.__VIDEO_DATA__\s*=\s*({.+?});</script>",
                    r"<script[^>]*>var\s+videoData\s*=\s*({.+?});</script>",
                    r'<script[^>]*id="__NEXT_DATA__"[^>]*>({.+?})</script>',
                ]

                for pattern in script_patterns:
                    match = re.search(pattern, html, re.DOTALL)
                    if match:
                        try:
                            data = json.loads(match.group(1))
                            video_data = self._extract_video_from_json(data)
                            if video_data:
                                return self._parse_api_video(video_data)
                        except json.JSONDecodeError:
                            continue

                # Fallback: Parse HTML
                return self._parse_video_page_html(html, video_id)

        except Exception as e:
            logger.error(f"Failed to get video details: {e}")

        return None

    def _extract_video_from_json(self, data: Any) -> Optional[Dict[str, Any]]:
        """Extract video data from JSON."""
        # Try common paths
        paths = [
            ["video"],
            ["data", "video"],
            ["props", "pageProps", "video"],
            ["props", "pageProps", "data", "video"],
        ]

        for path in paths:
            current = data
            try:
                for key in path:
                    if isinstance(current, dict):
                        current = current.get(key)
                    else:
                        break
                if isinstance(current, dict):
                    return current
            except (KeyError, TypeError):
                continue

        return None

    def _parse_video_page_html(self, html: str, video_id: str) -> Dict[str, Any]:
        """Parse video details from video page HTML."""
        # Extract title
        title_match = re.search(r"<h1[^>]*>([^<]+)</h1>", html)
        title = clean_title(title_match.group(1)) if title_match else "Untitled"

        # Extract description
        desc_match = re.search(
            r'<div[^>]*class="[^"]*video-description[^"]*"[^>]*>(.*?)</div>', html, re.DOTALL
        )
        description = ""
        if desc_match:
            description = re.sub(r"<[^>]+>", "", desc_match.group(1)).strip()

        # Extract tags
        tags = []
        tag_matches = re.finditer(r'<a[^>]*href="[^"]*tags[^"]*"[^>]*>([^<]+)</a>', html)
        tags = [clean_title(m.group(1)) for m in tag_matches]

        # Extract performers
        performers = []
        performer_matches = re.finditer(r'<a[^>]*href="[^"]*pornstars[^"]*"[^>]*>([^<]+)</a>', html)
        performers = [clean_title(m.group(1)) for m in performer_matches]

        return {
            "title": title,
            "url": f"{self.base_url}/videos/{video_id}",
            "thumbnail": "",
            "duration": 0,
            "views": 0,
            "rating": 0.0,
            "tags": tags,
            "performers": performers,
            "description": description,
            "source_api": "xhamster",
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
        ordering: str = "mostviewed",
    ) -> List[Dict[str, Any]]:
        """Get videos from a specific category."""
        return await self.search("", category=category, page=page, limit=limit, ordering=ordering)

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
