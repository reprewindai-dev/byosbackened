"""Privacy/GDPR endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status, Query
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
    limit: int = Query(10000, ge=1, le=50000, description="Max records per type"),
):
    """Export user data (GDPR right to access) - paginated to prevent OOM."""
    # Collect user data with limits to prevent memory issues
    export_data = {
        "workspace_id": workspace_id,
        "exported_at": datetime.utcnow().isoformat(),
        "assets": [],
        "transcripts": [],
        "exports": [],
        "jobs": [],
        "truncated": False,
    }
    
    # Export assets with limit
    assets = db.query(Asset).filter(
        Asset.workspace_id == workspace_id
    ).order_by(Asset.created_at.desc()).limit(limit).all()
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
    if len(assets) >= limit:
        export_data["truncated"] = True
        export_data["assets_truncated"] = True
    
    # Export transcripts with limit
    transcripts = db.query(Transcript).filter(
        Transcript.workspace_id == workspace_id
    ).order_by(Transcript.created_at.desc()).limit(limit).all()
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
    if len(transcripts) >= limit:
        export_data["truncated"] = True
        export_data["transcripts_truncated"] = True
    
    # Export exports with limit
    exports = db.query(Export).filter(
        Export.workspace_id == workspace_id
    ).order_by(Export.created_at.desc()).limit(limit).all()
    export_data["exports"] = [
        {
            "id": e.id,
            "format": e.format.value,
            "created_at": e.created_at.isoformat(),
        }
        for e in exports
    ]
    if len(exports) >= limit:
        export_data["truncated"] = True
        export_data["exports_truncated"] = True
    
    # Export jobs with limit
    jobs = db.query(Job).filter(
        Job.workspace_id == workspace_id
    ).order_by(Job.created_at.desc()).limit(limit).all()
    export_data["jobs"] = [
        {
            "id": j.id,
            "job_type": j.job_type.value,
            "status": j.status.value,
            "created_at": j.created_at.isoformat(),
        }
        for j in jobs
    ]
    if len(jobs) >= limit:
        export_data["truncated"] = True
        export_data["jobs_truncated"] = True
    
    if request.format == "csv":
        # Convert to CSV
        import csv
        import io
        from fastapi.responses import StreamingResponse
        
        def generate_csv():
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow(["Category", "ID", "Field", "Value"])
            
            # Write assets
            for asset in export_data["assets"]:
                writer.writerow(["Asset", asset["id"], "filename", asset["filename"]])
                writer.writerow(["Asset", asset["id"], "content_type", asset["content_type"]])
                writer.writerow(["Asset", asset["id"], "file_size", asset["file_size"]])
                writer.writerow(["Asset", asset["id"], "created_at", asset["created_at"]])
            
            # Write transcripts
            for transcript in export_data["transcripts"]:
                writer.writerow(["Transcript", transcript["id"], "language", transcript["language"]])
                writer.writerow(["Transcript", transcript["id"], "provider", transcript["provider"]])
                writer.writerow(["Transcript", transcript["id"], "created_at", transcript["created_at"]])
                # Truncate text for CSV
                text_preview = transcript["text"][:500] + "..." if len(transcript["text"]) > 500 else transcript["text"]
                writer.writerow(["Transcript", transcript["id"], "text_preview", text_preview])
            
            # Write exports
            for export in export_data["exports"]:
                writer.writerow(["Export", export["id"], "format", export["format"]])
                writer.writerow(["Export", export["id"], "created_at", export["created_at"]])
            
            # Write jobs
            for job in export_data["jobs"]:
                writer.writerow(["Job", job["id"], "job_type", job["job_type"]])
                writer.writerow(["Job", job["id"], "status", job["status"]])
                writer.writerow(["Job", job["id"], "created_at", job["created_at"]])
            
            return output.getvalue()
        
        csv_content = generate_csv()
        return StreamingResponse(
            io.StringIO(csv_content),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=privacy_export_{workspace_id}_{datetime.utcnow().strftime('%Y%m%d')}.csv"
            }
        )
    
    return export_data


@router.post("/delete")
async def delete_user_data(
    request: DataDeletionRequest,
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
    batch_size: int = Query(1000, ge=100, le=5000, description="Records per batch"),
):
    """Delete user data (GDPR right to deletion) - batched to prevent timeouts."""
    if not request.confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Deletion requires explicit confirmation",
        )
    
    deleted_counts = {"assets": 0, "transcripts": 0, "exports": 0, "jobs": 0, "users": 0}
    
    # Delete in batches to prevent memory/timeout issues
    while True:
        assets = db.query(Asset).filter(
            Asset.workspace_id == workspace_id
        ).limit(batch_size).all()
        if not assets:
            break
        for asset in assets:
            db.delete(asset)
            deleted_counts["assets"] += 1
        db.commit()
    
    while True:
        transcripts = db.query(Transcript).filter(
            Transcript.workspace_id == workspace_id
        ).limit(batch_size).all()
        if not transcripts:
            break
        for transcript in transcripts:
            db.delete(transcript)
            deleted_counts["transcripts"] += 1
        db.commit()
    
    while True:
        exports = db.query(Export).filter(
            Export.workspace_id == workspace_id
        ).limit(batch_size).all()
        if not exports:
            break
        for export in exports:
            db.delete(export)
            deleted_counts["exports"] += 1
        db.commit()
    
    while True:
        jobs = db.query(Job).filter(
            Job.workspace_id == workspace_id
        ).limit(batch_size).all()
        if not jobs:
            break
        for job in jobs:
            db.delete(job)
            deleted_counts["jobs"] += 1
        db.commit()
    
    # Delete users last (if requested)
    if request.delete_audit_logs:
        while True:
            users = db.query(User).filter(
                User.workspace_id == workspace_id
            ).limit(batch_size).all()
            if not users:
                break
            for user in users:
                db.delete(user)
                deleted_counts["users"] += 1
            db.commit()
    
    return {
        "message": "Data deleted successfully",
        "deleted_at": datetime.utcnow().isoformat(),
        "deleted_counts": deleted_counts,
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
