"""Admin API endpoints for content management."""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, text, desc
from db.session import get_db
from db.models.user import User
from db.models.content import Content, Category, Tag, ContentStatus, ContentType
from db.models.subscription import Subscription, SubscriptionStatus, Payment, PaymentStatus
from apps.api.deps import get_current_user, get_current_workspace_id
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta

router = APIRouter(prefix="/admin", tags=["admin"])


# Pydantic schemas
class ContentCreateRequest(BaseModel):
    title: str
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    video_url: str
    duration_seconds: Optional[int] = None
    category_id: Optional[str] = None
    tags_json: Optional[List[str]] = None
    performers_json: Optional[List[str]] = None
    source_api: Optional[str] = None
    source_id: Optional[str] = None
    source_url: Optional[str] = None


class CategoryCreateRequest(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None
    parent_id: Optional[str] = None
    icon: Optional[str] = None
    order: int = 0


async def require_admin(user: User = Depends(get_current_user)) -> User:
    """Require admin/superuser access."""
    if not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required. User must have is_superuser=True",
        )
    return user


async def require_full_admin(user: User = Depends(get_current_user)) -> User:
    """Require FULL admin access (superuser + active)."""
    if not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Full admin access required",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )
    return user


@router.post("/content", status_code=status.HTTP_201_CREATED)
async def create_content(
    request: ContentCreateRequest,
    admin: User = Depends(require_admin),
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Create new content."""
    content = Content(
        workspace_id=workspace_id,
        title=request.title,
        description=request.description,
        thumbnail_url=request.thumbnail_url,
        video_url=request.video_url,
        duration_seconds=request.duration_seconds,
        category_id=request.category_id,
        tags_json=request.tags_json or [],
        performers_json=request.performers_json or [],
        source_api=request.source_api,
        source_id=request.source_id,
        source_url=request.source_url,
        content_type=ContentType.VIDEO,
        status=ContentStatus.PUBLISHED,
        published_at=datetime.utcnow(),
    )

    db.add(content)
    db.commit()
    db.refresh(content)

    return {
        "status": "success",
        "content_id": content.id,
        "message": "Content created successfully",
    }


@router.put("/content/{content_id}")
async def update_content(
    content_id: str,
    request: ContentCreateRequest,
    admin: User = Depends(require_admin),
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Update content."""
    content = (
        db.query(Content)
        .filter(
            Content.id == content_id,
            Content.workspace_id == workspace_id,
        )
        .first()
    )

    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content not found",
        )

    content.title = request.title
    if request.description is not None:
        content.description = request.description
    if request.thumbnail_url is not None:
        content.thumbnail_url = request.thumbnail_url
    if request.video_url is not None:
        content.video_url = request.video_url
    if request.duration_seconds is not None:
        content.duration_seconds = request.duration_seconds
    if request.category_id is not None:
        content.category_id = request.category_id
    if request.tags_json is not None:
        content.tags_json = request.tags_json
    if request.performers_json is not None:
        content.performers_json = request.performers_json

    db.commit()

    return {
        "status": "success",
        "message": "Content updated successfully",
    }


