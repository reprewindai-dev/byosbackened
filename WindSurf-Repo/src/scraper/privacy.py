"""Privacy and anonymity features for scrapers."""

import random
import httpx
from typing import Optional, Dict, List
import logging
from datetime import datetime, timedelta
import asyncio

logger = logging.getLogger(__name__)


class PrivacyManager:
    """Manages privacy and anonymity features."""

    # Mobile user agents (iOS, Android) - PRIMARY for anonymity
    MOBILE_USER_AGENTS = [
        # iOS Safari
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (iPad; CPU OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
        # Android Chrome
        "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 12; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 13; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Mobile Safari/537.36",
        # Android Firefox
        "Mozilla/5.0 (Mobile; rv:121.0) Gecko/121.0 Firefox/121.0",
        "Mozilla/5.0 (Mobile; rv:120.0) Gecko/120.0 Firefox/120.0",
    ]

    # Desktop user agents (fallback)
    DESKTOP_USER_AGENTS = [
        # Windows Chrome
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        # macOS Chrome
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        # Windows Firefox
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        # Safari
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    ]

    # Use mobile by default for anonymity
    USER_AGENTS = MOBILE_USER_AGENTS

    # Common referers (rotate to avoid patterns)
    REFERERS = [
        "https://www.google.com/",
        "https://www.bing.com/",
        "https://duckduckgo.com/",
        "https://www.reddit.com/",
        "https://www.youtube.com/",
        None,  # Sometimes no referer
    ]

    # Accept-Language headers (vary by region)
    ACCEPT_LANGUAGES = [
        "en-US,en;q=0.9",
        "en-GB,en;q=0.9",
        "en-CA,en;q=0.9",
        "en-AU,en;q=0.9",
        "en-US,en;q=0.8,es;q=0.1",
    ]

    def __init__(
        self,
        use_proxy: bool = False,
        proxy_url: Optional[str] = None,
        rotate_user_agent: bool = True,
        random_referer: bool = True,
        mobile_mode: bool = True,  # Use mobile user agents by default
        location_randomization: bool = True,  # Randomize location headers
        session_rotation_minutes: int = 60,  # Rotate session every N minutes
    ):
        """
        Initialize privacy manager.

        Args:
            use_proxy: Enable proxy support
            proxy_url: Proxy URL (e.g., "http://proxy:port" or "socks5://proxy:port")
            rotate_user_agent: Rotate user agents
            random_referer: Use random referers
            mobile_mode: Use mobile user agents (harder to trace)
            location_randomization: Randomize location headers
            session_rotation_minutes: Rotate session every N minutes
        """
        self.use_proxy = use_proxy
        self.proxy_url = proxy_url
        self.rotate_user_agent = rotate_user_agent
        self.random_referer = random_referer
        self.mobile_mode = mobile_mode
        self.location_randomization = location_randomization
        self.session_rotation_minutes = session_rotation_minutes

        # Use mobile agents if mobile mode enabled
        if mobile_mode:
            self.USER_AGENTS = self.MOBILE_USER_AGENTS
        else:
            self.USER_AGENTS = self.DESKTOP_USER_AGENTS

        self.current_user_agent_index = random.randint(0, len(self.USER_AGENTS) - 1)
        self.session_start = datetime.utcnow()
        self.last_location_change = datetime.utcnow()

    def get_random_location(self) -> Dict[str, str]:
        """Get randomized location headers."""
        locations = [
            {"country": "US", "city": "New York"},
            {"country": "US", "city": "Los Angeles"},
            {"country": "US", "city": "Chicago"},
            {"country": "GB", "city": "London"},
            {"country": "DE", "city": "Berlin"},
            {"country": "FR", "city": "Paris"},
            {"country": "JP", "city": "Tokyo"},
            {"country": "AU", "city": "Sydney"},
            {"country": "CA", "city": "Toronto"},
            {"country": "NL", "city": "Amsterdam"},
        ]
        return random.choice(locations)

    def should_change_location(self) -> bool:
        """Check if location should be changed (every 30 minutes)."""
        elapsed = (datetime.utcnow() - self.last_location_change).total_seconds() / 60
        return elapsed >= 30  # Change location every 30 minutes

    def get_headers(self, base_url: Optional[str] = None) -> Dict[str, str]:
        """Get privacy-focused headers with mobile anonymity."""
        headers = {
            "User-Agent": self.get_user_agent(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": random.choice(self.ACCEPT_LANGUAGES),
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
            # Anti-tracking headers
            "DNT": "1",  # Do Not Track
            "Sec-GPC": "1",  # Global Privacy Control
        }

        # Add mobile-specific headers if in mobile mode
        if self.mobile_mode:
            headers["X-Requested-With"] = "XMLHttpRequest"

        # Add location randomization (change location periodically)
        if self.location_randomization:
            if self.should_change_location():
                self.last_location_change = datetime.utcnow()

            location = self.get_random_location()
            # Obfuscate IP with random values
            headers["X-Forwarded-For"] = (
                f"{random.randint(10, 172)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}"
            )
            headers["X-Real-IP"] = headers["X-Forwarded-For"]
            headers["CF-IPCountry"] = location["country"]
            headers["X-User-Country"] = location["country"]
            headers["X-User-City"] = location["city"]

        # Add random referer
        if self.random_referer and base_url:
            mobile_referers = (
                [
                    "https://www.google.com/",
                    "https://m.facebook.com/",
                    "https://mobile.twitter.com/",
                    "https://www.reddit.com/",
                    None,  # Sometimes no referer
                ]
                if self.mobile_mode
                else self.REFERERS
            )
            referer = random.choice(mobile_referers)
            if referer:
                headers["Referer"] = referer

        return headers

    def should_rotate_session(self) -> bool:
        """Check if session should be rotated."""
        elapsed = (datetime.utcnow() - self.session_start).total_seconds() / 60
        return elapsed >= self.session_rotation_minutes

    def rotate_session(self):
        """Rotate session (reset start time)."""
        if self.should_rotate_session():
            self.session_start = datetime.utcnow()
            # Also rotate user agent
            self.current_user_agent_index = random.randint(0, len(self.USER_AGENTS) - 1)
            logger.info("Session rotated for anonymity")
            return True
        return False

    async def random_delay(self, min_seconds: float = 2.0, max_seconds: float = 8.0):
        """Add random delay to prevent timing analysis."""
        delay = random.uniform(min_seconds, max_seconds)
        await asyncio.sleep(delay)

    def get_user_agent(self) -> str:
        """Get user agent (rotated if enabled)."""
        if self.rotate_user_agent:
            # Rotate to next agent
            self.current_user_agent_index = (self.current_user_agent_index + 1) % len(
                self.USER_AGENTS
            )
        return self.USER_AGENTS[self.current_user_agent_index]

    def get_proxy_config(self) -> Optional[Dict[str, str]]:
        """Get proxy configuration."""
        if self.use_proxy and self.proxy_url:
            return {
                "http://": self.proxy_url,
                "https://": self.proxy_url,
            }
        return None

    def get_client_config(self) -> Dict:
        """Get HTTP client configuration with privacy features."""
        config = {
            "timeout": 30.0,
            "follow_redirects": True,
            "headers": self.get_headers(),
        }

        # Add proxy if configured
        proxy_config = self.get_proxy_config()
        if proxy_config:
            config["proxies"] = proxy_config

        return config


class AnonymousClient:
    """Anonymous HTTP client wrapper."""

    def __init__(
        self,
        privacy_manager: Optional[PrivacyManager] = None,
        proxy_url: Optional[str] = None,
    ):
        """
        Initialize anonymous client.

        Args:
            privacy_manager: Privacy manager instance
            proxy_url: Optional proxy URL
        """
        if privacy_manager is None:
            use_proxy = proxy_url is not None
            privacy_manager = PrivacyManager(
                use_proxy=use_proxy,
                proxy_url=proxy_url,
                rotate_user_agent=True,
                random_referer=True,
            )

        self.privacy_manager = privacy_manager
        self.client = httpx.AsyncClient(**privacy_manager.get_client_config())

    async def get(self, url: str, **kwargs) -> httpx.Response:
        """Make GET request with privacy headers."""
        # Update headers for each request
        headers = self.privacy_manager.get_headers(url)
        if "headers" in kwargs:
            headers.update(kwargs["headers"])
        kwargs["headers"] = headers

        return await self.client.get(url, **kwargs)

    async def post(self, url: str, **kwargs) -> httpx.Response:
        """Make POST request with privacy headers."""
        headers = self.privacy_manager.get_headers(url)
        if "headers" in kwargs:
            headers.update(kwargs["headers"])
        kwargs["headers"] = headers

        return await self.client.post(url, **kwargs)

    async def request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Make request with privacy headers."""
        headers = self.privacy_manager.get_headers(url)
        if "headers" in kwargs:
            headers.update(kwargs["headers"])
        kwargs["headers"] = headers

        return await self.client.request(method, url, **kwargs)

    async def close(self):
        """Close client."""
        await self.client.aclose()


def get_anonymous_client(proxy_url: Optional[str] = None) -> AnonymousClient:
    """
    Get anonymous HTTP client.

    Args:
        proxy_url: Optional proxy URL (e.g., "http://proxy:port" or "socks5://proxy:port")

    Returns:
        AnonymousClient instance
    """
    return AnonymousClient(proxy_url=proxy_url)
