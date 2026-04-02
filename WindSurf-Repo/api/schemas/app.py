"""App schemas."""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class AppResponse(BaseModel):
    """App response schema."""

    id: str
    name: str
    slug: str
    description: Optional[str] = None
    icon_url: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AppWorkspaceResponse(BaseModel):
    """AppWorkspace response schema."""

    id: str
    app_id: str
    workspace_id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AppWithWorkspaceStatus(AppResponse):
    """App with workspace access status."""

    workspace_has_access: bool
    workspace_is_active: Optional[bool] = None
