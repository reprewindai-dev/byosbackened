"""
Admin Research Dashboard API
Superuser-only endpoints for market research: search, trending, categories, source health.
Content is NEVER stored — metadata + embed codes only.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from apps.api.deps import get_current_user
from db.models.user import User
from db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/research", tags=["Admin Research"])

NICHE_TAGS = [
    "lesbian", "squirting", "masturbation", "gooning", "goonette",
    "hypno", "hypnosis", "brain rot", "brainrot", "pmv",
    "solo female", "female orgasm", "dildo", "vibrator",
]

SOURCES = ["pornhub", "xhamster", "lustpress", "nsfw-api2", "redtube"]


# ── Auth guard ────────────────────────────────────────────────────────────────

async def require_superuser(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superuser required")
    return current_user


# ── Embed helpers ─────────────────────────────────────────────────────────────

def build_embed_url(source: str, source_id: str, video_url: str) -> Optional[str]:
    """Build official embed iframe URL from source + ID."""
    if source == "pornhub" and source_id:
        return f"https://www.pornhub.com/embed/{source_id}"
    if source == "xhamster" and source_id:
        return f"https://xhamster.com/xembed.php?video={source_id}"
    if source == "redtube" and source_id:
        return f"https://embed.redtube.com/?id={source_id}&bgcolor=000000"
    return video_url


def enrich_with_embed(result: Dict[str, Any]) -> Dict[str, Any]:
    src = result.get("source_api", result.get("source", ""))
    sid = result.get("source_id", "")
    url = result.get("url", "")
    result["embed_url"] = build_embed_url(src, sid, url)
    result["source"] = src
    return result


# ── Schemas ───────────────────────────────────────────────────────────────────

class SearchRequest(BaseModel):
    query: str
    source: Optional[str] = "all"
    category: Optional[str] = None
    limit: int = 30
    ordering: Optional[str] = "mostviewed"


class SearchResponse(BaseModel):
    results: List[Dict[str, Any]]
    total: int
    query: str
    source: str


class TrendingResponse(BaseModel):
    tags: List[Dict[str, Any]]
    categories: List[Dict[str, Any]]


class SourceStatus(BaseModel):
    name: str
    online: bool
    latency_ms: Optional[float] = None


# ── Source status check ───────────────────────────────────────────────────────

async def check_source(name: str, url: str) -> SourceStatus:
    try:
        import time
        start = time.monotonic()
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(url)
        ms = (time.monotonic() - start) * 1000
        return SourceStatus(name=name, online=r.status_code < 500, latency_ms=round(ms, 1))
    except Exception:
        return SourceStatus(name=name, online=False)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/sources", response_model=List[SourceStatus], summary="Scraper health")
async def sources_status(_: User = Depends(require_superuser)):
    """Check which scrapers are reachable right now."""
    checks = [
        check_source("pornhub", "https://www.pornhub.com"),
        check_source("xhamster", "https://xhamster.com"),
        check_source("lustpress", "https://lustpress.com"),
        check_source("redtube", "https://www.redtube.com"),
        check_source("nsfw-api2", "https://nsfw-api-p302.onrender.com"),
    ]
    return await asyncio.gather(*checks)


@router.get("/trending", response_model=TrendingResponse, summary="Trending tags & categories")
async def trending(_: User = Depends(require_superuser)):
    """Return niche trending tags and top categories."""
    tag_data = [
        {"tag": t, "score": max(100 - i * 3, 10), "niche": True}
        for i, t in enumerate(NICHE_TAGS)
    ]
    categories = [
        {"name": "Lesbian", "slug": "lesbian"},
        {"name": "Squirting", "slug": "squirting"},
        {"name": "Masturbation", "slug": "masturbation"},
        {"name": "Gooning", "slug": "gooning"},
        {"name": "Hypno", "slug": "hypno"},
        {"name": "PMV", "slug": "pmv"},
        {"name": "Solo Female", "slug": "solo-female"},
        {"name": "Goonette", "slug": "goonette"},
    ]
    return TrendingResponse(tags=tag_data, categories=categories)


@router.get("/categories", summary="All categories from all sources")
async def categories(_: User = Depends(require_superuser)):
    """Aggregate categories from all scraper sources."""
    try:
        from core.content_apis import ContentAggregator
        agg = ContentAggregator()
        cats = await agg.get_all_categories()
        await agg.close()
        return {"categories": cats, "total": len(cats)}
    except Exception as exc:
        logger.warning(f"[categories] Scraper error: {exc}")
        return {"categories": [], "total": 0, "error": str(exc)}


@router.post("/search", response_model=SearchResponse, summary="Search content across sources")
async def search_content(req: SearchRequest, _: User = Depends(require_superuser)):
    """
    Search across all or a specific scraper source.
    Returns metadata + embed URL — nothing is stored on the server.
    """
    results: List[Dict[str, Any]] = []

    try:
        if req.source == "all":
            from core.content_apis import ContentAggregator
            agg = ContentAggregator()
            raw = await agg.search_all(req.query, req.category, limit_per_api=req.limit // 5 + 5)
            await agg.close()
            results = [enrich_with_embed(r) for r in raw[: req.limit]]

        elif req.source == "pornhub":
            from src.scraper.pornhub import PornHubScraper
            s = PornHubScraper()
            raw = await s.search(req.query, category=req.category, limit=req.limit, ordering=req.ordering)
            await s.close()
            results = [enrich_with_embed({**r, "source_api": "pornhub"}) for r in raw]

        elif req.source == "xhamster":
            from src.scraper.xhamster import XHamsterScraper
            s = XHamsterScraper()
            raw = await s.search(req.query, category=req.category, limit=req.limit, ordering=req.ordering)
            await s.close()
            results = [enrich_with_embed({**r, "source_api": "xhamster"}) for r in raw]

        elif req.source == "lustpress":
            from src.scraper.lustpress import LustPressScraper
            s = LustPressScraper()
            raw = await s.search(req.query, category=req.category, limit=req.limit)
            await s.close()
            results = [enrich_with_embed({**r, "source_api": "lustpress"}) for r in raw]

        elif req.source == "nsfw-api2":
            from src.scraper.nsfw_api2 import NSFWAPI2Client
            s = NSFWAPI2Client()
            raw = await s.search_all(req.query, limit_per_type=req.limit // 2)
            await s.close()
            results = [enrich_with_embed({**r, "source_api": "nsfw-api2"}) for r in raw[: req.limit]]

        elif req.source == "redtube":
            from core.content_apis import RedTubeAPIClient
            s = RedTubeAPIClient()
            raw = await s.search(req.query, req.category, req.limit)
            await s.close()
            results = [enrich_with_embed(r) for r in raw]

    except Exception as exc:
        logger.error(f"[search] source={req.source} query={req.query!r} error: {exc}")
        raise HTTPException(status_code=502, detail=f"Scraper error: {exc}")

    return SearchResponse(
        results=results,
        total=len(results),
        query=req.query,
        source=req.source or "all",
    )
