"""ClipCrafter business logic services."""

from sqlalchemy.orm import Session
from sqlalchemy import func
from db.models.app import App
from db.models.workspace import Workspace
from apps.clipcrafter.models import (
    ClipCrafterProject,
    ClipCrafterClip,
    ClipCrafterTemplate,
    ClipCrafterRender,
)
from apps.clipcrafter.schemas import (
    ProjectCreate,
    ProjectUpdate,
    ClipCreate,
    ClipUpdate,
    TemplateCreate,
    TemplateUpdate,
    RenderCreate,
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
    ) -> ClipCrafterProject:
        """Create a new project."""
        project = ClipCrafterProject(
            app_id=app.id,
            workspace_id=workspace.id,
            name=project_data.name,
            description=project_data.description,
            aspect_ratio=project_data.aspect_ratio,
            resolution=project_data.resolution,
            frame_rate=project_data.frame_rate,
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
    ) -> ClipCrafterProject:
        """Get a project by ID."""
        project = (
            db.query(ClipCrafterProject)
            .filter(
                ClipCrafterProject.id == project_id,
                ClipCrafterProject.app_id == app.id,
                ClipCrafterProject.workspace_id == workspace.id,
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
    ) -> List[ClipCrafterProject]:
        """List all projects for workspace."""
        return (
            db.query(ClipCrafterProject)
            .filter(
                ClipCrafterProject.app_id == app.id,
                ClipCrafterProject.workspace_id == workspace.id,
                ClipCrafterProject.is_active == True,
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
    ) -> ClipCrafterProject:
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


class ClipService:
    """Service for clip operations."""

    @staticmethod
    def create_clip(
        db: Session,
        app: App,
        workspace: Workspace,
        project_id: str,
        clip_data: ClipCreate,
    ) -> ClipCrafterClip:
        """Create a new clip."""
        # Verify project exists and belongs to workspace
        project = ProjectService.get_project(db, app, workspace, project_id)

        clip = ClipCrafterClip(
            app_id=app.id,
            workspace_id=workspace.id,
            project_id=project_id,
            name=clip_data.name,
            clip_type=clip_data.clip_type,
            file_path=clip_data.file_path,
            start_time=clip_data.start_time,
            end_time=clip_data.end_time,
            position_x=clip_data.position_x,
            position_y=clip_data.position_y,
            width=clip_data.width,
            height=clip_data.height,
            opacity=clip_data.opacity or 100.0,
            volume=clip_data.volume or 100.0,
            effects=clip_data.effects,
            transitions=clip_data.transitions,
            order=clip_data.order or 0,
        )
        db.add(clip)
        db.commit()
        db.refresh(clip)
        return clip

    @staticmethod
    def get_clip(
        db: Session,
        app: App,
        workspace: Workspace,
        clip_id: str,
    ) -> ClipCrafterClip:
        """Get a clip by ID."""
        clip = (
            db.query(ClipCrafterClip)
            .filter(
                ClipCrafterClip.id == clip_id,
                ClipCrafterClip.app_id == app.id,
                ClipCrafterClip.workspace_id == workspace.id,
            )
            .first()
        )

        if not clip:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Clip '{clip_id}' not found",
            )
        return clip

    @staticmethod
    def list_clips(
        db: Session,
        app: App,
        workspace: Workspace,
        project_id: Optional[str] = None,
        clip_type: Optional[str] = None,
    ) -> List[ClipCrafterClip]:
        """List clips, optionally filtered by project and type."""
        query = db.query(ClipCrafterClip).filter(
            ClipCrafterClip.app_id == app.id,
            ClipCrafterClip.workspace_id == workspace.id,
        )

        if project_id:
            query = query.filter(ClipCrafterClip.project_id == project_id)
        if clip_type:
            query = query.filter(ClipCrafterClip.clip_type == clip_type)

        return query.order_by(ClipCrafterClip.order).all()

    @staticmethod
    def update_clip(
        db: Session,
        app: App,
        workspace: Workspace,
        clip_id: str,
        clip_data: ClipUpdate,
    ) -> ClipCrafterClip:
        """Update a clip."""
        clip = ClipService.get_clip(db, app, workspace, clip_id)

        update_data = clip_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(clip, field, value)

        db.commit()
        db.refresh(clip)
        return clip

    @staticmethod
    def delete_clip(
        db: Session,
        app: App,
        workspace: Workspace,
        clip_id: str,
    ) -> None:
        """Delete a clip."""
        clip = ClipService.get_clip(db, app, workspace, clip_id)
        db.delete(clip)
        db.commit()


class TemplateService:
    """Service for template operations."""

    @staticmethod
    def create_template(
        db: Session,
        app: App,
        workspace: Workspace,
        template_data: TemplateCreate,
        project_id: Optional[str] = None,
    ) -> ClipCrafterTemplate:
        """Create a new template."""
        # Verify project exists if project_id provided
        if project_id:
            ProjectService.get_project(db, app, workspace, project_id)

        template = ClipCrafterTemplate(
            app_id=app.id,
            workspace_id=workspace.id,
            project_id=project_id,
            name=template_data.name,
            description=template_data.description,
            category=template_data.category,
            thumbnail_path=template_data.thumbnail_path,
            template_data=template_data.template_data,
            aspect_ratio=template_data.aspect_ratio,
            duration=template_data.duration,
            is_public=template_data.is_public or False,
        )
        db.add(template)
        db.commit()
        db.refresh(template)
        return template

    @staticmethod
    def get_template(
        db: Session,
        app: App,
        workspace: Workspace,
        template_id: str,
    ) -> ClipCrafterTemplate:
        """Get a template by ID."""
        template = (
            db.query(ClipCrafterTemplate)
            .filter(
                ClipCrafterTemplate.id == template_id,
                ClipCrafterTemplate.app_id == app.id,
                # Allow access if public or belongs to workspace
                (
                    (ClipCrafterTemplate.workspace_id == workspace.id)
                    | (ClipCrafterTemplate.is_public == True)
                ),
            )
            .first()
        )

        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template '{template_id}' not found",
            )
        return template

    @staticmethod
    def list_templates(
        db: Session,
        app: App,
        workspace: Workspace,
        project_id: Optional[str] = None,
        category: Optional[str] = None,
        is_favorite: Optional[bool] = None,
        include_public: bool = True,
    ) -> List[ClipCrafterTemplate]:
        """List templates with optional filters."""
        query = db.query(ClipCrafterTemplate).filter(
            ClipCrafterTemplate.app_id == app.id,
        )

        # Filter by workspace or public templates
        if include_public:
            query = query.filter(
                (ClipCrafterTemplate.workspace_id == workspace.id)
                | (ClipCrafterTemplate.is_public == True)
            )
        else:
            query = query.filter(ClipCrafterTemplate.workspace_id == workspace.id)

        if project_id:
            query = query.filter(ClipCrafterTemplate.project_id == project_id)
        if category:
            query = query.filter(ClipCrafterTemplate.category == category)
        if is_favorite is not None:
            query = query.filter(ClipCrafterTemplate.is_favorite == is_favorite)

        return query.order_by(ClipCrafterTemplate.created_at.desc()).all()

    @staticmethod
    def update_template(
        db: Session,
        app: App,
        workspace: Workspace,
        template_id: str,
        template_data: TemplateUpdate,
    ) -> ClipCrafterTemplate:
        """Update a template."""
        template = TemplateService.get_template(db, app, workspace, template_id)

        # Only workspace owner can update
        if template.workspace_id != workspace.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot update templates from other workspaces",
            )

        update_data = template_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(template, field, value)

        db.commit()
        db.refresh(template)
        return template

    @staticmethod
    def delete_template(
        db: Session,
        app: App,
        workspace: Workspace,
        template_id: str,
    ) -> None:
        """Delete a template."""
        template = TemplateService.get_template(db, app, workspace, template_id)

        # Only workspace owner can delete
        if template.workspace_id != workspace.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot delete templates from other workspaces",
            )

        db.delete(template)
        db.commit()

    @staticmethod
    def increment_usage(
        db: Session,
        template_id: str,
    ) -> None:
        """Increment template usage count."""
        template = (
            db.query(ClipCrafterTemplate).filter(ClipCrafterTemplate.id == template_id).first()
        )

        if template:
            template.usage_count += 1
            db.commit()


