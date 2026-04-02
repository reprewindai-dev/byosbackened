"""TrapMaster Pro business logic services."""

from sqlalchemy.orm import Session
from sqlalchemy import func
from db.models.app import App
from db.models.workspace import Workspace
from apps.trapmaster_pro.models import (
    TrapMasterProject,
    TrapMasterTrack,
    TrapMasterSample,
    TrapMasterExport,
)
from apps.trapmaster_pro.schemas import (
    ProjectCreate,
    ProjectUpdate,
    TrackCreate,
    TrackUpdate,
    SampleCreate,
    SampleUpdate,
    ExportCreate,
)
from fastapi import HTTPException, status
from typing import List, Optional


class ProjectService:
    """Service for project operations."""

    @staticmethod
    def create_project(
        db: Session,
        app: App,
        workspace: Workspace,
        project_data: ProjectCreate,
    ) -> TrapMasterProject:
        """Create a new project."""
        project = TrapMasterProject(
            app_id=app.id,
            workspace_id=workspace.id,
            name=project_data.name,
            description=project_data.description,
            bpm=project_data.bpm,
            key=project_data.key,
            time_signature=project_data.time_signature,
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        return project

    @staticmethod
    def get_project(
        db: Session,
        app: App,
        workspace: Workspace,
        project_id: str,
    ) -> TrapMasterProject:
        """Get a project by ID."""
        project = (
            db.query(TrapMasterProject)
            .filter(
                TrapMasterProject.id == project_id,
                TrapMasterProject.app_id == app.id,
                TrapMasterProject.workspace_id == workspace.id,
            )
            .first()
        )

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project '{project_id}' not found",
            )
        return project

    @staticmethod
    def list_projects(
        db: Session,
        app: App,
        workspace: Workspace,
        skip: int = 0,
        limit: int = 100,
    ) -> List[TrapMasterProject]:
        """List all projects for workspace."""
        return (
            db.query(TrapMasterProject)
            .filter(
                TrapMasterProject.app_id == app.id,
                TrapMasterProject.workspace_id == workspace.id,
                TrapMasterProject.is_active == True,
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def update_project(
        db: Session,
        app: App,
        workspace: Workspace,
        project_id: str,
        project_data: ProjectUpdate,
    ) -> TrapMasterProject:
        """Update a project."""
        project = ProjectService.get_project(db, app, workspace, project_id)

        update_data = project_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(project, field, value)

        db.commit()
        db.refresh(project)
        return project

    @staticmethod
    def delete_project(
        db: Session,
        app: App,
        workspace: Workspace,
        project_id: str,
    ) -> None:
        """Delete a project (soft delete by setting is_active=False)."""
        project = ProjectService.get_project(db, app, workspace, project_id)
        project.is_active = False
        db.commit()


class TrackService:
    """Service for track operations."""

    @staticmethod
    def create_track(
        db: Session,
        app: App,
        workspace: Workspace,
        project_id: str,
        track_data: TrackCreate,
    ) -> TrapMasterTrack:
        """Create a new track."""
        # Verify project exists and belongs to workspace
        project = ProjectService.get_project(db, app, workspace, project_id)

        track = TrapMasterTrack(
            app_id=app.id,
            workspace_id=workspace.id,
            project_id=project_id,
            name=track_data.name,
            track_type=track_data.track_type,
            file_path=track_data.file_path,
            volume=track_data.volume or 100.0,
            pan=track_data.pan or 0.0,
            is_muted=track_data.is_muted or False,
            is_solo=track_data.is_solo or False,
            order=track_data.order or 0,
        )
        db.add(track)
        db.commit()
        db.refresh(track)
        return track

    @staticmethod
    def get_track(
        db: Session,
        app: App,
        workspace: Workspace,
        track_id: str,
    ) -> TrapMasterTrack:
        """Get a track by ID."""
        track = (
            db.query(TrapMasterTrack)
            .filter(
                TrapMasterTrack.id == track_id,
                TrapMasterTrack.app_id == app.id,
                TrapMasterTrack.workspace_id == workspace.id,
            )
            .first()
        )

        if not track:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Track '{track_id}' not found",
            )
        return track

    @staticmethod
    def list_tracks(
        db: Session,
        app: App,
        workspace: Workspace,
        project_id: Optional[str] = None,
    ) -> List[TrapMasterTrack]:
        """List tracks, optionally filtered by project."""
        query = db.query(TrapMasterTrack).filter(
            TrapMasterTrack.app_id == app.id,
            TrapMasterTrack.workspace_id == workspace.id,
        )

        if project_id:
            query = query.filter(TrapMasterTrack.project_id == project_id)

        return query.order_by(TrapMasterTrack.order).all()

    @staticmethod
    def update_track(
        db: Session,
        app: App,
        workspace: Workspace,
        track_id: str,
        track_data: TrackUpdate,
    ) -> TrapMasterTrack:
        """Update a track."""
        track = TrackService.get_track(db, app, workspace, track_id)

        update_data = track_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(track, field, value)

        db.commit()
        db.refresh(track)
        return track

    @staticmethod
    def delete_track(
        db: Session,
        app: App,
        workspace: Workspace,
        track_id: str,
    ) -> None:
        """Delete a track."""
        track = TrackService.get_track(db, app, workspace, track_id)
        db.delete(track)
        db.commit()


class SampleService:
    """Service for sample operations."""

    @staticmethod
    def create_sample(
        db: Session,
        app: App,
        workspace: Workspace,
        sample_data: SampleCreate,
        project_id: Optional[str] = None,
    ) -> TrapMasterSample:
        """Create a new sample."""
        # Verify project exists if project_id provided
        if project_id:
            ProjectService.get_project(db, app, workspace, project_id)

        sample = TrapMasterSample(
            app_id=app.id,
            workspace_id=workspace.id,
            project_id=project_id,
            name=sample_data.name,
            category=sample_data.category,
            file_path=sample_data.file_path,
            bpm=sample_data.bpm,
            key=sample_data.key,
            tags=sample_data.tags,
            is_favorite=sample_data.is_favorite or False,
        )
        db.add(sample)
        db.commit()
        db.refresh(sample)
        return sample

    @staticmethod
    def get_sample(
        db: Session,
        app: App,
        workspace: Workspace,
        sample_id: str,
    ) -> TrapMasterSample:
        """Get a sample by ID."""
        sample = (
            db.query(TrapMasterSample)
            .filter(
                TrapMasterSample.id == sample_id,
                TrapMasterSample.app_id == app.id,
                TrapMasterSample.workspace_id == workspace.id,
            )
            .first()
        )

        if not sample:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sample '{sample_id}' not found",
            )
        return sample

    @staticmethod
    def list_samples(
        db: Session,
        app: App,
        workspace: Workspace,
        project_id: Optional[str] = None,
        category: Optional[str] = None,
        is_favorite: Optional[bool] = None,
    ) -> List[TrapMasterSample]:
        """List samples with optional filters."""
        query = db.query(TrapMasterSample).filter(
            TrapMasterSample.app_id == app.id,
            TrapMasterSample.workspace_id == workspace.id,
        )

        if project_id:
            query = query.filter(TrapMasterSample.project_id == project_id)
        if category:
            query = query.filter(TrapMasterSample.category == category)
        if is_favorite is not None:
            query = query.filter(TrapMasterSample.is_favorite == is_favorite)

        return query.order_by(TrapMasterSample.created_at.desc()).all()

    @staticmethod
    def update_sample(
        db: Session,
        app: App,
        workspace: Workspace,
        sample_id: str,
        sample_data: SampleUpdate,
    ) -> TrapMasterSample:
        """Update a sample."""
        sample = SampleService.get_sample(db, app, workspace, sample_id)

        update_data = sample_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(sample, field, value)

        db.commit()
        db.refresh(sample)
        return sample

    @staticmethod
    def delete_sample(
        db: Session,
        app: App,
        workspace: Workspace,
        sample_id: str,
    ) -> None:
        """Delete a sample."""
        sample = SampleService.get_sample(db, app, workspace, sample_id)
        db.delete(sample)
        db.commit()


