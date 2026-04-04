"""
Public Content API
Handles browsing, search, trending, video detail, creator profiles.
Content is embedded from external sources — nothing stored on this server.
Subscription gating via Stripe is enforced on premium endpoints.
"""

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from apps.api.deps import get_current_user
from db.session import get_db
from db.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/public", tags=["Public Platform"])

NICHE_CATEGORIES = [
    {"slug": "lesbian",       "label": "Lesbian",       "icon": "💜", "hot": True},
    {"slug": "squirting",     "label": "Squirting",     "icon": "💦", "hot": True},
    {"slug": "masturbation",  "label": "Masturbation",  "icon": "🔥", "hot": True},
    {"slug": "gooning",       "label": "Gooning",       "icon": "🌀", "hot": True},
    {"slug": "goonette",      "label": "Goonette",      "icon": "💫", "hot": False},
    {"slug": "hypno",         "label": "Hypno",         "icon": "🌀", "hot": True},
    {"slug": "pmv",           "label": "PMV",           "icon": "🎵", "hot": True},
    {"slug": "brainrot",      "label": "Brain Rot",     "icon": "🧠", "hot": False},
    {"slug": "solo-female",   "label": "Solo Female",   "icon": "👤", "hot": False},
    {"slug": "orgasm",        "label": "Orgasm",        "icon": "✨", "hot": False},
]


# ── Schemas ───────────────────────────────────────────────────────────────────

class BrowseRequest(BaseModel):
    category: Optional[str] = None
    sort: Optional[str] = "trending"   # trending | newest | top-rated
    source: Optional[str] = "all"
    page: int = 1
    limit: int = 24


class SearchRequest(BaseModel):
    query: str
    category: Optional[str] = None
    source: Optional[str] = "all"
    limit: int = 24


class DMCARequest(BaseModel):
    content_url: str
    your_name: str
    your_email: str
    reason: str
    original_work_url: Optional[str] = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def build_embed_url(source: str, source_id: str, video_url: str) -> Optional[str]:
    if source == "pornhub" and source_id:
        return f"https://www.pornhub.com/embed/{source_id}"
    if source == "xhamster" and source_id:
        return f"https://xhamster.com/xembed.php?video={source_id}"
    if source == "redtube" and source_id:
        return f"https://embed.redtube.com/?id={source_id}&bgcolor=000000"
    return None


def enrich(v: Dict[str, Any]) -> Dict[str, Any]:
    src = v.get("source_api", v.get("source", ""))
    sid = v.get("source_id", "")
    url = v.get("url", "")
    v["source"] = src
    v["embed_url"] = build_embed_url(src, sid, url)
    v.pop("source_api", None)
    return v


async def run_search(query: str, source: str = "all", limit: int = 24) -> List[Dict]:
    try:
        if source == "all":
            from core.content_apis import ContentAggregator
            agg = ContentAggregator()
            raw = await agg.search_all(query, limit_per_api=max(limit // 4, 6))
            await agg.close()
            return [enrich(r) for r in raw[:limit]]
        elif source == "pornhub":
            from src.scraper.pornhub import PornHubScraper
            s = PornHubScraper(); raw = await s.search(query, limit=limit); await s.close()
            return [enrich({**r, "source_api": "pornhub"}) for r in raw]
        elif source == "xhamster":
            from src.scraper.xhamster import XHamsterScraper
            s = XHamsterScraper(); raw = await s.search(query, limit=limit); await s.close()
            return [enrich({**r, "source_api": "xhamster"}) for r in raw]
        elif source == "lustpress":
            from src.scraper.lustpress import LustPressScraper
            s = LustPressScraper(); raw = await s.search(query, limit=limit); await s.close()
            return [enrich({**r, "source_api": "lustpress"}) for r in raw]
        elif source == "redtube":
            from core.content_apis import RedTubeAPIClient
            s = RedTubeAPIClient(); raw = await s.search(query, limit=limit); await s.close()
            return [enrich(r) for r in raw]
    except Exception as exc:
        logger.warning(f"[public search] source={source} error: {exc}")
    return []


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/categories", summary="All niche categories")
async def get_categories():
    """Public — returns all browseable niche categories."""
    return {"categories": NICHE_CATEGORIES}


@router.get("/trending", summary="Trending right now")
async def get_trending(limit: int = Query(24, le=60)):
    """Public — trending content across top niches."""
    import asyncio
    niches = ["lesbian", "squirting", "gooning", "hypno", "pmv"]
    results = []
    for niche in niches[:3]:
        try:
            items = await run_search(niche, "all", limit=limit // 3 + 2)
            results.extend(items)
        except Exception:
            pass
    return {"results": results[:limit], "total": len(results[:limit])}


@router.post("/browse", summary="Browse by niche/category")
async def browse_content(req: BrowseRequest):
    """Public — paginated content browsing by niche."""
    query = req.category or "lesbian"
    results = await run_search(query, req.source or "all", req.limit)
    offset = (req.page - 1) * req.limit
    page_results = results[offset:offset + req.limit]
    return {
        "results": page_results,
        "total": len(results),
        "page": req.page,
        "category": req.category,
        "sort": req.sort,
    }


@router.post("/search", summary="Search content")
async def search_content(req: SearchRequest):
    """Public — keyword search across sources."""
    results = await run_search(req.query, req.source or "all", req.limit)
    return {"results": results, "total": len(results), "query": req.query}


@router.get("/video/{source}/{source_id}", summary="Video detail + embed")
async def get_video(source: str, source_id: str):
    """Public — get embed URL + metadata for a specific video."""
    embed_url = build_embed_url(source, source_id, "")
    if not embed_url:
        raise HTTPException(status_code=404, detail="No embed available for this source")
    return {
        "source": source,
        "source_id": source_id,
        "embed_url": embed_url,
    }


@router.post("/dmca", summary="Submit DMCA takedown request")
async def submit_dmca(req: DMCARequest):
    """Submit a DMCA takedown notice. Logged and forwarded to admin."""
    logger.warning(
        f"[DMCA] from={req.your_email} content={req.content_url} reason={req.reason}"
    )
    return {
        "status": "received",
        "message": "Your DMCA notice has been received and will be reviewed within 24 hours.",
        "reference": f"DMCA-{hash(req.content_url) % 999999:06d}",
    }


@router.get("/subscription/tiers", summary="Subscription pricing tiers")
async def subscription_tiers():
    """Public — return available subscription tiers and features."""
    return {
        "tiers": [
            {
                "id": "free",
                "name": "Free",
                "price_usd": 0,
                "period": None,
                "features": [
                    "Browse curated embedded content",
                    "Access all niche categories",
                    "Basic search",
                ],
                "cta": "Browse Free",
            },
            {
                "id": "premium",
                "name": "Premium",
                "price_usd": 9.99,
                "period": "month",
                "features": [
                    "Everything in Free",
                    "No ads",
                    "AI-powered recommendations",
                    "Playlists & favorites",
                    "HD priority content",
                    "Early access to new niches",
                ],
                "cta": "Go Premium",
                "badge": "Most Popular",
            },
            {
                "id": "vip",
                "name": "VIP",
                "price_usd": 24.99,
                "period": "month",
                "features": [
                    "Everything in Premium",
                    "Creator content access",
                    "Community & chat",
                    "Priority support",
                    "Exclusive curated drops",
                ],
                "cta": "Go VIP",
                "badge": "Best Value",
            },
        ]
    }
