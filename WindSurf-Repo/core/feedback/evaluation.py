from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from db.models.ai_feedback import AIFeedback
from db.models.ai_audit import AIAuditLog


class FeedbackEvaluator:
    def apply_feedback_signals(
        self,
        db: Session,
        workspace_id: str,
        lookback_hours: int = 168,
        limit: int = 1000,
        overwrite: bool = False,
    ) -> dict:
        cutoff = datetime.utcnow() - timedelta(hours=lookback_hours)

        q = (
            db.query(AIFeedback)
            .filter(AIFeedback.workspace_id == workspace_id, AIFeedback.created_at >= cutoff)
            .order_by(AIFeedback.created_at.desc())
            .limit(limit)
        )

        processed = 0
        updated_audits = 0
        skipped_missing_audit = 0
        skipped_no_signal = 0

        for fb in q.all():
            processed += 1
            if not fb.audit_log_id:
                skipped_missing_audit += 1
                continue

            audit = (
                db.query(AIAuditLog)
                .filter(AIAuditLog.id == fb.audit_log_id, AIAuditLog.workspace_id == workspace_id)
                .first()
            )
            if not audit:
                skipped_missing_audit += 1
                continue

            score = self._derive_quality_score(fb)
            if score is None:
                skipped_no_signal += 1
                continue

            if (audit.actual_quality is None) or overwrite:
                audit.actual_quality = score
                updated_audits += 1

        db.commit()

        return {
            "workspace_id": workspace_id,
            "lookback_hours": lookback_hours,
            "processed_feedback": processed,
            "updated_audit_logs": updated_audits,
            "skipped_missing_audit": skipped_missing_audit,
            "skipped_no_signal": skipped_no_signal,
        }

    def _derive_quality_score(self, fb: AIFeedback) -> Optional[Decimal]:
        if fb.quality_score is not None:
            return Decimal(str(fb.quality_score))
        if fb.rating is not None:
            try:
                r = int(fb.rating)
            except Exception:
                return None
            if r < 1:
                r = 1
            if r > 5:
                r = 5
            return Decimal(str(round((r - 1) / 4, 2)))
        if fb.is_correct is not None:
            return Decimal("1.00") if int(fb.is_correct) == 1 else Decimal("0.00")
        return None


_evaluator = FeedbackEvaluator()


def get_feedback_evaluator() -> FeedbackEvaluator:
    return _evaluator
