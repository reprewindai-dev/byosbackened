"""Upload schemas."""

from pydantic import BaseModel
from datetime import datetime


class UploadRequest(BaseModel):
    """Upload request (multipart form data handled by FastAPI)."""

    pass


class UploadResponse(BaseModel):
    """Upload response."""

    id: str
    filename: str
    original_filename: str
    content_type: str
    file_size: int
    s3_key: str
    created_at: datetime

    class Config:
        from_attributes = True
