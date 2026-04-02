"""Mobile anonymity and anti-tracking features."""

import random
import asyncio
from typing import Optional, List, Dict
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class MobileAnonymityManager:
    """Manages mobile anonymity and anti-tracking features."""

    # Mobile user agents (iOS, Android)
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
        # Android Samsung Internet
        "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/23.0 Chrome/115.0.0.0 Mobile Safari/537.36",
    ]

    # VPN/Proxy rotation (user can configure)
    PROXY_ROTATION_ENABLED = True
    PROXY_ROTATION_INTERVAL_MINUTES = 15  # Rotate proxy every 15 minutes

    # Location randomization
    LOCATION_ROTATION_ENABLED = True
    LOCATION_CHANGE_INTERVAL_MINUTES = 30  # Change apparent location every 30 minutes

    # Session rotation
    SESSION_ROTATION_ENABLED = True
    SESSION_MAX_DURATION_MINUTES = 60  # Max session duration before rotation

    def __init__(
        self,
        enable_mobile_mode: bool = True,
        enable_proxy_rotation: bool = True,
        enable_location_randomization: bool = True,
        enable_session_rotation: bool = True,
    ):
        """
        Initialize mobile anonymity manager.

        Args:
            enable_mobile_mode: Use mobile user agents
            enable_proxy_rotation: Rotate proxies periodically
            enable_location_randomization: Randomize apparent location
            enable_session_rotation: Rotate sessions periodically
        """
        self.enable_mobile_mode = enable_mobile_mode
        self.enable_proxy_rotation = enable_proxy_rotation
        self.enable_location_randomization = enable_location_randomization
        self.enable_session_rotation = enable_session_rotation

        self.current_user_agent_index = random.randint(0, len(self.MOBILE_USER_AGENTS) - 1)
        self.last_proxy_rotation = datetime.utcnow()
        self.last_location_change = datetime.utcnow()
        self.session_start = datetime.utcnow()
        self.current_proxy_index = 0
        self.proxies: List[str] = []

    def get_mobile_user_agent(self) -> str:
        """Get mobile user agent (rotated)."""
        if self.enable_mobile_mode:
            self.current_user_agent_index = (self.current_user_agent_index + 1) % len(
                self.MOBILE_USER_AGENTS
            )
            return self.MOBILE_USER_AGENTS[self.current_user_agent_index]
        return random.choice(self.MOBILE_USER_AGENTS)

    def should_rotate_proxy(self) -> bool:
        """Check if proxy should be rotated."""
        if not self.enable_proxy_rotation:
            return False

        elapsed = (datetime.utcnow() - self.last_proxy_rotation).total_seconds() / 60
        return elapsed >= self.PROXY_ROTATION_INTERVAL_MINUTES

    def should_change_location(self) -> bool:
        """Check if location should be changed."""
        if not self.enable_location_randomization:
            return False

        elapsed = (datetime.utcnow() - self.last_location_change).total_seconds() / 60
        return elapsed >= self.LOCATION_CHANGE_INTERVAL_MINUTES

    def should_rotate_session(self) -> bool:
        """Check if session should be rotated."""
        if not self.enable_session_rotation:
            return False

        elapsed = (datetime.utcnow() - self.session_start).total_seconds() / 60
        return elapsed >= self.SESSION_MAX_DURATION_MINUTES

    def get_random_location(self) -> Dict[str, str]:
        """Get randomized location headers."""
        # Random major cities (diverse locations)
        locations = [
            {"country": "US", "city": "New York", "timezone": "America/New_York"},
            {"country": "US", "city": "Los Angeles", "timezone": "America/Los_Angeles"},
            {"country": "US", "city": "Chicago", "timezone": "America/Chicago"},
            {"country": "GB", "city": "London", "timezone": "Europe/London"},
            {"country": "DE", "city": "Berlin", "timezone": "Europe/Berlin"},
            {"country": "FR", "city": "Paris", "timezone": "Europe/Paris"},
            {"country": "JP", "city": "Tokyo", "timezone": "Asia/Tokyo"},
            {"country": "AU", "city": "Sydney", "timezone": "Australia/Sydney"},
            {"country": "CA", "city": "Toronto", "timezone": "America/Toronto"},
            {"country": "NL", "city": "Amsterdam", "timezone": "Europe/Amsterdam"},
        ]

        return random.choice(locations)

    def get_location_headers(self) -> Dict[str, str]:
        """Get location obfuscation headers."""
        if not self.enable_location_randomization:
            return {}

        if self.should_change_location():
            self.last_location_change = datetime.utcnow()

        location = self.get_random_location()

        return {
            "X-Forwarded-For": self._generate_random_ip(),
            "X-Real-IP": self._generate_random_ip(),
            "CF-IPCountry": location["country"],
            "X-User-Country": location["country"],
            "X-User-City": location["city"],
            "X-User-Timezone": location["timezone"],
        }

    def _generate_random_ip(self) -> str:
        """Generate random IP address."""
        # Generate random private IP (won't be traced to real location)
        return f"{random.randint(10, 172)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}"

    def get_anti_tracking_headers(self) -> Dict[str, str]:
        """Get anti-tracking headers."""
        headers = {
            "DNT": "1",  # Do Not Track
            "Sec-GPC": "1",  # Global Privacy Control
            "X-Do-Not-Track": "1",
        }

        # Add location headers if enabled
        if self.enable_location_randomization:
            headers.update(self.get_location_headers())

        return headers

    def get_mobile_headers(self, base_url: Optional[str] = None) -> Dict[str, str]:
        """Get complete mobile anonymity headers."""
        headers = {
            "User-Agent": self.get_mobile_user_agent(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": random.choice(
                [
                    "en-US,en;q=0.9",
                    "en-GB,en;q=0.9",
                    "en-CA,en;q=0.9",
                    "en-AU,en;q=0.9",
                ]
            ),
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
            "X-Requested-With": "XMLHttpRequest",  # Common mobile header
        }

        # Add anti-tracking headers
        headers.update(self.get_anti_tracking_headers())

        # Add random referer (mobile sources)
        if base_url:
            mobile_referers = [
                "https://www.google.com/",
                "https://m.facebook.com/",
                "https://mobile.twitter.com/",
                "https://www.reddit.com/",
                None,  # Sometimes no referer
            ]
            referer = random.choice(mobile_referers)
            if referer:
                headers["Referer"] = referer

        return headers

    async def random_delay(self, min_seconds: float = 2.0, max_seconds: float = 8.0):
        """Add random delay to prevent timing analysis."""
        delay = random.uniform(min_seconds, max_seconds)
        await asyncio.sleep(delay)

    def rotate_session(self):
        """Rotate session (reset session start time)."""
        if self.should_rotate_session():
            self.session_start = datetime.utcnow()
            logger.info("Session rotated for anonymity")
            return True
        return False


# Global instance
_mobile_anonymity_manager: Optional[MobileAnonymityManager] = None


def get_mobile_anonymity_manager() -> MobileAnonymityManager:
    """Get global mobile anonymity manager."""
    global _mobile_anonymity_manager
    if _mobile_anonymity_manager is None:
        _mobile_anonymity_manager = MobileAnonymityManager()
    return _mobile_anonymity_manager
