"""Base scraper interface."""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any


class BaseScraper(ABC):
    """Base class for all scrapers."""

    @abstractmethod
    async def search(
        self,
        query: str,
        category: Optional[str] = None,
        page: int = 1,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Search for content."""
        pass

    @abstractmethod
    async def get_categories(self) -> List[Dict[str, Any]]:
        """Get available categories."""
        pass

    @abstractmethod
    async def close(self):
        """Close resources."""
        pass
