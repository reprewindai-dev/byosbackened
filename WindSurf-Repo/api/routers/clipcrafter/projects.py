"""ClipCrafter projects endpoints."""

from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.orm import Session
from db.session import get_db
from db.models.app import App
from db.models.workspace import Workspace
from apps.clipcrafter.schemas import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
)
from apps.clipcrafter.services import ProjectService
from typing import List

router = APIRouter(prefix="/clipcrafter", tags=["ClipCrafter"])


@router.post("/projects", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    """Create a new ClipCrafter project."""
    app: App = request.state.app
    workspace: Workspace = request.state.workspace

    project = ProjectService.create_project(db, app, workspace, project_data)

    # Get counts for response
    from apps.clipcrafter.models import ClipCrafterClip, ClipCrafterTemplate, ClipCrafterRender
    from sqlalchemy import func

    clips_count = (
        db.query(func.count(ClipCrafterClip.id))
        .filter(ClipCrafterClip.project_id == project.id)
        .scalar()
        or 0
    )

    templates_count = (
        db.query(func.count(ClipCrafterTemplate.id))
        .filter(ClipCrafterTemplate.project_id == project.id)
        .scalar()
        or 0
    )

    renders_count = (
        db.query(func.count(ClipCrafterRender.id))
        .filter(ClipCrafterRender.project_id == project.id)
        .scalar()
        or 0
    )

    return ProjectResponse(
        **project.__dict__,
        clips_count=clips_count,
        templates_count=templates_count,
        renders_count=renders_count,
    )


@router.get("/projects", response_model=List[ProjectResponse])
async def list_projects(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """List all ClipCrafter projects."""
    app: App = request.state.app
    workspace: Workspace = request.state.workspace

    projects = ProjectService.list_projects(db, app, workspace, skip=skip, limit=limit)

    # Get counts for each project
    from apps.clipcrafter.models import ClipCrafterClip, ClipCrafterTemplate, ClipCrafterRender
    from sqlalchemy import func

    result = []
    for project in projects:
        clips_count = (
            db.query(func.count(ClipCrafterClip.id))
            .filter(ClipCrafterClip.project_id == project.id)
            .scalar()
            or 0
        )

        templates_count = (
            db.query(func.count(ClipCrafterTemplate.id))
            .filter(ClipCrafterTemplate.project_id == project.id)
            .scalar()
            or 0
        )

        renders_count = (
            db.query(func.count(ClipCrafterRender.id))
            .filter(ClipCrafterRender.project_id == project.id)
            .scalar()
            or 0
        )

        result.append(
            ProjectResponse(
                **project.__dict__,
                clips_count=clips_count,
                templates_count=templates_count,
                renders_count=renders_count,
            )
        )

    return result


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """Get a ClipCrafter project by ID."""
    app: App = request.state.app
    workspace: Workspace = request.state.workspace

    project = ProjectService.get_project(db, app, workspace, project_id)

    # Get counts
    from apps.clipcrafter.models import ClipCrafterClip, ClipCrafterTemplate, ClipCrafterRender
    from sqlalchemy import func

    clips_count = (
        db.query(func.count(ClipCrafterClip.id))
        .filter(ClipCrafterClip.project_id == project.id)
        .scalar()
        or 0
    )

    templates_count = (
        db.query(func.count(ClipCrafterTemplate.id))
        .filter(ClipCrafterTemplate.project_id == project.id)
        .scalar()
        or 0
    )

    renders_count = (
        db.query(func.count(ClipCrafterRender.id))
        .filter(ClipCrafterRender.project_id == project.id)
        .scalar()
        or 0
    )

    return ProjectResponse(
        **project.__dict__,
        clips_count=clips_count,
        templates_count=templates_count,
        renders_count=renders_count,
    )


@router.put("/projects/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    project_data: ProjectUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    """Update a ClipCrafter project."""
    app: App = request.state.app
    workspace: Workspace = request.state.workspace

    project = ProjectService.update_project(db, app, workspace, project_id, project_data)

    # Get counts
    from apps.clipcrafter.models import ClipCrafterClip, ClipCrafterTemplate, ClipCrafterRender
    from sqlalchemy import func

    clips_count = (
        db.query(func.count(ClipCrafterClip.id))
        .filter(ClipCrafterClip.project_id == project.id)
        .scalar()
        or 0
    )

    templates_count = (
        db.query(func.count(ClipCrafterTemplate.id))
        .filter(ClipCrafterTemplate.project_id == project.id)
        .scalar()
        or 0
    )

    renders_count = (
        db.query(func.count(ClipCrafterRender.id))
        .filter(ClipCrafterRender.project_id == project.id)
        .scalar()
        or 0
    )

    return ProjectResponse(
        **project.__dict__,
        clips_count=clips_count,
        templates_count=templates_count,
        renders_count=renders_count,
    )


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """Delete a ClipCrafter project."""
    app: App = request.state.app
    workspace: Workspace = request.state.workspace

    ProjectService.delete_project(db, app, workspace, project_id)
    return None
