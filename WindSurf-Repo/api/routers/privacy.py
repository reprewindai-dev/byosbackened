"""Privacy/GDPR endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from db.session import get_db
from apps.api.deps import get_current_workspace_id
from core.privacy.pii_detection import detect_pii, mask_pii, detect_and_mask_pii
from db.models import Asset, Transcript, Export, Job, User
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

router = APIRouter(prefix="/privacy", tags=["privacy"])


class DataExportRequest(BaseModel):
    """Data export request."""

    format: str = "json"  # json, csv


class DataDeletionRequest(BaseModel):
    """Data deletion request."""

    confirm: bool = False
    delete_audit_logs: bool = False  # Usually audit logs retained longer


@router.post("/export")
async def export_user_data(
    request: DataExportRequest,
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Export all user data (GDPR right to access)."""
    # Collect all user data
    export_data = {
        "workspace_id": workspace_id,
        "exported_at": datetime.utcnow().isoformat(),
        "assets": [],
        "transcripts": [],
        "exports": [],
        "jobs": [],
    }

    # Export assets
    assets = db.query(Asset).filter(Asset.workspace_id == workspace_id).all()
    export_data["assets"] = [
        {
            "id": a.id,
            "filename": a.filename,
            "content_type": a.content_type,
            "file_size": a.file_size,
            "created_at": a.created_at.isoformat(),
        }
        for a in assets
    ]

    # Export transcripts
    transcripts = db.query(Transcript).filter(Transcript.workspace_id == workspace_id).all()
    export_data["transcripts"] = [
        {
            "id": t.id,
            "text": t.text,
            "language": t.language,
            "provider": t.provider,
            "created_at": t.created_at.isoformat(),
        }
        for t in transcripts
    ]

    # Export exports
    exports = db.query(Export).filter(Export.workspace_id == workspace_id).all()
    export_data["exports"] = [
        {
            "id": e.id,
            "format": e.format.value,
            "created_at": e.created_at.isoformat(),
        }
        for e in exports
    ]

    # Export jobs
    jobs = db.query(Job).filter(Job.workspace_id == workspace_id).all()
    export_data["jobs"] = [
        {
            "id": j.id,
            "job_type": j.job_type.value,
            "status": j.status.value,
            "created_at": j.created_at.isoformat(),
        }
        for j in jobs
    ]

    if request.format == "csv":
        # TODO: Convert to CSV
        return {"message": "CSV export not yet implemented", "data": export_data}

    return export_data


@router.post("/delete")
async def delete_user_data(
    request: DataDeletionRequest,
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Delete all user data (GDPR right to deletion)."""
    if not request.confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Deletion requires explicit confirmation",
        )

    # Delete assets
    assets = db.query(Asset).filter(Asset.workspace_id == workspace_id).all()
    for asset in assets:
        db.delete(asset)

    # Delete transcripts
    transcripts = db.query(Transcript).filter(Transcript.workspace_id == workspace_id).all()
    for transcript in transcripts:
        db.delete(transcript)

    # Delete exports
    exports = db.query(Export).filter(Export.workspace_id == workspace_id).all()
    for export in exports:
        db.delete(export)

    # Delete jobs
    jobs = db.query(Job).filter(Job.workspace_id == workspace_id).all()
    for job in jobs:
        db.delete(job)

    # Delete users (if requested)
    users = db.query(User).filter(User.workspace_id == workspace_id).all()
    for user in users:
        db.delete(user)

    db.commit()

    return {
        "message": "Data deleted successfully",
        "deleted_at": datetime.utcnow().isoformat(),
    }


@router.post("/detect-pii")
async def detect_pii_endpoint(
    text: str,
    workspace_id: str = Depends(get_current_workspace_id),
):
    """Detect PII in text."""
    detected = detect_pii(text)
    return {
        "detected": detected,
        "count": len(detected),
    }


@router.post("/mask-pii")
async def mask_pii_endpoint(
    text: str,
    strategy: str = "partial",
    workspace_id: str = Depends(get_current_workspace_id),
):
    """Mask PII in text."""
    masked, detected = detect_and_mask_pii(text, strategy)
    return {
        "masked_text": masked,
        "detected": detected,
    }
