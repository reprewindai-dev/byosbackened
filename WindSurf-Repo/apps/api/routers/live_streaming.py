"""Live streaming endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from db.session import get_db
from db.models.content import Content, ContentStatus, ContentType
from db.models.live_stream import LiveStream, LiveStreamStatus, LiveStreamViewer, LiveStreamGift
from db.models.user import User
from apps.api.deps import get_current_user, get_current_workspace_id
from apps.api.deps_subscription import require_subscription
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
import uuid
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/live", tags=["live-streaming"])
settings = None
try:
    from core.config import get_settings

    settings = get_settings()
except:
    pass


class StartLiveRequest(BaseModel):
    """Start live stream request."""

    title: str
    description: Optional[str] = None
    category_id: Optional[str] = None
    tags: Optional[List[str]] = None
    chat_enabled: bool = True
    gifts_enabled: bool = True


class StartLiveResponse(BaseModel):
    """Start live stream response."""

    stream_id: str
    rtmp_url: str
    stream_key: str
    playback_url: str
    message: str


class LiveStreamResponse(BaseModel):
    """Live stream info."""

    id: str
    title: str
    status: str
    current_viewers: int
    peak_viewers: int
    likes_count: int
    gems_earned: int
    started_at: Optional[datetime]
    duration_minutes: int


class LiveStreamListResponse(BaseModel):
    """List of live streams."""

    items: List[LiveStreamResponse]
    total: int


@router.post("/start", response_model=StartLiveResponse, status_code=status.HTTP_201_CREATED)
async def start_live_stream(
    request: StartLiveRequest,
    user: User = Depends(get_current_user),
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
    subscription=Depends(require_subscription),  # Must have subscription to go live
):
    """Start a live stream (like TikTok Live)."""

    # Check if user already has an active stream
    active_stream = (
        db.query(LiveStream)
        .filter(
            LiveStream.user_id == user.id,
            LiveStream.status == LiveStreamStatus.LIVE,
        )
        .first()
    )

    if active_stream:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have an active live stream",
        )

    # Generate stream key
    stream_key = f"{user.id}_{uuid.uuid4().hex[:16]}"

    # Create content entry
    content = Content(
        workspace_id=workspace_id,
        title=request.title,
        description=request.description,
        content_type=ContentType.LIVE,
        status=ContentStatus.LIVE,
        category_id=request.category_id,
        tags_json=request.tags or [],
        uploaded_by_user_id=user.id,
        is_live=True,
        live_started_at=datetime.utcnow(),
        live_chat_enabled=request.chat_enabled,
    )
    db.add(content)
    db.flush()

    # Create live stream entry
    stream = LiveStream(
        user_id=user.id,
        workspace_id=workspace_id,
        content_id=content.id,
        title=request.title,
        description=request.description,
        rtmp_url=f"rtmp://live.example.com/live",  # Replace with actual RTMP server
        stream_key=stream_key,
        playback_url=f"https://stream.example.com/hls/{stream_key}.m3u8",  # Replace with actual playback URL
        status=LiveStreamStatus.LIVE,
        started_at=datetime.utcnow(),
        chat_enabled=request.chat_enabled,
        gifts_enabled=request.gifts_enabled,
        tags_json=request.tags or [],
    )
    db.add(stream)
    db.commit()
    db.refresh(stream)

    logger.info(f"User {user.id} started live stream {stream.id}")

    return StartLiveResponse(
        stream_id=stream.id,
        rtmp_url=stream.rtmp_url,
        stream_key=stream_key,
        playback_url=stream.playback_url,
        message="Live stream started! Share your stream URL with viewers.",
    )


@router.post("/{stream_id}/end")
async def end_live_stream(
    stream_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """End a live stream."""

    stream = (
        db.query(LiveStream)
        .filter(
            LiveStream.id == stream_id,
            LiveStream.user_id == user.id,
        )
        .first()
    )

    if not stream:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stream not found",
        )

    if stream.status != LiveStreamStatus.LIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stream is not currently live",
        )

    # Calculate duration
    duration = (
        (datetime.utcnow() - stream.started_at).total_seconds() / 60 if stream.started_at else 0
    )

    # Update stream
    stream.status = LiveStreamStatus.ENDED
    stream.ended_at = datetime.utcnow()
    stream.duration_minutes = int(duration)

    # Update content
    if stream.content_id:
        content = db.query(Content).filter(Content.id == stream.content_id).first()
        if content:
            content.is_live = False
            content.status = ContentStatus.APPROVED  # Auto-approve after live ends
            content.live_ended_at = datetime.utcnow()

    # Calculate rewards (gems based on viewers, duration, gifts)
    base_gems = 10  # Base gems for going live
    viewer_bonus = stream.peak_viewers * 2  # 2 gems per peak viewer
    duration_bonus = int(duration) * 1  # 1 gem per minute
    gift_bonus = stream.gifts_received * 5  # 5 gems per gift

    total_gems = base_gems + viewer_bonus + duration_bonus + gift_bonus
    stream.gems_earned = total_gems

    # Update user stats
    user.gems += total_gems
    user.total_live_sessions += 1
    user.total_live_minutes += int(duration)
    user.total_live_viewers += stream.peak_viewers
    user.monthly_live_score += total_gems  # Add to monthly score

    db.commit()

    logger.info(f"User {user.id} ended live stream {stream_id}, earned {total_gems} gems")

    return {
        "message": "Live stream ended",
        "gems_earned": total_gems,
        "duration_minutes": int(duration),
        "peak_viewers": stream.peak_viewers,
    }


@router.get("/active", response_model=LiveStreamListResponse)
async def get_active_streams(
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
    page: int = 1,
    page_size: int = 20,
):
    """Get all currently active live streams."""

    query = db.query(LiveStream).filter(
        LiveStream.workspace_id == workspace_id,
        LiveStream.status == LiveStreamStatus.LIVE,
    )

    total = query.count()
    items = (
        query.order_by(LiveStream.started_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return LiveStreamListResponse(
        items=[
            LiveStreamResponse(
                id=item.id,
                title=item.title,
                status=item.status.value,
                current_viewers=item.current_viewers,
                peak_viewers=item.peak_viewers,
                likes_count=item.likes_count,
                gems_earned=item.gems_earned,
                started_at=item.started_at,
                duration_minutes=item.duration_minutes,
            )
            for item in items
        ],
        total=total,
    )


@router.post("/{stream_id}/join")
async def join_live_stream(
    stream_id: str,
    user: Optional[User] = Depends(get_current_user),  # Optional for anonymous viewers
    db: Session = Depends(get_db),
):
    """Join a live stream as viewer."""

    stream = db.query(LiveStream).filter(LiveStream.id == stream_id).first()

    if not stream:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stream not found",
        )

    if stream.status != LiveStreamStatus.LIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stream is not currently live",
        )

    # Create viewer entry
    viewer = LiveStreamViewer(
        stream_id=stream_id,
        viewer_user_id=user.id if user else None,
    )
    db.add(viewer)

    # Update stream viewer count
    stream.current_viewers += 1
    if stream.current_viewers > stream.peak_viewers:
        stream.peak_viewers = stream.current_viewers
    stream.total_views += 1

    db.commit()

    return {
        "message": "Joined live stream",
        "current_viewers": stream.current_viewers,
    }


@router.post("/{stream_id}/gift")
async def send_gift(
    stream_id: str,
    gift_type: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    subscription=Depends(require_subscription),
):
    """Send a virtual gift during live stream."""

    stream = db.query(LiveStream).filter(LiveStream.id == stream_id).first()

    if not stream:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stream not found",
        )

    if not stream.gifts_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Gifts are disabled for this stream",
        )

    # Gift values (in gems)
    gift_values = {
        "rose": 10,
        "diamond": 50,
        "crown": 100,
        "super_star": 500,
    }

    gift_value = gift_values.get(gift_type, 10)

    # Check if user has enough gems (or allow anyway for now)
    # In production, you'd deduct gems here

    # Create gift entry
    gift = LiveStreamGift(
        stream_id=stream_id,
        sender_user_id=user.id,
        gift_type=gift_type,
        gift_value=gift_value,
    )
    db.add(gift)

    # Update stream
    stream.gifts_received += 1

    # Streamer gets gems
    streamer = db.query(User).filter(User.id == stream.user_id).first()
    if streamer:
        streamer.gems += gift_value
        streamer.monthly_live_score += gift_value

    db.commit()

    return {
        "message": f"Gift sent: {gift_type}",
        "gift_value": gift_value,
    }