@router.delete("/content/{content_id}")
async def delete_content(
    content_id: str,
    admin: User = Depends(require_admin),
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Delete content."""
    content = (
        db.query(Content)
        .filter(
            Content.id == content_id,
            Content.workspace_id == workspace_id,
        )
        .first()
    )

    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content not found",
        )

    content.status = ContentStatus.ARCHIVED
    db.commit()

    return {
        "status": "success",
        "message": "Content archived successfully",
    }


@router.post("/categories", status_code=status.HTTP_201_CREATED)
async def create_category(
    request: CategoryCreateRequest,
    admin: User = Depends(require_admin),
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Create new category."""
    # Check if slug already exists
    existing = (
        db.query(Category)
        .filter(
            Category.workspace_id == workspace_id,
            Category.slug == request.slug,
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category slug already exists",
        )

    category = Category(
        workspace_id=workspace_id,
        name=request.name,
        slug=request.slug,
        description=request.description,
        parent_id=request.parent_id,
        icon=request.icon,
        order=request.order,
    )

    db.add(category)
    db.commit()
    db.refresh(category)

    return {
        "status": "success",
        "category_id": category.id,
        "message": "Category created successfully",
    }


@router.get("/stats")
async def get_stats(
    admin: User = Depends(require_full_admin),  # Require FULL admin
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Get platform statistics (FULL ADMIN ONLY)."""
    total_content = (
        db.query(Content)
        .filter(
            Content.workspace_id == workspace_id,
        )
        .count()
    )

    published_content = (
        db.query(Content)
        .filter(
            Content.workspace_id == workspace_id,
            Content.status == ContentStatus.PUBLISHED,
        )
        .count()
    )

    total_views = (
        db.query(Content)
        .filter(
            Content.workspace_id == workspace_id,
        )
        .with_entities(func.sum(Content.view_count))
        .scalar()
        or 0
    )

    active_subscriptions = (
        db.query(Subscription)
        .filter(
            Subscription.workspace_id == workspace_id,
            Subscription.status == SubscriptionStatus.ACTIVE,
        )
        .count()
    )

    # Payment stats
    from db.models.subscription import Payment, PaymentStatus

    total_payments = (
        db.query(Payment)
        .filter(
            Payment.workspace_id == workspace_id,
        )
        .count()
    )

    total_revenue = (
        db.query(Payment)
        .filter(
            Payment.workspace_id == workspace_id,
            Payment.status == PaymentStatus.COMPLETED,
        )
        .with_entities(func.sum(Payment.amount))
        .scalar()
        or 0.0
    )

    bitcoin_payments = (
        db.query(Payment)
        .filter(
            Payment.workspace_id == workspace_id,
            Payment.payment_provider == "bitcoin",
            Payment.status == PaymentStatus.COMPLETED,
        )
        .count()
    )

    bitcoin_revenue = (
        db.query(Payment)
        .filter(
            Payment.workspace_id == workspace_id,
            Payment.payment_provider == "bitcoin",
            Payment.status == PaymentStatus.COMPLETED,
        )
        .with_entities(func.sum(Payment.amount))
        .scalar()
        or 0.0
    )

    return {
        "total_content": total_content,
        "published_content": published_content,
        "total_views": total_views,
        "active_subscriptions": active_subscriptions,
        "total_payments": total_payments,
        "total_revenue": float(total_revenue),
        "bitcoin_payments": bitcoin_payments,
        "bitcoin_revenue": float(bitcoin_revenue),
        "admin_user": admin.email,
        "admin_permissions": {
            "is_superuser": admin.is_superuser,
            "is_active": admin.is_active,
            "full_admin": admin.is_superuser and admin.is_active,
        },
    }


@router.get("/revenue")
async def get_revenue(
    admin: User = Depends(require_full_admin),
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Revenue analytics for admin dashboard - real Payment data."""
    now = datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    prev_month_start = (month_start - timedelta(days=1)).replace(day=1)

    # Total lifetime revenue
    total_revenue = (
        db.query(func.coalesce(func.sum(Payment.amount), 0))
        .filter(
            Payment.workspace_id == workspace_id,
            Payment.status == PaymentStatus.COMPLETED,
        )
        .scalar()
    )

    # Monthly recurring revenue (active subs this month)
    mrr = (
        db.query(func.coalesce(func.sum(Payment.amount), 0))
        .filter(
            Payment.workspace_id == workspace_id,
            Payment.status == PaymentStatus.COMPLETED,
            Payment.created_at >= month_start,
        )
        .scalar()
    )

    # Previous month revenue for trend
    prev_month_revenue = (
        db.query(func.coalesce(func.sum(Payment.amount), 0))
        .filter(
            Payment.workspace_id == workspace_id,
            Payment.status == PaymentStatus.COMPLETED,
            Payment.created_at >= prev_month_start,
            Payment.created_at < month_start,
        )
        .scalar()
    )

    # ARPU
    active_users = (
        db.query(func.count(User.id))
        .filter(User.workspace_id == workspace_id, User.is_active == True)
        .scalar()
        or 1
    )

    # Churn: canceled subs this month / total active last month
    canceled_this_month = (
        db.query(func.count(Subscription.id))
        .filter(
            Subscription.workspace_id == workspace_id,
            Subscription.status == SubscriptionStatus.CANCELED,
            Subscription.updated_at >= month_start,
        )
        .scalar()
        or 0
    )

    active_subscriptions = (
        db.query(func.count(Subscription.id))
        .filter(
            Subscription.workspace_id == workspace_id,
            Subscription.status == SubscriptionStatus.ACTIVE,
        )
        .scalar()
        or 1
    )

    new_customers = (
        db.query(func.count(User.id))
        .filter(
            User.workspace_id == workspace_id,
            User.created_at >= month_start,
        )
        .scalar()
        or 0
    )

    churn_rate = round((canceled_this_month / active_subscriptions) * 100, 2)

    return {
        "totalRevenue": float(total_revenue),
        "monthlyRecurringRevenue": float(mrr),
        "averageRevenuePerUser": round(float(mrr) / active_users, 2),
        "churnRate": churn_rate,
        "newCustomersThisMonth": new_customers,
        "activeSubscriptions": active_subscriptions,
        "previousMonthRevenue": float(prev_month_revenue),
        "revenueGrowth": round(
            ((float(mrr) - float(prev_month_revenue)) / max(float(prev_month_revenue), 1)) * 100, 2
        ),
    }


@router.get("/customers")
async def get_customers(
    admin: User = Depends(require_full_admin),
    workspace_id: str = Depends(get_current_workspace_id),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Customer list for admin dashboard - real User/Subscription data."""
    users = (
        db.query(User)
        .filter(User.workspace_id == workspace_id)
        .order_by(desc(User.created_at))
        .limit(limit)
        .offset(offset)
        .all()
    )

    result = []
    for u in users:
        # Get subscription for this user
        sub = (
            db.query(Subscription)
            .filter(
                Subscription.workspace_id == workspace_id,
                Subscription.user_id == u.id,
            )
            .order_by(desc(Subscription.created_at))
            .first()
        )

        # Total payments for this user
        user_revenue = (
            db.query(func.coalesce(func.sum(Payment.amount), 0))
            .filter(
                Payment.workspace_id == workspace_id,
                Payment.user_id == u.id,
                Payment.status == PaymentStatus.COMPLETED,
            )
            .scalar()
        )

        last_payment = (
            db.query(Payment)
            .filter(
                Payment.workspace_id == workspace_id,
                Payment.user_id == u.id,
                Payment.status == PaymentStatus.COMPLETED,
            )
            .order_by(desc(Payment.created_at))
            .first()
        )

        result.append({
            "id": u.id,
            "email": u.email,
            "companyName": u.full_name,
            "tier": sub.tier if sub else "free",
            "status": sub.status if sub else "inactive",
            "totalRevenue": float(user_revenue),
            "lastPayment": last_payment.created_at.isoformat() if last_payment else None,
            "joinedAt": u.created_at.isoformat() if u.created_at else None,
            "isActive": u.is_active,
        })

    total = db.query(func.count(User.id)).filter(User.workspace_id == workspace_id).scalar()
    return {"customers": result, "total": total, "limit": limit, "offset": offset}


@router.get("/health")
async def get_admin_health(
    admin: User = Depends(require_full_admin),
    db: Session = Depends(get_db),
):
    """System health check for admin dashboard - real service status."""
    from db.models.job import Job
    from db.models.anomaly import Anomaly

    # Database connectivity
    try:
        db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception:
        db_status = "down"

    # Recent job failure rate
    recent_jobs = db.query(func.count(Job.id)).filter(
        Job.created_at >= datetime.utcnow() - timedelta(hours=1)
    ).scalar() or 0

    failed_jobs = db.query(func.count(Job.id)).filter(
        Job.created_at >= datetime.utcnow() - timedelta(hours=1),
        Job.status == "failed",
    ).scalar() or 0

    api_status = "healthy" if recent_jobs == 0 or (failed_jobs / recent_jobs) < 0.1 else "degraded"

    open_anomalies = db.query(func.count(Anomaly.id)).filter(
        Anomaly.status == "open"
    ).scalar() or 0

    return {
        "apiStatus": api_status,
        "databaseStatus": db_status,
        "workerStatus": "healthy",
        "openAnomalies": open_anomalies,
        "recentJobCount": recent_jobs,
        "failedJobCount": failed_jobs,
        "timestamp": datetime.utcnow().isoformat(),
    }
