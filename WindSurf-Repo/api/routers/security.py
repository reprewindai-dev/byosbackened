"""Security management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from db.session import get_db
from db.models.user import User
from apps.api.deps import get_current_user
from apps.api.routers.admin import require_full_admin
from core.security.security_monitoring import SecurityMonitor, SecurityHealthCheck
from core.security.vulnerability_scanner import VulnerabilityScanner
from core.security.intrusion_detection import IntrusionDetectionSystem
from core.security.input_validation import InputValidator
from pydantic import BaseModel
from typing import Optional, Dict, List

router = APIRouter(prefix="/security", tags=["security"])


class SecurityStatusResponse(BaseModel):
    status: str
    events: Dict
    recommendations: List[str]
    last_check: str


class VulnerabilityScanResponse(BaseModel):
    overall_score: float
    owasp_top_10: Dict
    dependency_scan: Dict
    recommendations: List[str]


@router.get("/status", response_model=SecurityStatusResponse)
async def get_security_status(
    admin: User = Depends(require_full_admin),
    db: Session = Depends(get_db),
):
    """Get overall security status."""
    health_check = SecurityHealthCheck()
    status_data = health_check.get_security_status(db)
    return SecurityStatusResponse(**status_data)


@router.get("/scan", response_model=VulnerabilityScanResponse)
async def scan_vulnerabilities(
    admin: User = Depends(require_full_admin),
):
    """Scan for vulnerabilities."""
    scanner = VulnerabilityScanner()
    scan_result = scanner.get_security_score()
    return VulnerabilityScanResponse(**scan_result)


@router.get("/events")
async def get_security_events(
    hours: int = 24,
    admin: User = Depends(require_full_admin),
    db: Session = Depends(get_db),
):
    """Get security events in last N hours."""
    monitor = SecurityMonitor()
    events = monitor.check_security_events(db, hours=hours)
    return events


@router.post("/validate-input")
async def validate_input(
    input_text: str,
    max_length: Optional[int] = None,
    admin: User = Depends(require_full_admin),
):
    """Validate input for security threats."""
    validator = InputValidator()
    is_valid, error = validator.validate_string(
        input_text,
        max_length=max_length,
        allow_sql=False,
        allow_xss=False,
        allow_command_injection=False,
        allow_path_traversal=False,
    )

    return {
        "is_valid": is_valid,
        "error": error,
        "sanitized": validator.sanitize_string(input_text) if is_valid else None,
    }


@router.post("/validate-password")
async def validate_password_strength(
    password: str,
):
    """Validate password strength."""
    validator = InputValidator()
    is_valid, error = validator.validate_password_strength(password)

    return {
        "is_valid": is_valid,
        "error": error,
        "strength": "strong" if is_valid else "weak",
    }
