"""Content API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc
from typing import List, Optional
from fastapi import Header
from db.session import get_db
from db.models.content import Content, Category, Tag, ContentStatus, ContentType
from db.models.subscription import Subscription, SubscriptionTier
from apps.api.deps import get_current_user, get_current_workspace_id
from db.models.user import User
from apps.api.deps_subscription import require_subscription, get_user_subscription
from pydantic import BaseModel
from datetime import datetime
from core.content_apis import ContentAggregator

router = APIRouter(prefix="/content", tags=["content"])


# Pydantic schemas
class ContentResponse(BaseModel):
    id: str
    title: str
    description: Optional[str]
    thumbnail_url: Optional[str]
    video_url: str
    duration_seconds: Optional[int]
    content_type: str
    view_count: int
    like_count: int
    category_id: Optional[str]
    tags_json: Optional[List[str]]
    performers_json: Optional[List[str]]
    published_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


class ContentListResponse(BaseModel):
    items: List[ContentResponse]
    total: int
    page: int
    page_size: int


class CategoryResponse(BaseModel):
    id: str
    name: str
    slug: str
    description: Optional[str]
    icon: Optional[str]

    class Config:
        from_attributes = True


@router.get("/", response_model=ContentListResponse)
async def list_content(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
    search: Optional[str] = None,
    tags: Optional[str] = None,  # Comma-separated tags
    sort: str = Query("newest", pattern="^(newest|popular|views|likes)$"),
    subscription: Optional[Subscription] = Depends(get_user_subscription),
    user: User = Depends(get_current_user),
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """List content with filtering and pagination.

    ADMIN USERS (is_superuser=True) have FULL ACCESS without subscription.
    All other users MUST pay/subscribe to access content.
    """
    # ADMIN BYPASS: Full access for superusers (handled in get_user_subscription)
    # Regular users MUST have active subscription
    if not subscription or not subscription.is_active():
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Subscription required to view content. Admin users have full access.",
        )

    query = db.query(Content).filter(
        Content.workspace_id == workspace_id,
        Content.status == ContentStatus.PUBLISHED,
    )

    # Filter by category
    if category:
        cat = (
            db.query(Category)
            .filter(
                Category.workspace_id == workspace_id,
                Category.slug == category,
            )
            .first()
        )
        if cat:
            query = query.filter(Content.category_id == cat.id)

    # Search
    if search:
        query = query.filter(
            or_(
                Content.title.ilike(f"%{search}%"),
                Content.description.ilike(f"%{search}%"),
            )
        )

    # Tags filter
    if tags:
        tag_list = [t.strip() for t in tags.split(",")]
        # This is simplified - in production, use proper tag relationship filtering
        for tag_name in tag_list:
            query = query.filter(Content.tags_json.contains([tag_name]))

    # Sorting
    if sort == "newest":
        query = query.order_by(desc(Content.published_at))
    elif sort == "popular":
        query = query.order_by(desc(Content.view_count))
    elif sort == "views":
        query = query.order_by(desc(Content.view_count))
    elif sort == "likes":
        query = query.order_by(desc(Content.like_count))

    # Pagination
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    return ContentListResponse(
        items=[ContentResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{content_id}", response_model=ContentResponse)
async def get_content(
    content_id: str,
    subscription: Subscription = Depends(require_subscription),
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Get single content item."""
    content = (
        db.query(Content)
        .filter(
            Content.id == content_id,
            Content.workspace_id == workspace_id,
            Content.status == ContentStatus.PUBLISHED,
        )
        .first()
    )

    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content not found",
        )

    # Increment view count
    content.view_count += 1
    db.commit()

    return ContentResponse.model_validate(content)


@router.get("/categories/list", response_model=List[CategoryResponse])
async def list_categories(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """List all categories."""
    # Try to get workspace_id from token, but allow public access
    workspace_id = None
    try:
        if authorization:
            from apps.api.deps import get_current_workspace_id

            workspace_id = await get_current_workspace_id(authorization, db)
    except:
        pass

    query = db.query(Category)
    if workspace_id:
        query = query.filter(Category.workspace_id == workspace_id)
    query = query.filter(Category.is_active == True)
    categories = query.order_by(Category.order).all()

    return [CategoryResponse.model_validate(cat) for cat in categories]


@router.post("/aggregate")
async def aggregate_content(
    query: str = Query(..., description="Search query"),
    category: Optional[str] = None,
    limit: int = Query(30, ge=1, le=50),  # Reduced max limit to 50
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """
    Aggregate content from external APIs and import to database.

    Note: Rate limited to prevent aggressive requests.
    Max 50 items per request, with delays between API calls.
    """
    # Limit requests to prevent overwhelming servers
    if limit > 50:
        limit = 50

    aggregator = ContentAggregator()

    try:
        # Search all APIs with conservative limits
        # Split limit across APIs (max 10 per API to be safe)
        limit_per_api = min(10, limit // len(aggregator.clients))
        videos = await aggregator.search_all(query, category, limit_per_api=limit_per_api)

        imported_count = 0
        # Process videos in batches to avoid overwhelming database
        batch_size = 10
        for i in range(0, len(videos), batch_size):
            batch = videos[i : i + batch_size]

            for video_data in batch:
                # Check if already exists
                existing = (
                    db.query(Content)
                    .filter(
                        Content.workspace_id == workspace_id,
                        Content.source_api == video_data.get("source_api"),
                        Content.source_id == video_data.get("source_id"),
                    )
                    .first()
                )

                if not existing:
                    content = Content(
                        workspace_id=workspace_id,
                        title=video_data.get("title", "Untitled"),
                        description="",
                        thumbnail_url=video_data.get("thumbnail"),
                        video_url=video_data.get("url"),
                        duration_seconds=video_data.get("duration"),
                        content_type=ContentType.VIDEO,
                        status=ContentStatus.PUBLISHED,
                        source_api=video_data.get("source_api"),
                        source_id=video_data.get("source_id"),
                        source_url=video_data.get("url"),
                        tags_json=video_data.get("tags", []),
                        view_count=video_data.get("views", 0),
                        published_at=datetime.utcnow(),
                    )

                    # Assign category if provided
                    if category:
                        cat = (
                            db.query(Category)
                            .filter(
                                Category.workspace_id == workspace_id,
                                Category.slug == category,
                            )
                            .first()
                        )
                        if cat:
                            content.category_id = cat.id

                    db.add(content)
                    imported_count += 1

            # Commit batch
            db.commit()

            # Small delay between batches
            if i + batch_size < len(videos):
                await asyncio.sleep(1)

        return {
            "status": "success",
            "found": len(videos),
            "imported": imported_count,
            "message": f"Imported {imported_count} new videos (rate limited for safety)",
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Content aggregation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Aggregation failed: {str(e)}",
        )
    finally:
        await aggregator.close()
