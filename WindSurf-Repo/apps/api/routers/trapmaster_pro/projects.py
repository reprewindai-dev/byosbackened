"""TrapMaster Pro projects endpoints."""

from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.orm import Session
from db.session import get_db
from db.models.app import App
from db.models.workspace import Workspace
from apps.trapmaster_pro.schemas import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
)
from apps.trapmaster_pro.services import ProjectService
from apps.api.deps import get_current_workspace_id
from typing import List

router = APIRouter(prefix="/trapmaster-pro", tags=["TrapMaster Pro"])


@router.post("/projects", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    """Create a new TrapMaster Pro project."""
    app: App = request.state.app
    workspace: Workspace = request.state.workspace

    project = ProjectService.create_project(db, app, workspace, project_data)

    # Get counts for response
    from apps.trapmaster_pro.models import TrapMasterTrack, TrapMasterSample, TrapMasterExport
    from sqlalchemy import func

    tracks_count = (
        db.query(func.count(TrapMasterTrack.id))
        .filter(TrapMasterTrack.project_id == project.id)
        .scalar()
        or 0
    )

    samples_count = (
        db.query(func.count(TrapMasterSample.id))
        .filter(TrapMasterSample.project_id == project.id)
        .scalar()
        or 0
    )

    exports_count = (
        db.query(func.count(TrapMasterExport.id))
        .filter(TrapMasterExport.project_id == project.id)
        .scalar()
        or 0
    )

    return ProjectResponse(
        **project.__dict__,
        tracks_count=tracks_count,
        samples_count=samples_count,
        exports_count=exports_count,
    )


@router.get("/projects", response_model=List[ProjectResponse])
async def list_projects(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """List all TrapMaster Pro projects."""
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

    projects = ProjectService.list_projects(db, app, workspace, skip=skip, limit=limit)

    # Get counts for each project
    from apps.trapmaster_pro.models import TrapMasterTrack, TrapMasterSample, TrapMasterExport
    from sqlalchemy import func

    result = []
    for project in projects:
        tracks_count = (
            db.query(func.count(TrapMasterTrack.id))
            .filter(TrapMasterTrack.project_id == project.id)
            .scalar()
            or 0
        )

        samples_count = (
            db.query(func.count(TrapMasterSample.id))
            .filter(TrapMasterSample.project_id == project.id)
            .scalar()
            or 0
        )

        exports_count = (
            db.query(func.count(TrapMasterExport.id))
            .filter(TrapMasterExport.project_id == project.id)
            .scalar()
            or 0
        )

        result.append(
            ProjectResponse(
                **project.__dict__,
                tracks_count=tracks_count,
                samples_count=samples_count,
                exports_count=exports_count,
            )
        )

    return result


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """Get a TrapMaster Pro project by ID."""
    app: App = request.state.app
    workspace: Workspace = request.state.workspace

    project = ProjectService.get_project(db, app, workspace, project_id)

    # Get counts
    from apps.trapmaster_pro.models import TrapMasterTrack, TrapMasterSample, TrapMasterExport
    from sqlalchemy import func

    tracks_count = (
        db.query(func.count(TrapMasterTrack.id))
        .filter(TrapMasterTrack.project_id == project.id)
        .scalar()
        or 0
    )

    samples_count = (
        db.query(func.count(TrapMasterSample.id))
        .filter(TrapMasterSample.project_id == project.id)
        .scalar()
        or 0
    )

    exports_count = (
        db.query(func.count(TrapMasterExport.id))
        .filter(TrapMasterExport.project_id == project.id)
        .scalar()
        or 0
    )

    return ProjectResponse(
        **project.__dict__,
        tracks_count=tracks_count,
        samples_count=samples_count,
        exports_count=exports_count,
    )


@router.put("/projects/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    project_data: ProjectUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    """Update a TrapMaster Pro project."""
    app: App = request.state.app
    workspace: Workspace = request.state.workspace

    project = ProjectService.update_project(db, app, workspace, project_id, project_data)

    # Get counts
    from apps.trapmaster_pro.models import TrapMasterTrack, TrapMasterSample, TrapMasterExport
    from sqlalchemy import func

    tracks_count = (
        db.query(func.count(TrapMasterTrack.id))
        .filter(TrapMasterTrack.project_id == project.id)
        .scalar()
        or 0
    )

    samples_count = (
        db.query(func.count(TrapMasterSample.id))
        .filter(TrapMasterSample.project_id == project.id)
        .scalar()
        or 0
    )

    exports_count = (
        db.query(func.count(TrapMasterExport.id))
        .filter(TrapMasterExport.project_id == project.id)
        .scalar()
        or 0
    )

    return ProjectResponse(
        **project.__dict__,
        tracks_count=tracks_count,
        samples_count=samples_count,
        exports_count=exports_count,
    )


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """Delete a TrapMaster Pro project."""
    app: App = request.state.app
    workspace: Workspace = request.state.workspace

    ProjectService.delete_project(db, app, workspace, project_id)
    return None
