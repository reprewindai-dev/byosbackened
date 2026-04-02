"""Rate limiting and throttling for scrapers."""

import asyncio
import time
from typing import Dict, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter to prevent aggressive requests."""

    def __init__(
        self,
        requests_per_minute: int = 10,
        requests_per_hour: int = 200,
        min_delay_seconds: float = 2.0,
        max_delay_seconds: float = 5.0,
    ):
        """
        Initialize rate limiter.

        Args:
            requests_per_minute: Max requests per minute
            requests_per_hour: Max requests per hour
            min_delay_seconds: Minimum delay between requests
            max_delay_seconds: Maximum delay between requests
        """
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.min_delay = min_delay_seconds
        self.max_delay = max_delay_seconds

        self.request_times: list[datetime] = []
        self.last_request_time: Optional[datetime] = None
        self.lock = asyncio.Lock()

    async def wait_if_needed(self):
        """Wait if rate limit would be exceeded."""
        async with self.lock:
            now = datetime.utcnow()

            # Clean old requests (older than 1 hour)
            self.request_times = [rt for rt in self.request_times if now - rt < timedelta(hours=1)]

            # Check hourly limit
            if len(self.request_times) >= self.requests_per_hour:
                oldest_request = min(self.request_times)
                wait_until = oldest_request + timedelta(hours=1)
                wait_seconds = (wait_until - now).total_seconds()
                if wait_seconds > 0:
                    logger.info(f"Rate limit: Waiting {wait_seconds:.1f}s for hourly limit")
                    await asyncio.sleep(wait_seconds)
                    self.request_times.clear()

            # Check per-minute limit
            recent_requests = [rt for rt in self.request_times if now - rt < timedelta(minutes=1)]

            if len(recent_requests) >= self.requests_per_minute:
                oldest_recent = min(recent_requests)
                wait_until = oldest_recent + timedelta(minutes=1)
                wait_seconds = (wait_until - now).total_seconds()
                if wait_seconds > 0:
                    logger.info(f"Rate limit: Waiting {wait_seconds:.1f}s for per-minute limit")
                    await asyncio.sleep(wait_seconds)

            # Add random delay between requests
            if self.last_request_time:
                time_since_last = (now - self.last_request_time).total_seconds()
                if time_since_last < self.min_delay:
                    delay = self.min_delay - time_since_last
                    # Add some randomness
                    import random

                    delay += random.uniform(0, self.max_delay - self.min_delay)
                    logger.debug(f"Rate limit: Adding {delay:.2f}s delay")
                    await asyncio.sleep(delay)

            self.last_request_time = datetime.utcnow()
            self.request_times.append(self.last_request_time)


class ScraperConfig:
    """Configuration for respectful scraping."""

    # Conservative defaults to avoid getting shut down
    REQUESTS_PER_MINUTE = 8  # Very conservative
    REQUESTS_PER_HOUR = 150  # Conservative hourly limit
    MIN_DELAY_SECONDS = 3.0  # Minimum 3 seconds between requests
    MAX_DELAY_SECONDS = 8.0  # Up to 8 seconds delay

    # Retry configuration
    MAX_RETRIES = 2  # Only retry twice
    RETRY_DELAY_BASE = 5.0  # Base delay for retries
    RETRY_EXPONENTIAL_BACKOFF = True

    # Timeout configuration
    REQUEST_TIMEOUT = 30.0  # 30 second timeout

    # User agent rotation
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]

    @classmethod
    def get_rate_limiter(cls) -> RateLimiter:
        """Get configured rate limiter."""
        return RateLimiter(
            requests_per_minute=cls.REQUESTS_PER_MINUTE,
            requests_per_hour=cls.REQUESTS_PER_HOUR,
            min_delay_seconds=cls.MIN_DELAY_SECONDS,
            max_delay_seconds=cls.MAX_DELAY_SECONDS,
        )

    @classmethod
    def get_user_agent(cls) -> str:
        """Get random user agent."""
        import random

        return random.choice(cls.USER_AGENTS)


async def safe_request(
    client: any, method: str, url: str, rate_limiter: RateLimiter, max_retries: int = 2, **kwargs
):
    """
    Make a safe HTTP request with rate limiting and retries.

    Args:
        client: HTTP client (httpx.AsyncClient)
        method: HTTP method
        url: Request URL
        rate_limiter: Rate limiter instance
        max_retries: Maximum retry attempts
        **kwargs: Additional request arguments
    """
    # Wait for rate limit
    await rate_limiter.wait_if_needed()

    last_error = None
    for attempt in range(max_retries + 1):
        try:
            response = await client.request(method, url, **kwargs)

            # If rate limited (429), wait longer
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                logger.warning(f"Rate limited (429). Waiting {retry_after}s")
                await asyncio.sleep(retry_after)
                continue

            # If server error (5xx), retry with backoff
            if response.status_code >= 500 and attempt < max_retries:
                delay = ScraperConfig.RETRY_DELAY_BASE * (2**attempt)
                logger.warning(f"Server error {response.status_code}. Retrying in {delay}s")
                await asyncio.sleep(delay)
                continue

            return response

        except Exception as e:
            last_error = e
            if attempt < max_retries:
                delay = ScraperConfig.RETRY_DELAY_BASE * (2**attempt)
                logger.warning(f"Request failed: {e}. Retrying in {delay}s")
                await asyncio.sleep(delay)
            else:
                logger.error(f"Request failed after {max_retries} retries: {e}")

    raise last_error
