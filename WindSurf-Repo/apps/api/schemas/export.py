"""Export schemas."""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ExportRequest(BaseModel):
    """Export request."""

    asset_ids: Optional[list[str]] = None
    transcript_ids: Optional[list[str]] = None
    format: str  # "json", "csv", "zip"
    include_metadata: bool = True


class ExportResponse(BaseModel):
    """Export response."""

    job_id: str
    status: str
    message: str
