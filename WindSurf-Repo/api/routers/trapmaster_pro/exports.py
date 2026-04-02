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
    db: Session = Depends(get_db),
):
    """List exports, optionally filtered by project."""
    app: App = request.state.app
    workspace: Workspace = request.state.workspace

    exports = ExportService.list_exports(db, app, workspace, project_id=project_id)
    return [ExportResponse(**export.__dict__) for export in exports]


@router.get("/exports/{export_id}", response_model=ExportResponse)
async def get_export(
    export_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """Get an export by ID."""
    app: App = request.state.app
    workspace: Workspace = request.state.workspace

    export = ExportService.get_export(db, app, workspace, export_id)
    return ExportResponse(**export.__dict__)
