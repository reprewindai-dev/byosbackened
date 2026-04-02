"""Disclaimer and terms endpoints."""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/disclaimer", tags=["disclaimer"])


class DisclaimerResponse(BaseModel):
    title: str
    content: str
    last_updated: str


@router.get("/", response_model=DisclaimerResponse)
async def get_disclaimer():
    """Get disclaimer and terms of service."""
    return DisclaimerResponse(
        title="Terms of Service & Content Disclaimer",
        content="""
ADULTS ONLY (18+): This website contains explicit adult content. You must be 18 years or older to access this site.

CONTENT ACCESS & SOURCES:
Our platform aggregates content from multiple publicly available sources through legitimate means:
- Public APIs: We use official webmaster APIs provided by content platforms
- Public Content: We aggregate publicly available content accessible on the internet
- Content Aggregation: We collect metadata (titles, thumbnails, descriptions) and links to publicly hosted videos
- No Hosting: We do not host or store video files ourselves - we provide links to content hosted elsewhere

HOW WE ACCESS CONTENT:
1. API Integration: We use official APIs provided by content platforms
2. Public Web Scraping: We access publicly available web pages using standard HTTP requests
3. Rate Limiting: We implement strict rate limiting (8 requests per minute) to respect server resources
4. Privacy Protection: We use rotating user agents and privacy headers
5. Content Indexing: We index publicly available metadata and provide search functionality

LEGAL & ETHICAL CONSIDERATIONS:
- All content we link to is publicly available on the internet
- We respect robots.txt and terms of service where applicable
- We do not bypass paywalls or access restricted content
- We aggregate only publicly accessible metadata and links
- We implement rate limiting to avoid server overload

USER RESPONSIBILITIES:
- You must be 18+ years old to use this service
- You are responsible for ensuring content access complies with your local laws
- You agree not to use this service for illegal purposes
- You understand that content is aggregated from external sources
- You acknowledge that we do not control or host the actual video content

CONTENT DISCLAIMER:
We do not own, host, or control the video content. All videos are hosted by third-party platforms. 
We provide links and metadata for discovery purposes only.
        """,
        last_updated="2026-02-04",
    )
