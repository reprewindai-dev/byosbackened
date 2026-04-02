"""Upload router."""

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.orm import Session
from db.session import get_db
from apps.api.deps import get_current_workspace_id
from apps.api.schemas.upload import UploadResponse
from db.models import Asset
from core.config import get_settings
import boto3
import uuid
from datetime import datetime

router = APIRouter(prefix="/upload", tags=["upload"])
settings = get_settings()

# S3 client
s3_client = boto3.client(
    "s3",
    endpoint_url=settings.s3_endpoint_url,
    aws_access_key_id=settings.s3_access_key_id,
    aws_secret_access_key=settings.s3_secret_access_key,
    region_name=settings.s3_region,
    use_ssl=settings.s3_use_ssl,
)


@router.post("", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Upload a file (video/audio) to S3 and record in database."""
    # Generate S3 key
    file_id = str(uuid.uuid4())
    s3_key = f"{workspace_id}/{file_id}/{file.filename}"

    # Upload to S3
    try:
        file_content = await file.read()
        s3_client.put_object(
            Bucket=settings.s3_bucket_name,
            Key=s3_key,
            Body=file_content,
            ContentType=file.content_type,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload to S3: {str(e)}",
        )

    # Record in database
    asset = Asset(
        id=file_id,
        workspace_id=workspace_id,
        filename=file.filename,
        original_filename=file.filename,
        content_type=file.content_type or "application/octet-stream",
        file_size=len(file_content),
        s3_key=s3_key,
        s3_bucket=settings.s3_bucket_name,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)

    return UploadResponse(
        id=asset.id,
        filename=asset.filename,
        original_filename=asset.original_filename,
        content_type=asset.content_type,
        file_size=asset.file_size,
        s3_key=asset.s3_key,
        created_at=asset.created_at,
    )
