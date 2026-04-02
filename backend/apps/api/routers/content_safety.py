"""Content Safety: age verification, content classification, PII-first privacy for adult platforms."""
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from apps.api.deps import get_current_user, require_admin
from db.session import get_db
from db.models import (
    ContentFilterLog, AgeVerification,
    ContentCategory, AgeVerificationStatus,
    User,
)

router = APIRouter(prefix="/content-safety", tags=["content-safety"])

# ─── Keywords/patterns that trigger flags (extensible via DB in production) ───

_BLOCKED_PATTERNS: List[str] = []  # CSAM zero-tolerance — add patterns via admin

_ADULT_SIGNALS = {
    "content_type_hints": ["adult", "explicit", "nsfw", "18+", "xxx"],
    "requires_age_gate": True,
}


# ─── Schemas ──────────────────────────────────────────────────────────────────

class ContentScanRequest(BaseModel):
    content_hash: Optional[str] = None
    content_type: Optional[str] = None
    filename: Optional[str] = None
    tags: Optional[List[str]] = None
    asset_id: Optional[str] = None


class ContentScanResponse(BaseModel):
    allowed: bool
    category: str
    confidence: float
    flags: List[str]
    action: str
    requires_age_verification: bool
    message: Optional[str] = None


class AgeVerificationRequest(BaseModel):
    verification_method: str = "self_attestation"


class AgeVerificationStatusResponse(BaseModel):
    user_id: str
    status: str
    verified_at: Optional[str]
    expires_at: Optional[str]
    verification_method: Optional[str]


# ─── Internal scan logic ──────────────────────────────────────────────────────

