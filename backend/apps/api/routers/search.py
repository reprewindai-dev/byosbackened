"""Search router."""
from fastapi import APIRouter, Depends
from apps.api.deps import get_current_workspace_id
from apps.api.schemas.search import SearchRequest, SearchResponse
from apps.ai.providers import SERPProvider

router = APIRouter(prefix="/search", tags=["search"])


@router.post("", response_model=SearchResponse)
async def search(
    request: SearchRequest,
    workspace_id: str = Depends(get_current_workspace_id),
):
    """Perform search using SERP API."""
    provider = SERPProvider()
    results = await provider.search(request.query, request.num_results)

    return SearchResponse(
        results=[
            {
                "title": r.title,
                "url": r.url,
                "snippet": r.snippet,
                "position": r.position,
                "metadata": r.metadata,
            }
            for r in results
        ],
        provider=provider.get_name(),
        query=request.query,
    )
