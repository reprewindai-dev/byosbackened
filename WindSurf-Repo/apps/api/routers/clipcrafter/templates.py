"""ClipCrafter templates endpoints."""

from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.orm import Session
from db.session import get_db
from db.models.app import App
from db.models.workspace import Workspace
from apps.clipcrafter.schemas import (
    TemplateCreate,
    TemplateUpdate,
    TemplateResponse,
)
from apps.clipcrafter.services import TemplateService
from apps.api.deps import get_current_workspace_id
from typing import List, Optional

router = APIRouter(prefix="/clipcrafter", tags=["ClipCrafter"])


@router.post("/templates", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    template_data: TemplateCreate,
    request: Request,
    project_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Create a new template."""
    app: App = request.state.app
    workspace: Workspace = request.state.workspace

    template = TemplateService.create_template(
        db, app, workspace, template_data, project_id=project_id
    )
    return TemplateResponse(**template.__dict__)


@router.get("/templates", response_model=List[TemplateResponse])
async def list_templates(
    request: Request,
    project_id: Optional[str] = None,
    category: Optional[str] = None,
    is_favorite: Optional[bool] = None,
    include_public: bool = True,
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """List templates with optional filters."""
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

    templates = TemplateService.list_templates(
        db,
        app,
        workspace,
        project_id=project_id,
        category=category,
        is_favorite=is_favorite,
        include_public=include_public,
    )
    return [TemplateResponse(**template.__dict__) for template in templates]


@router.get("/templates/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """Get a template by ID."""
    app: App = request.state.app
    workspace: Workspace = request.state.workspace

    template = TemplateService.get_template(db, app, workspace, template_id)

    # Increment usage count when accessed
    TemplateService.increment_usage(db, template_id)

    return TemplateResponse(**template.__dict__)


@router.put("/templates/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: str,
    template_data: TemplateUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    """Update a template."""
    app: App = request.state.app
    workspace: Workspace = request.state.workspace

    template = TemplateService.update_template(db, app, workspace, template_id, template_data)
    return TemplateResponse(**template.__dict__)


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """Delete a template."""
    app: App = request.state.app
    workspace: Workspace = request.state.workspace

    TemplateService.delete_template(db, app, workspace, template_id)
    return None
