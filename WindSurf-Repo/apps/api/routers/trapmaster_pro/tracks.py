"""TrapMaster Pro tracks endpoints."""

from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.orm import Session
from db.session import get_db
from db.models.app import App
from db.models.workspace import Workspace
from apps.trapmaster_pro.schemas import (
    TrackCreate,
    TrackUpdate,
    TrackResponse,
)
from apps.trapmaster_pro.services import TrackService
from apps.api.deps import get_current_workspace_id
from typing import List, Optional

router = APIRouter(prefix="/trapmaster-pro", tags=["TrapMaster Pro"])


@router.post(
    "/projects/{project_id}/tracks",
    response_model=TrackResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_track(
    project_id: str,
    track_data: TrackCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    """Create a new track in a project."""
    app: App = request.state.app
    workspace: Workspace = request.state.workspace

    track = TrackService.create_track(db, app, workspace, project_id, track_data)
    return TrackResponse(**track.__dict__)


@router.get("/tracks", response_model=List[TrackResponse])
async def list_tracks(
    request: Request,
    project_id: Optional[str] = None,
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """List tracks, optionally filtered by project."""
    # Try to get app/workspace from request.state (set by middleware), fallback to deps
    app = getattr(request.state, "app", None)
    workspace = getattr(request.state, "workspace", None)

    if not workspace:
        workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
        if not workspace:
            raise HTTPException(status_code=404, detail="Workspace not found")

    if not app:
        # Try to get trapmaster-pro app
        app = db.query(App).filter(App.slug == "trapmaster-pro").first()
        if not app:
            raise HTTPException(status_code=404, detail="TrapMaster Pro app not found")

    tracks = TrackService.list_tracks(db, app, workspace, project_id=project_id)
    return [TrackResponse(**track.__dict__) for track in tracks]


@router.get("/tracks/{track_id}", response_model=TrackResponse)
async def get_track(
    track_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """Get a track by ID."""
    app: App = request.state.app
    workspace: Workspace = request.state.workspace

    track = TrackService.get_track(db, app, workspace, track_id)
    return TrackResponse(**track.__dict__)


@router.put("/tracks/{track_id}", response_model=TrackResponse)
async def update_track(
    track_id: str,
    track_data: TrackUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    """Update a track."""
    app: App = request.state.app
    workspace: Workspace = request.state.workspace

    track = TrackService.update_track(db, app, workspace, track_id, track_data)
    return TrackResponse(**track.__dict__)


@router.delete("/tracks/{track_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_track(
    track_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """Delete a track."""
    app: App = request.state.app
    workspace: Workspace = request.state.workspace

    TrackService.delete_track(db, app, workspace, track_id)
    return None


# ─── AI-Powered TrapMaster Pro Endpoints ─────────────────────────────────────

@router.post("/ai/describe-beat")
async def ai_describe_beat(
    genre: str = "trap",
    tempo: int = 140,
    mood: str = "energetic",
    key: str = "A minor",
):
    """Generate beat description using HuggingFace Mistral."""
    from apps.trapmaster_pro.ai_service import generate_beat_description, generate_track_tags
    description = await generate_beat_description(genre, tempo, mood, key)
    tags = await generate_track_tags(genre, mood, description)
    return {"description": description, "tags": tags, "provider": "huggingface/mistral-7b"}


@router.post("/ai/generate-sample")
async def ai_generate_music_sample(
    prompt: str,
    duration_seconds: int = 10,
):
    """Generate a music sample using HuggingFace MusicGen.
    Returns WAV audio bytes."""
    from apps.trapmaster_pro.ai_service import generate_music_sample
    from fastapi.responses import Response
    try:
        audio_bytes = await generate_music_sample(prompt, duration_seconds)
        return Response(
            content=audio_bytes,
            media_type="audio/wav",
            headers={"Content-Disposition": "attachment; filename=generated_beat.wav"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Music generation failed: {str(e)}")


@router.post("/ai/suggest-similar")
async def ai_suggest_similar(track_description: str):
    """Suggest similar tracks using HuggingFace Mistral."""
    from apps.trapmaster_pro.ai_service import suggest_similar_tracks
    suggestions = await suggest_similar_tracks(track_description)
    return {"suggestions": suggestions, "provider": "huggingface/mistral-7b"}
