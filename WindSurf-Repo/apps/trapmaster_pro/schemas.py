"""TrapMaster Pro Pydantic schemas."""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


# Project Schemas
class ProjectCreate(BaseModel):
    """Schema for creating a project."""

    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    bpm: Optional[int] = Field(None, ge=1, le=300)
    key: Optional[str] = None
    time_signature: Optional[str] = None


class ProjectUpdate(BaseModel):
    """Schema for updating a project."""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    bpm: Optional[int] = Field(None, ge=1, le=300)
    key: Optional[str] = None
    time_signature: Optional[str] = None


class ProjectResponse(BaseModel):
    """Schema for project response."""

    id: str
    app_id: str
    workspace_id: str
    name: str
    description: Optional[str] = None
    bpm: Optional[int] = None
    key: Optional[str] = None
    time_signature: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    tracks_count: Optional[int] = 0
    samples_count: Optional[int] = 0
    exports_count: Optional[int] = 0

    class Config:
        from_attributes = True


# Track Schemas
class TrackCreate(BaseModel):
    """Schema for creating a track."""

    name: str = Field(..., min_length=1, max_length=200)
    track_type: str = Field(..., pattern="^(audio|midi|instrument)$")
    file_path: Optional[str] = None
    volume: Optional[Decimal] = Field(100.0, ge=0, le=100)
    pan: Optional[Decimal] = Field(0.0, ge=-100, le=100)
    is_muted: Optional[bool] = False
    is_solo: Optional[bool] = False
    order: Optional[int] = Field(0, ge=0)


class TrackUpdate(BaseModel):
    """Schema for updating a track."""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    volume: Optional[Decimal] = Field(None, ge=0, le=100)
    pan: Optional[Decimal] = Field(None, ge=-100, le=100)
    is_muted: Optional[bool] = None
    is_solo: Optional[bool] = None
    order: Optional[int] = Field(None, ge=0)


class TrackResponse(BaseModel):
    """Schema for track response."""

    id: str
    app_id: str
    workspace_id: str
    project_id: str
    name: str
    track_type: str
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    duration: Optional[Decimal] = None
    volume: Decimal
    pan: Decimal
    is_muted: bool
    is_solo: bool
    order: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Sample Schemas
class SampleCreate(BaseModel):
    """Schema for creating a sample."""

    name: str = Field(..., min_length=1, max_length=200)
    category: Optional[str] = None
    file_path: str  # Required for samples
    bpm: Optional[int] = Field(None, ge=1, le=300)
    key: Optional[str] = None
    tags: Optional[str] = None
    is_favorite: Optional[bool] = False


class SampleUpdate(BaseModel):
    """Schema for updating a sample."""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    category: Optional[str] = None
    bpm: Optional[int] = Field(None, ge=1, le=300)
    key: Optional[str] = None
    tags: Optional[str] = None
    is_favorite: Optional[bool] = None


class SampleResponse(BaseModel):
    """Schema for sample response."""

    id: str
    app_id: str
    workspace_id: str
    project_id: Optional[str] = None
    name: str
    category: Optional[str] = None
    file_path: str
    file_size: Optional[int] = None
    duration: Optional[Decimal] = None
    bpm: Optional[int] = None
    key: Optional[str] = None
    tags: Optional[str] = None
    is_favorite: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Export Schemas
class ExportCreate(BaseModel):
    """Schema for creating an export."""

    name: str = Field(..., min_length=1, max_length=200)
    format: str = Field(..., pattern="^(wav|mp3|flac|aac)$")
    quality: Optional[str] = Field(None, pattern="^(low|medium|high|lossless)$")


class ExportResponse(BaseModel):
    """Schema for export response."""

    id: str
    app_id: str
    workspace_id: str
    project_id: str
    name: str
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    format: str
    quality: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True