class ExportService:
    """Service for export operations."""

    @staticmethod
    def create_export(
        db: Session,
        app: App,
        workspace: Workspace,
        project_id: str,
        export_data: ExportCreate,
    ) -> TrapMasterExport:
        """Create a new export job."""
        # Verify project exists
        ProjectService.get_project(db, app, workspace, project_id)

        export = TrapMasterExport(
            app_id=app.id,
            workspace_id=workspace.id,
            project_id=project_id,
            name=export_data.name,
            format=export_data.format,
            quality=export_data.quality or "high",
            status="pending",
        )
        db.add(export)
        db.commit()
        db.refresh(export)
        return export

    @staticmethod
    def get_export(
        db: Session,
        app: App,
        workspace: Workspace,
        export_id: str,
    ) -> TrapMasterExport:
        """Get an export by ID."""
        export = (
            db.query(TrapMasterExport)
            .filter(
                TrapMasterExport.id == export_id,
                TrapMasterExport.app_id == app.id,
                TrapMasterExport.workspace_id == workspace.id,
            )
            .first()
        )

        if not export:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Export '{export_id}' not found",
            )
        return export

    @staticmethod
    def list_exports(
        db: Session,
        app: App,
        workspace: Workspace,
        project_id: Optional[str] = None,
    ) -> List[TrapMasterExport]:
        """List exports, optionally filtered by project."""
        query = db.query(TrapMasterExport).filter(
            TrapMasterExport.app_id == app.id,
            TrapMasterExport.workspace_id == workspace.id,
        )

        if project_id:
            query = query.filter(TrapMasterExport.project_id == project_id)

        return query.order_by(TrapMasterExport.created_at.desc()).all()
