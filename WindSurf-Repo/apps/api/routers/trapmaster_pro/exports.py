"""TrapMaster Pro exports endpoints."""

from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.orm import Session
from db.session import get_db
from db.models.app import App
from db.models.workspace import Workspace
from apps.trapmaster_pro.schemas import (
    ExportCreate,
    ExportResponse,
)
from apps.trapmaster_pro.services import ExportService
from apps.api.deps import get_current_workspace_id
from typing import List, Optional

router = APIRouter(prefix="/trapmaster-pro", tags=["TrapMaster Pro"])


@router.post(
    "/projects/{project_id}/exports",
    response_model=ExportResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_export(
    project_id: str,
    export_data: ExportCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    """Create a new export job for a project."""
    app: App = request.state.app
    workspace: Workspace = request.state.workspace
    export = ExportService.create_export(db, app, workspace, project_id, export_data)
    return ExportResponse(**export.__dict__)


@router.get("/exports", response_model=List[ExportResponse])
async def list_exports(
    request: Request,
    project_id: Optional[str] = None,
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """List exports, optionally filtered by project."""
    app = getattr(request.state, "app", None)
    workspace = getattr(request.state, "workspace", None)

    if not workspace:
        workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
        if not workspace:
            raise HTTPException(status_code=404, detail="Workspace not found")

    if not app:
        app = db.query(App).filter(App.slug == "trapmaster-pro").first()
        if not app:
            raise HTTPException(status_code=404, detail="TrapMaster Pro app not found")

    exports = ExportService.list_exports(db, app, workspace, project_id=project_id)
    return [ExportResponse(**e.__dict__) for e in exports]


@router.get("/exports/{export_id}", response_model=ExportResponse)
async def get_export(
    export_id: str,
    request: Request,
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Get an export by ID."""
    app = getattr(request.state, "app", None)
    workspace = getattr(request.state, "workspace", None)

    if not workspace:
        workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
        if not workspace:
            raise HTTPException(status_code=404, detail="Workspace not found")

    if not app:
        app = db.query(App).filter(App.slug == "trapmaster-pro").first()
        if not app:
            raise HTTPException(status_code=404, detail="TrapMaster Pro app not found")

    export = ExportService.get_export(db, app, workspace, export_id)
    return ExportResponse(**export.__dict__)
