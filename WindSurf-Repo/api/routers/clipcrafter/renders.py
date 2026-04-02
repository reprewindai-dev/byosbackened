"""ClipCrafter renders endpoints."""

from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.orm import Session
from db.session import get_db
from db.models.app import App
from db.models.workspace import Workspace
from apps.clipcrafter.schemas import (
    RenderCreate,
    RenderResponse,
)
from apps.clipcrafter.services import RenderService
from typing import List, Optional

router = APIRouter(prefix="/clipcrafter", tags=["ClipCrafter"])


@router.post(
    "/projects/{project_id}/renders",
    response_model=RenderResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_render(
    project_id: str,
    render_data: RenderCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    """Create a new render job for a project."""
    app: App = request.state.app
    workspace: Workspace = request.state.workspace

    render = RenderService.create_render(db, app, workspace, project_id, render_data)
    return RenderResponse(**render.__dict__)


@router.get("/renders", response_model=List[RenderResponse])
async def list_renders(
    request: Request,
    project_id: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List renders, optionally filtered by project and status."""
    app: App = request.state.app
    workspace: Workspace = request.state.workspace

    renders = RenderService.list_renders(db, app, workspace, project_id=project_id, status=status)
    return [RenderResponse(**render.__dict__) for render in renders]


@router.get("/renders/{render_id}", response_model=RenderResponse)
async def get_render(
    render_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """Get a render by ID."""
    app: App = request.state.app
    workspace: Workspace = request.state.workspace

    render = RenderService.get_render(db, app, workspace, render_id)
    return RenderResponse(**render.__dict__)
