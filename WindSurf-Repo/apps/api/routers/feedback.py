"""AI feedback endpoints (quality flywheel)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from apps.api.deps import get_current_workspace_id
from db.session import get_db
from db.models.ai_feedback import AIFeedback
from db.models.ai_audit import AIAuditLog
from core.feedback.evaluation import get_feedback_evaluator

router = APIRouter(prefix="/feedback", tags=["feedback"])
evaluator = get_feedback_evaluator()


class CreateFeedbackRequest(BaseModel):
    audit_log_id: str | None = None
    operation_id: str | None = None
    source: str = "user"  # user/admin/automated

    rating: int | None = None  # 1-5
    quality_score: float | None = None  # 0-1 or 0-100 (workspace defined)
    is_correct: bool | None = None

    feedback_text: str | None = None
    feedback_json: dict | None = None


class EvaluateFeedbackRequest(BaseModel):
    lookback_hours: int = 168
    limit: int = 1000
    overwrite: bool = False


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_feedback(
    request: CreateFeedbackRequest,
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Create feedback entry. Optionally updates audit log with actual_quality."""
    if not request.audit_log_id and not request.operation_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide either audit_log_id or operation_id",
        )

    audit_log = None
    if request.audit_log_id:
        audit_log = (
            db.query(AIAuditLog)
            .filter(AIAuditLog.id == request.audit_log_id, AIAuditLog.workspace_id == workspace_id)
            .first()
        )
        if not audit_log:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit log not found")

    fb = AIFeedback(
        workspace_id=workspace_id,
        audit_log_id=request.audit_log_id,
        operation_id=request.operation_id,
        source=request.source,
        rating=request.rating,
        quality_score=request.quality_score,
        is_correct=(
            1 if request.is_correct is True else 0 if request.is_correct is False else None
        ),
        feedback_text=request.feedback_text,
        feedback_json=request.feedback_json,
    )
    db.add(fb)

    # If feedback supplies quality_score and audit log exists, store it for training
    if audit_log and request.quality_score is not None:
        audit_log.actual_quality = request.quality_score

    db.commit()
    db.refresh(fb)

    return {
        "id": fb.id,
        "workspace_id": fb.workspace_id,
        "audit_log_id": fb.audit_log_id,
        "operation_id": fb.operation_id,
        "source": fb.source,
        "rating": fb.rating,
        "quality_score": float(fb.quality_score) if fb.quality_score is not None else None,
        "is_correct": (bool(fb.is_correct) if fb.is_correct is not None else None),
        "created_at": fb.created_at.isoformat(),
    }


@router.get("")
async def list_feedback(
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
    limit: int = 100,
):
    """List recent feedback."""
    feedback = (
        db.query(AIFeedback)
        .filter(AIFeedback.workspace_id == workspace_id)
        .order_by(AIFeedback.created_at.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "id": f.id,
            "audit_log_id": f.audit_log_id,
            "operation_id": f.operation_id,
            "source": f.source,
            "rating": f.rating,
            "quality_score": float(f.quality_score) if f.quality_score is not None else None,
            "is_correct": (bool(f.is_correct) if f.is_correct is not None else None),
            "feedback_text": f.feedback_text,
            "feedback_json": f.feedback_json,
            "created_at": f.created_at.isoformat(),
        }
        for f in feedback
    ]


@router.post("/evaluate")
async def evaluate_feedback(
    request: EvaluateFeedbackRequest,
    workspace_id: str = Depends(get_current_workspace_id),
    db: Session = Depends(get_db),
):
    """Apply feedback-derived quality signals to audit logs for training/evaluation."""
    return evaluator.apply_feedback_signals(
        db=db,
        workspace_id=workspace_id,
        lookback_hours=request.lookback_hours,
        limit=request.limit,
        overwrite=request.overwrite,
    )