class RenderService:
    """Service for render operations."""

    @staticmethod
    def create_render(
        db: Session,
        app: App,
        workspace: Workspace,
        project_id: str,
        render_data: RenderCreate,
    ) -> ClipCrafterRender:
        """Create a new render job."""
        # Verify project exists
        ProjectService.get_project(db, app, workspace, project_id)

        render = ClipCrafterRender(
            app_id=app.id,
            workspace_id=workspace.id,
            project_id=project_id,
            name=render_data.name,
            format=render_data.format,
            resolution=render_data.resolution,
            frame_rate=render_data.frame_rate,
            quality=render_data.quality or "high",
            render_settings=render_data.render_settings,
            status="pending",
            progress=0,
        )
        db.add(render)
        db.commit()
        db.refresh(render)
        return render

    @staticmethod
    def get_render(
        db: Session,
        app: App,
        workspace: Workspace,
        render_id: str,
    ) -> ClipCrafterRender:
        """Get a render by ID."""
        render = (
            db.query(ClipCrafterRender)
            .filter(
                ClipCrafterRender.id == render_id,
                ClipCrafterRender.app_id == app.id,
                ClipCrafterRender.workspace_id == workspace.id,
            )
            .first()
        )

        if not render:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Render '{render_id}' not found",
            )
        return render

    @staticmethod
    def list_renders(
        db: Session,
        app: App,
        workspace: Workspace,
        project_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[ClipCrafterRender]:
        """List renders, optionally filtered by project and status."""
        query = db.query(ClipCrafterRender).filter(
            ClipCrafterRender.app_id == app.id,
            ClipCrafterRender.workspace_id == workspace.id,
        )

        if project_id:
            query = query.filter(ClipCrafterRender.project_id == project_id)
        if status:
            query = query.filter(ClipCrafterRender.status == status)

        return query.order_by(ClipCrafterRender.created_at.desc()).all()

    @staticmethod
    def update_render_status(
        db: Session,
        app: App,
        workspace: Workspace,
        render_id: str,
        status: str,
        progress: Optional[int] = None,
        file_path: Optional[str] = None,
        file_size: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> ClipCrafterRender:
        """Update render status and progress."""
        render = RenderService.get_render(db, app, workspace, render_id)

        render.status = status
        if progress is not None:
            render.progress = progress
        if file_path:
            render.file_path = file_path
        if file_size:
            render.file_size = file_size
        if error_message:
            render.error_message = error_message

        if status == "completed":
            from datetime import datetime

            render.completed_at = datetime.utcnow()

        db.commit()
        db.refresh(render)
        return render