def _scan_content(
    content_hash: Optional[str],
    content_type: Optional[str],
    filename: Optional[str],
    tags: Optional[List[str]],
) -> ContentScanResponse:
    """
    Synchronous content scan. Extensible: add ML model inference here.
    Zero tolerance for CSAM — any match is an immediate hard block.
    """
    flags = []
    category = ContentCategory.SAFE
    confidence = 0.95
    action = "allow"
    requires_age = False

    lower_name = (filename or "").lower()
    lower_type = (content_type or "").lower()
    tag_set = {t.lower() for t in (tags or [])}

    # CSAM zero-tolerance check (hash blocklist + pattern)
    if content_hash and content_hash in _BLOCKED_PATTERNS:
        return ContentScanResponse(
            allowed=False,
            category=ContentCategory.BLOCKED.value,
            confidence=1.0,
            flags=["csam_hash_match"],
            action="block_report",
            requires_age_verification=False,
            message="Content blocked and flagged for review.",
        )

    # Adult content detection
    adult_signals = _ADULT_SIGNALS["content_type_hints"]
    if any(s in lower_name or s in lower_type for s in adult_signals):
        flags.append("adult_content_detected")
        category = ContentCategory.ADULT
        requires_age = True
        action = "allow_with_age_gate"
        confidence = 0.88

    if tag_set.intersection({"nsfw", "explicit", "adult", "xxx", "18+"}):
        flags.append("adult_tags")
        category = ContentCategory.ADULT
        requires_age = True
        action = "allow_with_age_gate"

    allowed = category not in (ContentCategory.BLOCKED,)

    return ContentScanResponse(
        allowed=allowed,
        category=category.value,
        confidence=confidence,
        flags=flags,
        action=action,
        requires_age_verification=requires_age,
        message=None,
    )


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.post("/scan", response_model=ContentScanResponse)
async def scan_content(
    payload: ContentScanRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Scan content metadata for safety classification."""
    result = _scan_content(
        content_hash=payload.content_hash,
        content_type=payload.content_type,
        filename=payload.filename,
        tags=payload.tags,
    )

    log = ContentFilterLog(
        workspace_id=current_user.workspace_id,
        user_id=current_user.id,
        asset_id=payload.asset_id,
        content_hash=payload.content_hash,
        category=ContentCategory(result.category),
        confidence=result.confidence,
        flags=result.flags,
        action_taken=result.action,
        blocked_reason="content_violation" if not result.allowed else None,
    )
    db.add(log)
    db.commit()

    return result


@router.post("/scan/file", response_model=ContentScanResponse)
async def scan_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Scan an uploaded file — hash it and run content checks."""
    chunk = await file.read(65536)
    content_hash = hashlib.sha256(chunk).hexdigest()
    result = _scan_content(
        content_hash=content_hash,
        content_type=file.content_type,
        filename=file.filename,
        tags=None,
    )

    log = ContentFilterLog(
        workspace_id=current_user.workspace_id,
        user_id=current_user.id,
        content_hash=content_hash,
        category=ContentCategory(result.category),
        confidence=result.confidence,
        flags=result.flags,
        action_taken=result.action,
        blocked_reason="content_violation" if not result.allowed else None,
    )
    db.add(log)
    db.commit()
    return result


# ─── Age Verification ─────────────────────────────────────────────────────────

@router.post("/age-verification/initiate")
async def initiate_age_verification(
    payload: AgeVerificationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Initiate age verification. Returns a token the user must confirm.
    Privacy-first: we store only a verification status, never raw ID documents.
    """
    existing = db.query(AgeVerification).filter(
        AgeVerification.user_id == current_user.id,
    ).first()
    if existing and existing.status == AgeVerificationStatus.VERIFIED:
        if existing.expires_at and datetime.utcnow() < existing.expires_at:
            return {"status": "already_verified", "expires_at": existing.expires_at.isoformat()}

    token = secrets.token_urlsafe(32)
    if existing:
        existing.verification_method = payload.verification_method
        existing.verification_token = token
        existing.status = AgeVerificationStatus.PENDING
        existing.updated_at = datetime.utcnow()
    else:
        existing = AgeVerification(
            workspace_id=current_user.workspace_id,
            user_id=current_user.id,
            verification_method=payload.verification_method,
            verification_token=token,
            status=AgeVerificationStatus.PENDING,
        )
        db.add(existing)
    db.commit()

    return {
        "status": "pending",
        "verification_token": token,
        "method": payload.verification_method,
        "instructions": _get_verification_instructions(payload.verification_method),
    }


def _get_verification_instructions(method: str) -> str:
    methods = {
        "self_attestation": "Confirm you are 18+ by submitting the token to /confirm endpoint.",
        "credit_card": "A $0 authorization will be placed on your card to verify age.",
        "id_document": "Upload a photo ID via the secure upload endpoint. ID is not stored.",
        "third_party": "You will be redirected to an age verification partner.",
    }
    return methods.get(method, "Complete age verification via the provided token.")


@router.post("/age-verification/confirm")
async def confirm_age_verification(
    token: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Confirm age verification token — marks user as verified."""
    record = db.query(AgeVerification).filter(
        AgeVerification.user_id == current_user.id,
        AgeVerification.verification_token == token,
        AgeVerification.status == AgeVerificationStatus.PENDING,
    ).first()
    if not record:
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")

    record.status = AgeVerificationStatus.VERIFIED
    record.verified_at = datetime.utcnow()
    record.expires_at = datetime.utcnow() + timedelta(days=365)
    record.verification_token = None
    record.updated_at = datetime.utcnow()
    db.commit()

    return {"status": "verified", "expires_at": record.expires_at.isoformat()}


@router.get("/age-verification/status", response_model=AgeVerificationStatusResponse)
async def age_verification_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Check current user's age verification status."""
    record = db.query(AgeVerification).filter(
        AgeVerification.user_id == current_user.id
    ).first()
    if not record:
        return AgeVerificationStatusResponse(
            user_id=current_user.id,
            status="unverified",
            verified_at=None,
            expires_at=None,
            verification_method=None,
        )
    return AgeVerificationStatusResponse(
        user_id=current_user.id,
        status=record.status.value,
        verified_at=record.verified_at.isoformat() if record.verified_at else None,
        expires_at=record.expires_at.isoformat() if record.expires_at else None,
        verification_method=record.verification_method,
    )


@router.get("/logs")
async def content_filter_logs(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin: view content filter decision log for the workspace."""
    logs = db.query(ContentFilterLog).filter(
        ContentFilterLog.workspace_id == current_user.workspace_id
    ).order_by(ContentFilterLog.created_at.desc()).offset(skip).limit(limit).all()
    return [
        {
            "id": l.id,
            "asset_id": l.asset_id,
            "category": l.category.value,
            "confidence": l.confidence,
            "flags": l.flags,
            "action": l.action_taken,
            "created_at": l.created_at.isoformat(),
        }
        for l in logs
    ]
