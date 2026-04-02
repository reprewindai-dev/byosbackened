"""NSFW-API2 client for content aggregation."""

import httpx
from typing import List, Dict, Optional, Any
import logging
from urllib.parse import urlencode

logger = logging.getLogger(__name__)


class NSFWAPI2Client:
    """Client for NSFW-API2 service."""

    def __init__(self, base_url: str = "https://nsfw-api-p302.onrender.com"):
        """
        Initialize NSFW-API2 client.

        Args:
            base_url: Base URL of the API (default: official deployment)
        """
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json",
            },
        )

    async def search_hentai_images(
        self,
        query: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Search hentai images.

        Args:
            query: Search query
            limit: Maximum results to return
        """
        try:
            url = f"{self.base_url}/h/image/search"
            params = {"q": query}

            response = await self.client.get(url, params=params)

            if response.status_code == 200:
                data = response.json()

                # Handle different response formats
                if isinstance(data, list):
                    items = data
                elif isinstance(data, dict):
                    items = data.get("results", data.get("data", data.get("items", [])))
                else:
                    items = []

                return [self._parse_image_item(item) for item in items[:limit]]
        except Exception as e:
            logger.error(f"NSFW-API2 hentai image search error: {e}", exc_info=True)

        return []

    async def search_hentai_videos(
        self,
        query: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Search hentai videos.

        Args:
            query: Search query
            limit: Maximum results to return
        """
        try:
            url = f"{self.base_url}/h/video/search"
            params = {"q": query}

            response = await self.client.get(url, params=params)

            if response.status_code == 200:
                data = response.json()

                # Handle different response formats
                if isinstance(data, list):
                    items = data
                elif isinstance(data, dict):
                    items = data.get("results", data.get("data", data.get("items", [])))
                else:
                    items = []

                return [
                    self._parse_video_item(item, content_type="hentai") for item in items[:limit]
                ]
        except Exception as e:
            logger.error(f"NSFW-API2 hentai video search error: {e}", exc_info=True)

        return []

    async def search_real_videos(
        self,
        query: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Search real videos.

        Args:
            query: Search query
            limit: Maximum results to return
        """
        try:
            url = f"{self.base_url}/r/video/search"
            params = {"q": query}

            response = await self.client.get(url, params=params)

            if response.status_code == 200:
                data = response.json()

                # Handle different response formats
                if isinstance(data, list):
                    items = data
                elif isinstance(data, dict):
                    items = data.get("results", data.get("data", data.get("items", [])))
                else:
                    items = []

                return [self._parse_video_item(item, content_type="real") for item in items[:limit]]
        except Exception as e:
            logger.error(f"NSFW-API2 real video search error: {e}", exc_info=True)

        return []

    async def search_real_images_by_tag(
        self,
        tag: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Search real images by tag.

        Args:
            tag: Tag name (110 types available)
            limit: Maximum results to return
        """
        try:
            url = f"{self.base_url}/r/image/{tag}"

            response = await self.client.get(url)

            if response.status_code == 200:
                data = response.json()

                # Handle different response formats
                if isinstance(data, list):
                    items = data
                elif isinstance(data, dict):
                    items = data.get("results", data.get("data", data.get("items", [])))
                else:
                    items = []

                return [self._parse_image_item(item) for item in items[:limit]]
        except Exception as e:
            logger.error(f"NSFW-API2 tag search error: {e}", exc_info=True)

        return []

    def _parse_image_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Parse image item from API response."""
        # Handle various response formats
        return {
            "title": item.get("title", item.get("name", "")),
            "url": item.get("url", item.get("link", item.get("src", ""))),
            "thumbnail": item.get(
                "thumbnail", item.get("thumb", item.get("preview", item.get("url", "")))
            ),
            "duration": 0,  # Images don't have duration
            "views": item.get("views", item.get("view_count", 0)),
            "rating": item.get("rating", item.get("score", 0.0)),
            "tags": item.get("tags", item.get("categories", [])),
            "performers": item.get("performers", item.get("models", [])),
            "source_api": "nsfw-api2",
            "source_id": str(item.get("id", item.get("image_id", ""))),
            "content_type": "image",
            "quality": "HD" if item.get("hd", item.get("high_quality", False)) else "SD",
        }

    def _parse_video_item(self, item: Dict[str, Any], content_type: str = "real") -> Dict[str, Any]:
        """Parse video item from API response."""
        # Handle various response formats
        duration = item.get("duration", item.get("length", 0))
        if isinstance(duration, str):
            # Parse duration string like "10:30" to seconds
            try:
                parts = duration.split(":")
                if len(parts) == 2:
                    duration = int(parts[0]) * 60 + int(parts[1])
                elif len(parts) == 3:
                    duration = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                else:
                    duration = int(duration)
            except:
                duration = 0

        return {
            "title": item.get("title", item.get("name", "")),
            "url": item.get("url", item.get("link", item.get("src", ""))),
            "thumbnail": item.get(
                "thumbnail", item.get("thumb", item.get("preview", item.get("poster", "")))
            ),
            "duration": int(duration),
            "views": item.get("views", item.get("view_count", 0)),
            "rating": float(item.get("rating", item.get("score", 0.0))),
            "tags": item.get("tags", item.get("categories", [])),
            "performers": item.get("performers", item.get("models", item.get("actors", []))),
            "source_api": "nsfw-api2",
            "source_id": str(item.get("id", item.get("video_id", ""))),
            "content_type": content_type,
            "quality": "HD" if item.get("hd", item.get("high_quality", False)) else "SD",
        }

    async def search_all(
        self,
        query: str,
        include_hentai: bool = True,
        include_real: bool = True,
        limit_per_type: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Search across all content types.

        Args:
            query: Search query
            include_hentai: Include hentai content
            include_real: Include real content
            limit_per_type: Results per content type
        """
        results = []

        if include_hentai:
            hentai_videos = await self.search_hentai_videos(query, limit_per_type)
            results.extend(hentai_videos)

        if include_real:
            real_videos = await self.search_real_videos(query, limit_per_type)
            results.extend(real_videos)

        return results

    async def get_available_tags(self) -> List[str]:
        """Get list of available tags (from tags.txt)."""
        try:
            # Try to fetch tags.txt from the repo or API
            url = f"{self.base_url}/tags.txt"
            response = await self.client.get(url)

            if response.status_code == 200:
                tags = response.text.strip().split("\n")
                return [tag.strip() for tag in tags if tag.strip()]
        except Exception as e:
            logger.debug(f"Failed to fetch tags: {e}")

        # Fallback: return common tags
        return [
            "lesbian",
            "solo-female",
            "squirting",
            "masturbation",
            "kissing",
            "pmv",
            "long-session",
            "sloppy",
            "cam-girls",
            "gooning",
            "squirt",
            "orgasm",
            "hardcore",
            "anal",
            "oral",
            "threesome",
        ]

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
