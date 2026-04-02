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
    db: Session = Depends(get_db),
):
    """List tracks, optionally filtered by project."""
    app: App = request.state.app
    workspace: Workspace = request.state.workspace

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
