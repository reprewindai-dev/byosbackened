"""Search schemas."""

from pydantic import BaseModel
from typing import List, Optional, Dict, Any


class SearchResult(BaseModel):
    """Search result item."""

    title: str
    url: str
    snippet: str
    position: int
    metadata: Optional[Dict[str, Any]] = None


class SearchRequest(BaseModel):
    """Search request."""

    query: str
    num_results: int = 10


class SearchResponse(BaseModel):
    """Search response."""

    results: List[SearchResult]
    provider: str
    query: str
