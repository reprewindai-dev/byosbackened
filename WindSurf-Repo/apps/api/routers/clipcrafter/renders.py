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
from apps.api.deps import get_current_workspace_id
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
    filter_status: Optional[str] = None,
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """List renders, optionally filtered by project and status."""
    app = getattr(request.state, "app", None)
    workspace = getattr(request.state, "workspace", None)

    if not workspace:
        workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
        if not workspace:
            raise HTTPException(status_code=404, detail="Workspace not found")

    if not app:
        app = db.query(App).filter(App.slug == "clipcrafter").first()
        if not app:
            raise HTTPException(status_code=404, detail="ClipCrafter app not found")

    renders = RenderService.list_renders(db, app, workspace, project_id=project_id, status=filter_status)
    return [RenderResponse(**r.__dict__) for r in renders]


@router.get("/renders/{render_id}", response_model=RenderResponse)
async def get_render(
    render_id: str,
    request: Request,
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Get a render by ID."""
    app = getattr(request.state, "app", None)
    workspace = getattr(request.state, "workspace", None)

    if not workspace:
        workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
        if not workspace:
            raise HTTPException(status_code=404, detail="Workspace not found")

    if not app:
        app = db.query(App).filter(App.slug == "clipcrafter").first()
        if not app:
            raise HTTPException(status_code=404, detail="ClipCrafter app not found")

    render = RenderService.get_render(db, app, workspace, render_id)
    return RenderResponse(**render.__dict__)
