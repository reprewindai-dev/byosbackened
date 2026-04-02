"""User content upload endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from db.session import get_db
from db.models.content import Content, ContentStatus, ContentType
from db.models.user import User
from apps.api.deps import get_current_user, get_current_workspace_id
from apps.api.deps_subscription import require_subscription
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from core.config import get_settings
import boto3
import uuid
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/user-uploads", tags=["user-uploads"])
settings = get_settings()

# S3 client
s3_client = boto3.client(
    "s3",
    endpoint_url=settings.s3_endpoint_url,
    aws_access_key_id=settings.s3_access_key_id,
    aws_secret_access_key=settings.s3_secret_access_key,
    region_name=settings.s3_region,
    use_ssl=settings.s3_use_ssl,
)


class UploadContentRequest(BaseModel):
    """Content upload request."""

    title: str
    description: Optional[str] = None
    category_id: Optional[str] = None
    tags: Optional[List[str]] = None
    is_live: bool = False  # For live streaming


class UploadContentResponse(BaseModel):
    """Content upload response."""

    id: str
    title: str
    status: str
    message: str
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None


class UserUploadListResponse(BaseModel):
    """List of user uploads."""

    items: List[dict]
    total: int
    pending_approval: int
    approved: int
    rejected: int


@router.post("/upload", response_model=UploadContentResponse, status_code=status.HTTP_201_CREATED)
async def upload_content(
    file: UploadFile = File(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    category_id: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),  # Comma-separated
    is_live: bool = Form(False),
    user: User = Depends(get_current_user),
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
    subscription=Depends(require_subscription),  # Must have subscription to upload
):
    """Upload content for admin approval."""

    # Generate S3 key
    file_id = str(uuid.uuid4())
    file_ext = file.filename.split(".")[-1] if "." in file.filename else "mp4"
    s3_key = f"user-uploads/{workspace_id}/{user.id}/{file_id}.{file_ext}"

    # Upload to S3
    try:
        file_content = await file.read()
        s3_client.put_object(
            Bucket=settings.s3_bucket_name,
            Key=s3_key,
            Body=file_content,
            ContentType=file.content_type or "video/mp4",
        )
        video_url = f"{settings.s3_endpoint_url}/{settings.s3_bucket_name}/{s3_key}"
    except Exception as e:
        logger.error(f"Failed to upload to S3: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file: {str(e)}",
        )

    # Parse tags
    tag_list = [t.strip() for t in tags.split(",")] if tags else []

    # Create content entry (pending approval)
    content = Content(
        workspace_id=workspace_id,
        title=title,
        description=description,
        video_url=video_url,
        content_type=ContentType.LIVE if is_live else ContentType.VIDEO,
        status=ContentStatus.PENDING_APPROVAL,
        category_id=category_id,
        tags_json=tag_list,
        uploaded_by_user_id=user.id,
        is_live=is_live,
    )

    db.add(content)
    db.commit()
    db.refresh(content)

    logger.info(f"User {user.id} uploaded content {content.id} - pending approval")

    return UploadContentResponse(
        id=content.id,
        title=content.title,
        status=content.status.value,
        message="Content uploaded successfully! Waiting for admin approval.",
        video_url=content.video_url,
    )


@router.get("/my-uploads", response_model=UserUploadListResponse)
async def get_my_uploads(
    user: User = Depends(get_current_user),
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
    page: int = 1,
    page_size: int = 20,
):
    """Get current user's uploaded content."""

    query = db.query(Content).filter(
        Content.workspace_id == workspace_id,
        Content.uploaded_by_user_id == user.id,
    )

    total = query.count()
    pending = query.filter(Content.status == ContentStatus.PENDING_APPROVAL).count()
    approved = query.filter(Content.status == ContentStatus.APPROVED).count()
    rejected = query.filter(Content.status == ContentStatus.REJECTED).count()

    items = (
        query.order_by(Content.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return UserUploadListResponse(
        items=[
            {
                "id": item.id,
                "title": item.title,
                "status": item.status.value,
                "created_at": item.created_at.isoformat(),
                "approval_notes": item.approval_notes,
                "video_url": item.video_url,
            }
            for item in items
        ],
        total=total,
        pending_approval=pending,
        approved=approved,
        rejected=rejected,
    )


@router.get("/pending-count")
async def get_pending_count(
    user: User = Depends(get_current_user),
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Get count of pending approval uploads."""
    count = (
        db.query(Content)
        .filter(
            Content.workspace_id == workspace_id,
            Content.uploaded_by_user_id == user.id,
            Content.status == ContentStatus.PENDING_APPROVAL,
        )
        .count()
    )

    return {"pending_count": count}
