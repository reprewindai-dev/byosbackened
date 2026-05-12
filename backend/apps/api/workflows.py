"""Durable Upstash Workflow endpoints for UACP maintenance."""
from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI
from sqlalchemy import desc

from core.operations.operator_watch import evaluate_operator_watch
from core.services.upstash_search_index import index_veklom_run
from db.models import VeklomRun, WorkspaceRequestLog
from db.session import SessionLocal

logger = logging.getLogger(__name__)


def _backfill_recent_proofs(limit: int) -> dict[str, Any]:
    indexed = 0
    skipped = 0
    db = SessionLocal()
    try:
        runs = db.query(VeklomRun).order_by(desc(VeklomRun.created_at)).limit(limit).all()
        for run in runs:
            row = None
            if run.request_log_id:
                row = db.query(WorkspaceRequestLog).filter(WorkspaceRequestLog.id == run.request_log_id).first()
            if row is None:
                skipped += 1
                continue
            ok = index_veklom_run(
                run=run,
                row=row,
                input_hash=run.input_hash,
                output_hash=run.output_hash,
                genome_hash=run.genome_hash,
            )
            indexed += 1 if ok else 0
            skipped += 0 if ok else 1
    finally:
        db.close()
    return {"indexed": indexed, "skipped": skipped}


def _persist_operator_watch() -> dict[str, Any]:
    db = SessionLocal()
    try:
        return evaluate_operator_watch(db, workspace_id=None, persist=True)
    finally:
        db.close()


def register_workflows(app: FastAPI) -> None:
    """Register Upstash Workflow routes against the existing FastAPI app."""
    try:
        from upstash_workflow import AsyncWorkflowContext
        from upstash_workflow.fastapi import Serve
    except Exception:
        logger.warning("upstash_workflow_sdk_missing")
        return

    serve = Serve(app)

    @serve.post("/api/v1/workflows/uacp-maintenance")
    async def uacp_maintenance(context: AsyncWorkflowContext[dict[str, Any]]) -> None:
        payload = context.request_payload or {}
        limit = int(payload.get("proof_backfill_limit") or 250)

        async def _index_recent_proofs() -> dict[str, Any]:
            return _backfill_recent_proofs(limit=max(1, min(limit, 1000)))

        proof_result = await context.run("index-recent-veklom-run-proofs", _index_recent_proofs)

        async def _operator_watch() -> dict[str, Any]:
            result = _persist_operator_watch()
            return {
                "status": result.get("status"),
                "severity": result.get("severity"),
                "actions": len(result.get("actions", [])),
            }

        watch_result = await context.run("persist-operator-watch", _operator_watch)

        async def _emit_summary() -> dict[str, Any]:
            return {
                "workflow": "uacp-maintenance",
                "proof_indexing": proof_result,
                "operator_watch": watch_result,
            }

        await context.run("emit-maintenance-summary", _emit_summary)
