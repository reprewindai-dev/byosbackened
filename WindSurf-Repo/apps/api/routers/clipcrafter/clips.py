"""ClipCrafter clips endpoints."""

from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.orm import Session
from db.session import get_db
from db.models.app import App
from db.models.workspace import Workspace
from apps.clipcrafter.schemas import (
    ClipCreate,
    ClipUpdate,
    ClipResponse,
)
from apps.clipcrafter.services import ClipService
from apps.api.deps import get_current_workspace_id
from typing import List, Optional

router = APIRouter(prefix="/clipcrafter", tags=["ClipCrafter"])


@router.post(
    "/projects/{project_id}/clips", response_model=ClipResponse, status_code=status.HTTP_201_CREATED
)
async def create_clip(
    project_id: str,
    clip_data: ClipCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    """Create a new clip in a project."""
    app: App = request.state.app
    workspace: Workspace = request.state.workspace

    clip = ClipService.create_clip(db, app, workspace, project_id, clip_data)
    return ClipResponse(**clip.__dict__)


@router.get("/clips", response_model=List[ClipResponse])
async def list_clips(
    request: Request,
    project_id: Optional[str] = None,
    clip_type: Optional[str] = None,
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """List clips, optionally filtered by project and type."""
    # Try to get app/workspace from request.state (set by middleware), fallback to deps
    app = getattr(request.state, "app", None)
    workspace = getattr(request.state, "workspace", None)

    if not workspace:
        workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
        if not workspace:
            raise HTTPException(status_code=404, detail="Workspace not found")

    if not app:
        # Try to get clipcrafter app
        app = db.query(App).filter(App.slug == "clipcrafter").first()
        if not app:
            raise HTTPException(status_code=404, detail="ClipCrafter app not found")

    clips = ClipService.list_clips(db, app, workspace, project_id=project_id, clip_type=clip_type)
    return [ClipResponse(**clip.__dict__) for clip in clips]


@router.get("/clips/{clip_id}", response_model=ClipResponse)
async def get_clip(
    clip_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """Get a clip by ID."""
    app: App = request.state.app
    workspace: Workspace = request.state.workspace

    clip = ClipService.get_clip(db, app, workspace, clip_id)
    return ClipResponse(**clip.__dict__)


@router.put("/clips/{clip_id}", response_model=ClipResponse)
async def update_clip(
    clip_id: str,
    clip_data: ClipUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    """Update a clip."""
    app: App = request.state.app
    workspace: Workspace = request.state.workspace

    clip = ClipService.update_clip(db, app, workspace, clip_id, clip_data)
    return ClipResponse(**clip.__dict__)


@router.delete("/clips/{clip_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_clip(
    clip_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """Delete a clip."""
    app: App = request.state.app
    workspace: Workspace = request.state.workspace

    ClipService.delete_clip(db, app, workspace, clip_id)
    return None


# ─── AI-Powered ClipCrafter Endpoints ────────────────────────────────────────

@router.post("/clips/{clip_id}/ai/describe")
async def ai_describe_clip(
    clip_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """Generate AI description for a clip using HuggingFace Mistral."""
    from apps.clipcrafter.ai_service import generate_clip_description, generate_clip_hashtags
    app: App = request.state.app
    workspace: Workspace = request.state.workspace

    clip = ClipService.get_clip(db, app, workspace, clip_id)
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")

    description = await generate_clip_description(
        video_title=getattr(clip, 'name', clip_id),
        transcript=getattr(clip, 'transcript', None),
    )
    hashtags = await generate_clip_hashtags(description)
    return {"clip_id": clip_id, "description": description, "hashtags": hashtags}


@router.post("/ai/transcribe")
async def ai_transcribe_audio(
    audio_url: str,
    language: str = "en",
    request: Request = None,
):
    """Transcribe audio using HuggingFace Whisper large-v3."""
    from apps.clipcrafter.ai_service import transcribe_audio
    try:
        transcript = await transcribe_audio(audio_url, language=language)
        return {"transcript": transcript, "language": language, "provider": "huggingface/whisper-large-v3"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")


@router.post("/ai/caption-thumbnail")
async def ai_caption_thumbnail(
    image_url: str,
    request: Request = None,
):
    """Generate caption for a thumbnail image using HuggingFace BLIP."""
    from apps.clipcrafter.ai_service import caption_thumbnail
    caption = await caption_thumbnail(image_url)
    return {"caption": caption, "image_url": image_url, "provider": "huggingface/blip"}
