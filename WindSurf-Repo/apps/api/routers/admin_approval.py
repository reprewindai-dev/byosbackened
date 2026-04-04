"""Admin content approval endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from db.session import get_db
from db.models.content import Content, ContentStatus
from db.models.user import User
from apps.api.deps import get_current_user
from apps.api.routers.admin import require_full_admin
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin/approval", tags=["admin-approval"])


class ApprovalRequest(BaseModel):
    """Content approval request."""

    content_id: str
    approve: bool  # True to approve, False to reject
    notes: Optional[str] = None


class ApprovalResponse(BaseModel):
    """Approval response."""

    content_id: str
    status: str
    message: str


class PendingContentResponse(BaseModel):
    """Pending content item."""

    id: str
    title: str
    description: Optional[str]
    video_url: str
    uploaded_by: dict
    uploaded_at: datetime
    category_id: Optional[str]
    tags: Optional[List[str]]


class PendingContentListResponse(BaseModel):
    """List of pending content."""

    items: List[PendingContentResponse]
    total: int


@router.get("/pending", response_model=PendingContentListResponse)
async def get_pending_content(
    admin: User = Depends(require_full_admin),
    db: Session = Depends(get_db),
    page: int = 1,
    page_size: int = 20,
):
    """Get all content pending approval (admin only)."""

    query = db.query(Content).filter(
        Content.status == ContentStatus.PENDING_APPROVAL,
    )

    total = query.count()
    items = (
        query.order_by(Content.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    # Get uploader info
    result_items = []
    for item in items:
        uploader = db.query(User).filter(User.id == item.uploaded_by_user_id).first()
        result_items.append(
            PendingContentResponse(
                id=item.id,
                title=item.title,
                description=item.description,
                video_url=item.video_url,
                uploaded_by={
                    "id": uploader.id if uploader else None,
                    "email": uploader.email if uploader else None,
                    "full_name": uploader.full_name if uploader else None,
                },
                uploaded_at=item.created_at,
                category_id=item.category_id,
                tags=item.tags_json or [],
            )
        )

    return PendingContentListResponse(items=result_items, total=total)


@router.post("/approve", response_model=ApprovalResponse)
async def approve_content(
    request: ApprovalRequest,
    admin: User = Depends(require_full_admin),
    db: Session = Depends(get_db),
):
    """Approve or reject content (admin only)."""

    content = db.query(Content).filter(Content.id == request.content_id).first()

    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content not found",
        )

    if content.status != ContentStatus.PENDING_APPROVAL:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Content is not pending approval (current status: {content.status.value})",
        )

    # Update status
    if request.approve:
        content.status = ContentStatus.APPROVED
        content.published_at = datetime.utcnow()
        message = "Content approved and published!"
    else:
        content.status = ContentStatus.REJECTED
        message = "Content rejected."

    content.approved_by_admin_id = admin.id
    content.approval_notes = request.notes
    content.approval_date = datetime.utcnow()

    db.commit()
    db.refresh(content)

    logger.info(
        f"Admin {admin.id} {'approved' if request.approve else 'rejected'} content {content.id}"
    )

    return ApprovalResponse(
        content_id=content.id,
        status=content.status.value,
        message=message,
    )


@router.get("/stats")
async def get_approval_stats(
    admin: User = Depends(require_full_admin),
    db: Session = Depends(get_db),
):
    """Get approval statistics (admin only)."""

    pending = db.query(Content).filter(Content.status == ContentStatus.PENDING_APPROVAL).count()
    approved = db.query(Content).filter(Content.status == ContentStatus.APPROVED).count()
    rejected = db.query(Content).filter(Content.status == ContentStatus.REJECTED).count()
    total_uploads = db.query(Content).filter(Content.uploaded_by_user_id.isnot(None)).count()

    return {
        "pending": pending,
        "approved": approved,
        "rejected": rejected,
        "total_uploads": total_uploads,
        "approval_rate": round((approved / total_uploads * 100) if total_uploads > 0 else 0, 2),
    }


class CreatorApplicationRequest(BaseModel):
    name: str
    email: str
    niche: str
    bio: Optional[str] = None


@router.post("/creator-apply", tags=["creators"], summary="Submit creator application (public)")
async def submit_creator_application(req: CreatorApplicationRequest):
    """
    Public endpoint — receives creator applications from the /creators page.
    Logged for admin review. No auth required.
    """
    logger.info(
        f"[creator-apply] name={req.name!r} email={req.email!r} niche={req.niche!r}"
    )
    return {
        "status": "received",
        "message": "Your application has been received. We review within 24 hours.",
        "reference": f"APP-{hash(req.email) % 999999:06d}",
    }
