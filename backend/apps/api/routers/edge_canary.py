"""Admin-run live protocol canary and public proof summary."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import desc
from sqlalchemy.orm import Session

from apps.api.deps import require_admin
from db.models import EdgeCanaryReport
from db.session import get_db
from edge.services.protocol_canary import public_canary_summary, run_protocol_canary


router = APIRouter(tags=["edge-canary"])


def _reject_query_params(request: Request | None) -> None:
    if request is None:
        return
    if request.query_params:
        unexpected = ", ".join(sorted(request.query_params.keys()))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported query parameter(s): {unexpected}",
        )


def _store_report(db: Session, report: dict[str, Any]) -> EdgeCanaryReport:
    generated_at = report.get("generated_at")
    if isinstance(generated_at, str):
        generated_at = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
    elif isinstance(generated_at, datetime):
        generated_at = generated_at if generated_at.tzinfo else generated_at.replace(tzinfo=timezone.utc)
    else:
        generated_at = datetime.now(timezone.utc)
    row = EdgeCanaryReport(
        status=str(report.get("status") or "failed"),
        generated_at=generated_at,
        report_json=report,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _load_latest_report(db: Session) -> dict[str, Any] | None:
    try:
        row = db.query(EdgeCanaryReport).order_by(desc(EdgeCanaryReport.created_at)).first()
    except Exception:
        return None
    if not row:
        return None
    report = row.report_json if isinstance(row.report_json, dict) else None
    return report


@router.post("/admin/edge/canary/run")
async def run_edge_canary(
    request: Request = None,
    current_user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Run the live allowlisted protocol canary."""
    _reject_query_params(request)
    _ = current_user
    report = await asyncio.to_thread(run_protocol_canary)
    _store_report(db, report)
    return report


@router.get("/edge/canary/public")
async def public_edge_canary(
    request: Request = None,
    db: Session = Depends(get_db),
):
    """Return the latest cached, sanitized protocol proof summary."""
    _reject_query_params(request)
    report = _load_latest_report(db)
    return public_canary_summary(report)
