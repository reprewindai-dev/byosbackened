"""TrapMaster Pro samples endpoints."""

from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.orm import Session
from db.session import get_db
from db.models.app import App
from db.models.workspace import Workspace
from apps.trapmaster_pro.schemas import (
    SampleCreate,
    SampleUpdate,
    SampleResponse,
)
from apps.trapmaster_pro.services import SampleService
from typing import List, Optional

router = APIRouter(prefix="/trapmaster-pro", tags=["TrapMaster Pro"])


@router.post("/samples", response_model=SampleResponse, status_code=status.HTTP_201_CREATED)
async def create_sample(
    sample_data: SampleCreate,
    request: Request,
    project_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Create a new sample."""
    app: App = request.state.app
    workspace: Workspace = request.state.workspace

    sample = SampleService.create_sample(db, app, workspace, sample_data, project_id=project_id)
    return SampleResponse(**sample.__dict__)


@router.get("/samples", response_model=List[SampleResponse])
async def list_samples(
    request: Request,
    project_id: Optional[str] = None,
    category: Optional[str] = None,
    is_favorite: Optional[bool] = None,
    db: Session = Depends(get_db),
):
    """List samples with optional filters."""
    app: App = request.state.app
    workspace: Workspace = request.state.workspace

    samples = SampleService.list_samples(
        db,
        app,
        workspace,
        project_id=project_id,
        category=category,
        is_favorite=is_favorite,
    )
    return [SampleResponse(**sample.__dict__) for sample in samples]


@router.get("/samples/{sample_id}", response_model=SampleResponse)
async def get_sample(
    sample_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """Get a sample by ID."""
    app: App = request.state.app
    workspace: Workspace = request.state.workspace

    sample = SampleService.get_sample(db, app, workspace, sample_id)
    return SampleResponse(**sample.__dict__)


@router.put("/samples/{sample_id}", response_model=SampleResponse)
async def update_sample(
    sample_id: str,
    sample_data: SampleUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    """Update a sample."""
    app: App = request.state.app
    workspace: Workspace = request.state.workspace

    sample = SampleService.update_sample(db, app, workspace, sample_id, sample_data)
    return SampleResponse(**sample.__dict__)


@router.delete("/samples/{sample_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sample(
    sample_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """Delete a sample."""
    app: App = request.state.app
    workspace: Workspace = request.state.workspace

    SampleService.delete_sample(db, app, workspace, sample_id)
    return None
