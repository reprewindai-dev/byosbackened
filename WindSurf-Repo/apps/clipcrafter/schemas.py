"""ClipCrafter Pydantic schemas."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal


# Project Schemas
class ProjectCreate(BaseModel):
    """Schema for creating a project."""

    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    aspect_ratio: Optional[str] = Field(None, pattern="^(16:9|9:16|1:1|4:5)$")
    resolution: Optional[str] = None
    frame_rate: Optional[int] = Field(None, ge=1, le=120)


class ProjectUpdate(BaseModel):
    """Schema for updating a project."""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    aspect_ratio: Optional[str] = Field(None, pattern="^(16:9|9:16|1:1|4:5)$")
    resolution: Optional[str] = None
    frame_rate: Optional[int] = Field(None, ge=1, le=120)
    duration: Optional[Decimal] = None


class ProjectResponse(BaseModel):
    """Schema for project response."""

    id: str
    app_id: str
    workspace_id: str
    name: str
    description: Optional[str] = None
    aspect_ratio: Optional[str] = None
    resolution: Optional[str] = None
    frame_rate: Optional[int] = None
    duration: Optional[Decimal] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    clips_count: Optional[int] = 0
    templates_count: Optional[int] = 0
    renders_count: Optional[int] = 0

    class Config:
        from_attributes = True


# Clip Schemas
class ClipCreate(BaseModel):
    """Schema for creating a clip."""

    name: str = Field(..., min_length=1, max_length=200)
    clip_type: str = Field(..., pattern="^(video|image|text|audio|transition)$")
    file_path: Optional[str] = None
    start_time: Optional[Decimal] = Field(None, ge=0)
    end_time: Optional[Decimal] = Field(None, ge=0)
    position_x: Optional[int] = None
    position_y: Optional[int] = None
    width: Optional[int] = Field(None, ge=1)
    height: Optional[int] = Field(None, ge=1)
    opacity: Optional[Decimal] = Field(100.0, ge=0, le=100)
    volume: Optional[Decimal] = Field(100.0, ge=0, le=100)
    effects: Optional[List[Dict[str, Any]]] = None
    transitions: Optional[List[Dict[str, Any]]] = None
    order: Optional[int] = Field(0, ge=0)


class ClipUpdate(BaseModel):
    """Schema for updating a clip."""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    start_time: Optional[Decimal] = Field(None, ge=0)
    end_time: Optional[Decimal] = Field(None, ge=0)
    position_x: Optional[int] = None
    position_y: Optional[int] = None
    width: Optional[int] = Field(None, ge=1)
    height: Optional[int] = Field(None, ge=1)
    opacity: Optional[Decimal] = Field(None, ge=0, le=100)
    volume: Optional[Decimal] = Field(None, ge=0, le=100)
    effects: Optional[List[Dict[str, Any]]] = None
    transitions: Optional[List[Dict[str, Any]]] = None
    order: Optional[int] = Field(None, ge=0)


class ClipResponse(BaseModel):
    """Schema for clip response."""

    id: str
    app_id: str
    workspace_id: str
    project_id: str
    name: str
    clip_type: str
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    duration: Optional[Decimal] = None
    start_time: Optional[Decimal] = None
    end_time: Optional[Decimal] = None
    position_x: Optional[int] = None
    position_y: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    opacity: Decimal
    volume: Decimal
    effects: Optional[List[Dict[str, Any]]] = None
    transitions: Optional[List[Dict[str, Any]]] = None
    order: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Template Schemas
class TemplateCreate(BaseModel):
    """Schema for creating a template."""

    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    category: Optional[str] = None
    thumbnail_path: Optional[str] = None
    template_data: Dict[str, Any] = Field(..., description="JSON structure defining the template")
    aspect_ratio: Optional[str] = Field(None, pattern="^(16:9|9:16|1:1|4:5)$")
    duration: Optional[Decimal] = Field(None, ge=0)
    is_public: Optional[bool] = False


class TemplateUpdate(BaseModel):
    """Schema for updating a template."""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    category: Optional[str] = None
    thumbnail_path: Optional[str] = None
    template_data: Optional[Dict[str, Any]] = None
    aspect_ratio: Optional[str] = Field(None, pattern="^(16:9|9:16|1:1|4:5)$")
    duration: Optional[Decimal] = Field(None, ge=0)
    is_favorite: Optional[bool] = None


class TemplateResponse(BaseModel):
    """Schema for template response."""

    id: str
    app_id: str
    workspace_id: str
    project_id: Optional[str] = None
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    thumbnail_path: Optional[str] = None
    template_data: Dict[str, Any]
    aspect_ratio: Optional[str] = None
    duration: Optional[Decimal] = None
    is_public: bool
    is_favorite: bool
    usage_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Render Schemas
class RenderCreate(BaseModel):
    """Schema for creating a render."""

    name: str = Field(..., min_length=1, max_length=200)
    format: str = Field(..., pattern="^(mp4|mov|webm|gif)$")
    resolution: str = Field(..., pattern="^(1080p|720p|4K|480p)$")
    frame_rate: Optional[int] = Field(None, ge=1, le=120)
    quality: Optional[str] = Field(None, pattern="^(low|medium|high|ultra)$")
    render_settings: Optional[Dict[str, Any]] = None


class RenderResponse(BaseModel):
    """Schema for render response."""

    id: str
    app_id: str
    workspace_id: str
    project_id: str
    name: str
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    format: str
    resolution: str
    frame_rate: Optional[int] = None
    quality: Optional[str] = None
    status: str
    progress: int
    error_message: Optional[str] = None
    render_settings: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True
