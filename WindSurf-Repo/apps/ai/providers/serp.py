"""SERP API provider (search)."""

import httpx
from typing import List
from apps.ai.contracts import SearchProvider, SearchResult
from core.config import get_settings

settings = get_settings()


class SERPProvider(SearchProvider):
    """SERP API provider for search."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key if api_key is not None else settings.serpapi_key
        self.base_url = "https://serpapi.com/search.json"

    async def search(self, query: str, num_results: int = 10) -> List[SearchResult]:
        """Perform search using SERP API."""
        if not self.api_key:
            raise ValueError("SERPAPI_KEY not configured")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                self.base_url,
                params={
                    "engine": "google",
                    "q": query[:400],  # Limit query length
                    "api_key": self.api_key,
                    "num": num_results,
                },
            )
            response.raise_for_status()
            data = response.json()

            results = []
            organic_results = data.get("organic_results", [])
            for idx, item in enumerate(organic_results[:num_results], start=1):
                results.append(
                    SearchResult(
                        title=item.get("title", ""),
                        url=item.get("link", ""),
                        snippet=item.get("snippet", ""),
                        position=idx,
                        metadata={
                            "source": "serpapi",
                            "displayed_link": item.get("displayed_link"),
                        },
                    )
                )
            return results

    def get_name(self) -> str:
        """Get provider name."""
        return "serpapi"
