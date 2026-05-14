"""Upstash Search indexing for governed Veklom runtime evidence.

This module is intentionally fail-open. Postgres remains authoritative for
VeklomRun proof. Upstash Search is the operator/search acceleration layer used
by Control Center, Sunnyvale, Silicon Valley, and future UACP evidence routing.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from core.config import get_settings

logger = logging.getLogger(__name__)


def _settings() -> Any:
    return get_settings()


def configured() -> bool:
    settings = _settings()
    return bool(settings.upstash_search_rest_url and settings.upstash_search_rest_token)


def index_name() -> str:
    return _settings().upstash_search_index or "default"


def _client() -> Any | None:
    settings = _settings()
    if not configured():
        return None
    try:
        from upstash_search import Search
    except Exception:
        logger.warning("upstash_search_sdk_missing")
        return None
    return Search(
        url=settings.upstash_search_rest_url,
        token=settings.upstash_search_rest_token,
        allow_telemetry=False,
    )


def _index() -> Any | None:
    client = _client()
    if client is None:
        return None
    return client.index(index_name())


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() + "Z" if value else None


def _safe_text(value: Any, *, fallback: str = "") -> str:
    if value is None:
        return fallback
    return str(value)[:4000]


def build_veklom_run_document(
    *,
    run: Any,
    row: Any,
    input_hash: str,
    output_hash: str,
    genome_hash: str,
) -> dict[str, Any]:
    """Build the canonical searchable proof document for a VeklomRun."""
    created_at = run.created_at or getattr(row, "created_at", None)
    run_id = str(run.run_id)
    status = getattr(run.status, "value", run.status)
    governance_decision = _safe_text(run.governance_decision, fallback="UNKNOWN")
    risk_tier = _safe_text(run.risk_tier, fallback="UNKNOWN")
    title = _safe_text(run.raw_intent or row.request_path or row.request_kind, fallback="VeklomRun")
    summary = _safe_text(
        row.response_preview
        or row.prompt_preview
        or row.error_message
        or f"{row.request_kind} via {row.provider or 'unknown'}"
    )

    return {
        "id": f"veklom-run-{run_id}",
        "content": {
            "kind": "veklom_run",
            "title": title,
            "summary": summary,
            "workspace_id": run.workspace_id,
            "tenant_id": run.tenant_id,
            "actor_id": run.actor_id,
            "status": status,
            "governance_decision": governance_decision,
            "risk_tier": risk_tier,
            "provider": row.provider,
            "model": row.model,
            "request_kind": row.request_kind,
            "request_path": row.request_path,
            "source_table": row.source_table,
            "source_id": row.source_id,
        },
        "metadata": {
            "run_id": run_id,
            "request_log_id": row.id,
            "workspace_id": run.workspace_id,
            "tenant_id": run.tenant_id,
            "status": status,
            "governance_decision": governance_decision,
            "risk_tier": risk_tier,
            "provider": row.provider,
            "model": row.model,
            "genome_hash": genome_hash,
            "input_hash": input_hash,
            "output_hash": output_hash,
            "decision_frame_hash": run.decision_frame_hash,
            "created_at": _iso(created_at),
        },
    }


def index_veklom_run(
    *,
    run: Any,
    row: Any,
    input_hash: str,
    output_hash: str,
    genome_hash: str,
) -> bool:
    """Index a sealed proof document in Upstash Search when configured."""
    search_index = _index()
    if search_index is None:
        return False

    document = build_veklom_run_document(
        run=run,
        row=row,
        input_hash=input_hash,
        output_hash=output_hash,
        genome_hash=genome_hash,
    )
    try:
        search_index.upsert(documents=[document])
        return True
    except Exception:
        logger.warning("upstash_search_veklom_run_index_failed", exc_info=True)
        return False


def _normalize_result(item: Any, position: int) -> dict[str, Any]:
    if hasattr(item, "model_dump"):
        item = item.model_dump()
    elif hasattr(item, "dict"):
        item = item.dict()
    elif not isinstance(item, dict):
        item = {
            "id": getattr(item, "id", None),
            "content": getattr(item, "content", None),
            "metadata": getattr(item, "metadata", None),
            "score": getattr(item, "score", None),
        }

    content = item.get("content") or {}
    metadata = item.get("metadata") or {}
    if not isinstance(content, dict):
        content = {"text": str(content)}
    if not isinstance(metadata, dict):
        metadata = {"value": str(metadata)}

    return {
        "position": position,
        "id": item.get("id"),
        "score": item.get("score"),
        "kind": content.get("kind") or metadata.get("kind"),
        "title": content.get("title") or item.get("id"),
        "summary": content.get("summary") or metadata.get("summary"),
        "content": content,
        "metadata": metadata,
    }


def search_evidence(
    *,
    query: str,
    limit: int = 10,
    filter: str | None = None,
    reranking: bool = True,
    semantic_weight: float | None = 0.7,
    input_enrichment: bool = True,
) -> dict[str, Any]:
    """Search indexed UACP/VeklomRun proof documents."""
    if not configured():
        return {
            "configured": False,
            "index": index_name(),
            "results": [],
            "empty_reason": "UPSTASH_SEARCH_REST_URL and UPSTASH_SEARCH_REST_TOKEN are not configured.",
        }

    search_index = _index()
    if search_index is None:
        return {
            "configured": False,
            "index": index_name(),
            "results": [],
            "empty_reason": "Upstash Search SDK is not installed or could not initialize.",
        }

    try:
        response = search_index.search(
            query=query,
            limit=limit,
            filter=filter,
            reranking=reranking,
            semantic_weight=semantic_weight,
            input_enrichment=input_enrichment,
        )
    except Exception as exc:
        logger.warning("upstash_search_query_failed", exc_info=True)
        return {
            "configured": True,
            "index": index_name(),
            "results": [],
            "empty_reason": f"Upstash Search query failed: {type(exc).__name__}",
        }

    raw_results = response
    if hasattr(response, "results"):
        raw_results = response.results
    elif isinstance(response, dict):
        raw_results = response.get("results", response.get("documents", []))

    results = [
        _normalize_result(item, position=index + 1)
        for index, item in enumerate(raw_results or [])
    ]
    return {
        "configured": True,
        "index": index_name(),
        "results": results,
        "empty_reason": None if results else "No indexed evidence matched the query.",
    }
