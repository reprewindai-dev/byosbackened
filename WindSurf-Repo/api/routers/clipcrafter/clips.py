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
    db: Session = Depends(get_db),
):
    """List clips, optionally filtered by project and type."""
    app: App = request.state.app
    workspace: Workspace = request.state.workspace

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
