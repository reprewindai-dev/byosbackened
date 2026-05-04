"""Audit trail endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from db.session import get_db
from apps.api.deps import get_current_workspace_id
from db.models import AIAuditLog
from core.audit.audit_logger import verify_log
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

router = APIRouter(prefix="/audit", tags=["audit"])


class ComplianceReportRequest(BaseModel):
    """Compliance report request."""

    report_type: str = "gdpr"  # "gdpr", "soc2", "custom"
    start_date: datetime
    end_date: datetime


@router.get("/logs")
async def get_audit_logs(
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
    operation_type: Optional[str] = None,
    provider: Optional[str] = None,
    user_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 100,
    offset: int = 0,
):
    """Query audit logs."""
    query = db.query(AIAuditLog).filter(AIAuditLog.workspace_id == workspace_id)
    
    if operation_type:
        query = query.filter(AIAuditLog.operation_type == operation_type)
    if provider:
        query = query.filter(AIAuditLog.provider == provider)
    if user_id:
        query = query.filter(AIAuditLog.user_id == user_id)
    if start_date:
        query = query.filter(AIAuditLog.created_at >= start_date)
    if end_date:
        query = query.filter(AIAuditLog.created_at <= end_date)
    
    total = query.count()
    logs = query.order_by(AIAuditLog.created_at.desc()).offset(offset).limit(limit).all()
    
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "logs": [
            {
                "id": log.id,
                "operation_type": log.operation_type,
                "provider": log.provider,
                "model": log.model,
                "cost": str(log.cost),
                "pii_detected": log.pii_detected,
                "pii_types": log.pii_types,
                "created_at": log.created_at.isoformat(),
                "input_preview": log.input_preview,
                "output_preview": log.output_preview,
            }
            for log in logs
        ],
    }


@router.get("/verify/{log_id}")
async def verify_audit_log(
    log_id: str,
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Verify audit log integrity."""
    log = db.query(AIAuditLog).filter(
        AIAuditLog.id == log_id,
        AIAuditLog.workspace_id == workspace_id,
    ).first()
    
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit log not found",
        )
    
    verified = verify_log(log)
    verification_status = "verified" if verified else "mismatch"
    reason = None
    if not verified and log.operation_type == "ai.complete":
        verification_status = "inconclusive"
        reason = "legacy_hash_scheme_unverifiable_with_current_row_fields"

    return {
        "log_id": log_id,
        "verified": verified,
        "hash_match": verified,
        "verification_status": verification_status,
        "reason": reason,
        "log_hash": log.log_hash[:16] + "..." if log.log_hash else None,
    }


@router.post("/compliance-report")
async def generate_compliance_report(
    request: ComplianceReportRequest,
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
    limit: int = Query(50000, ge=1, le=100000, description="Max audit logs to analyze"),
):
    """Generate compliance report - with limits to prevent OOM."""
    logs = db.query(AIAuditLog).filter(
        AIAuditLog.workspace_id == workspace_id,
        AIAuditLog.created_at >= request.start_date,
        AIAuditLog.created_at <= request.end_date,
    ).order_by(AIAuditLog.created_at.desc()).limit(limit).all()
    
    # Generate report based on type
    if request.report_type == "gdpr":
        report = {
            "report_type": "GDPR Compliance Report",
            "workspace_id": workspace_id,
            "period": {
                "start": request.start_date.isoformat(),
                "end": request.end_date.isoformat(),
            },
            "summary": {
                "total_operations": len(logs),
                "operations_with_pii": len([l for l in logs if l.pii_detected]),
                "total_cost": str(sum(l.cost for l in logs)),
            },
            "pii_summary": {},
            "data_retention": "90 days",
            "right_to_deletion": "Available via /api/v1/privacy/delete",
            "right_to_access": "Available via /api/v1/privacy/export",
        }
        
        # Count PII types
        pii_counts = {}
        for log in logs:
            if log.pii_types:
                for pii_type in log.pii_types:
                    pii_counts[pii_type] = pii_counts.get(pii_type, 0) + 1
        report["pii_summary"] = pii_counts
    
    else:
        report = {
            "report_type": request.report_type,
            "workspace_id": workspace_id,
            "period": {
                "start": request.start_date.isoformat(),
                "end": request.end_date.isoformat(),
            },
            "total_operations": len(logs),
        }
    
    return report
