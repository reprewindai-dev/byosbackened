"""Compliance endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from db.session import get_db
from apps.api.deps import get_current_workspace_id
from core.compliance import ComplianceChecker, ComplianceReporter, get_regulation_manager
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(prefix="/compliance", tags=["compliance"])
compliance_checker = ComplianceChecker()
compliance_reporter = ComplianceReporter()


class ComplianceCheckRequest(BaseModel):
    """Compliance check request."""
    regulation_id: str


class ComplianceReportRequest(BaseModel):
    """Compliance report request."""
    regulation_id: str
    start_date: datetime
    end_date: datetime


@router.get("/regulations")
async def list_regulations(
    workspace_id: str = Depends(get_current_workspace_id),
):
    """List supported regulations."""
    regulation_manager = get_regulation_manager()
    regulations = regulation_manager.list_regulations()
    
    return {
        "regulations": [
            {
                "id": reg_id,
                "name": regulation_manager.get_regulation(reg_id).get("name"),
                "region": regulation_manager.get_regulation(reg_id).get("region"),
            }
            for reg_id in regulations
        ],
    }


@router.post("/check")
async def check_compliance(
    request: ComplianceCheckRequest,
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Check compliance for workspace."""
    result = compliance_checker.check_compliance(
        db=db,
        workspace_id=workspace_id,
        regulation_id=request.regulation_id,
    )
    
    return result


@router.post("/report")
async def generate_compliance_report(
    request: ComplianceReportRequest,
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Generate compliance report."""
    report = compliance_reporter.generate_report(
        db=db,
        workspace_id=workspace_id,
        regulation_id=request.regulation_id,
        start_date=request.start_date,
        end_date=request.end_date,
    )
    
    return report
