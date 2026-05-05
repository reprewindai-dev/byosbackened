"""Workspace gateway analytics and model catalog helpers."""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Iterable, Optional

from sqlalchemy import and_, desc, func
from sqlalchemy.orm import Session

from core.config import get_settings
from core.llm.ollama_client import OllamaClient
from db.models import (
    APIKey,
    Alert,
    AIAuditLog,
    Budget,
    ExecutionLog,
    IncidentLog,
    TokenTransaction,
    TokenWallet,
    WorkspaceModelSetting,
    WorkspaceRequestLog,
)


TOKEN_USD_RATE = Decimal("0.00001")
settings = get_settings()
logger = logging.getLogger(__name__)

_BEDROCK_PROBE_TTL_SECONDS = 60
_bedrock_probe_cache: tuple[float, bool] | None = None


def _workspace_token_cost_per_1k_output_tokens() -> Decimal:
    return (TOKEN_USD_RATE * Decimal(10)).quantize(Decimal("0.000001"))


def _has_bedrock_credentials() -> bool:
    return bool(settings.aws_access_key_id and settings.aws_secret_access_key)


def _probe_bedrock_connectivity() -> bool:
    try:
        import boto3
        from botocore.config import Config

        client_config = Config(
            connect_timeout=1,
            read_timeout=1,
            retries={"max_attempts": 1, "mode": "standard"},
        )
        session = boto3.Session(
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            region_name=settings.aws_default_region,
        )
        session.client("sts", config=client_config).get_caller_identity()
        session.client("bedrock", config=client_config).list_foundation_models(byProvider="Anthropic")
        return True
    except Exception as exc:
        logger.info("bedrock_model_catalog_probe_failed", extra={"error": str(exc)})
        return False


def _bedrock_connected() -> bool:
    global _bedrock_probe_cache

    if not _has_bedrock_credentials():
        return False

    now = time.monotonic()
    if _bedrock_probe_cache and now - _bedrock_probe_cache[0] < _BEDROCK_PROBE_TTL_SECONDS:
        return _bedrock_probe_cache[1]

    connected = _probe_bedrock_connectivity()
    _bedrock_probe_cache = (now, connected)
    return connected


def _runtime_model_catalog() -> list[dict]:
    try:
        ollama_connected = OllamaClient().health_check()
    except Exception:
        ollama_connected = False

    rows = [
        {
            "model_slug": "ollama-default",
            "display_name": f"{settings.llm_model_default} (Ollama)",
            "bedrock_model_id": settings.llm_model_default,
            "provider": "ollama",
            "connected": ollama_connected,
            "input_cost_per_1m_tokens": Decimal("0.00"),
            "output_cost_per_1m_tokens": _workspace_token_cost_per_1k_output_tokens() * Decimal(1000),
        }
    ]

    if settings.groq_api_key and settings.llm_fallback == "groq":
        rows.append(
            {
                "model_slug": "groq-fast",
                "display_name": f"{settings.groq_model_fast} (Groq)",
                "bedrock_model_id": settings.groq_model_fast,
                "provider": "groq",
                "connected": True,
                "input_cost_per_1m_tokens": Decimal("0.00"),
                "output_cost_per_1m_tokens": _workspace_token_cost_per_1k_output_tokens() * Decimal(1000),
            }
        )
        rows.append(
            {
                "model_slug": "groq-smart",
                "display_name": f"{settings.groq_model_smart} (Groq)",
                "bedrock_model_id": settings.groq_model_smart,
                "provider": "groq",
                "connected": True,
                "input_cost_per_1m_tokens": Decimal("0.00"),
                "output_cost_per_1m_tokens": _workspace_token_cost_per_1k_output_tokens() * Decimal(1000),
            }
        )

    if _has_bedrock_credentials():
        rows.append(
            {
                "model_slug": "bedrock-haiku",
                "display_name": "anthropic.claude-3-haiku-20240307-v1:0 (Bedrock)",
                "bedrock_model_id": "anthropic.claude-3-haiku-20240307-v1:0",
                "provider": "bedrock",
                "connected": _bedrock_connected(),
                "input_cost_per_1m_tokens": Decimal("0.00"),
                "output_cost_per_1m_tokens": _workspace_token_cost_per_1k_output_tokens() * Decimal(1000),
            }
        )

    return rows


@dataclass
class NormalizedLog:
    source_table: str
    source_id: str
    request_kind: str
    request_path: str
    model: str | None
    provider: str | None
    status: str
    prompt_preview: str | None
    response_preview: str | None
    request_json: str | None
    response_json: str | None
    error_message: str | None
    tokens_in: int
    tokens_out: int
    latency_ms: int
    cost_usd: Decimal
    created_at: datetime
    user_id: str | None = None
    api_key_id: str | None = None


def month_start(now: Optional[datetime] = None) -> datetime:
    now = now or datetime.utcnow()
    return datetime(now.year, now.month, 1)


def _usd_from_tokens(tokens: int) -> Decimal:
    return (Decimal(tokens or 0) * TOKEN_USD_RATE).quantize(Decimal("0.000001"))


def seed_workspace_models(db: Session, workspace_id: str) -> list[WorkspaceModelSetting]:
    query = db.query(WorkspaceModelSetting).filter(
        WorkspaceModelSetting.workspace_id == workspace_id
    )
    try:
        existing_rows = query.all()
    except AttributeError:
        first = query.first()
        existing_rows = [first] if first else []

    existing_by_slug = {row.model_slug: row for row in existing_rows if row}

    rows: list[WorkspaceModelSetting] = []
    for model in _runtime_model_catalog():
        row = existing_by_slug.get(model["model_slug"])
        if row:
            row.display_name = model["display_name"]
            row.bedrock_model_id = model["bedrock_model_id"]
            row.provider = model["provider"]
            row.connected = model["connected"]
            row.input_cost_per_1m_tokens = model["input_cost_per_1m_tokens"]
            row.output_cost_per_1m_tokens = model["output_cost_per_1m_tokens"]
        else:
            row = WorkspaceModelSetting(
                workspace_id=workspace_id,
                model_slug=model["model_slug"],
                display_name=model["display_name"],
                bedrock_model_id=model["bedrock_model_id"],
                provider=model["provider"],
                enabled=True,
                connected=model["connected"],
                input_cost_per_1m_tokens=model["input_cost_per_1m_tokens"],
                output_cost_per_1m_tokens=model["output_cost_per_1m_tokens"],
            )
            db.add(row)
        rows.append(row)
    db.flush()
    return rows


def get_model_settings(db: Session, workspace_id: str) -> list[WorkspaceModelSetting]:
    rows = seed_workspace_models(db, workspace_id)
    db.commit()
    return rows


def get_model_setting(db: Session, workspace_id: str, model_slug: str) -> WorkspaceModelSetting:
    rows = seed_workspace_models(db, workspace_id)
    row = db.query(WorkspaceModelSetting).filter(
        WorkspaceModelSetting.workspace_id == workspace_id,
        WorkspaceModelSetting.model_slug == model_slug,
    ).first()
    if not row:
        row = next((item for item in rows if item.model_slug == model_slug), None)
    if not row:
        raise ValueError(f"Unknown model slug: {model_slug}")
    return row


def set_model_enabled(db: Session, workspace_id: str, model_slug: str, enabled: bool) -> WorkspaceModelSetting:
    row = get_model_setting(db, workspace_id, model_slug)
    row.enabled = enabled
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return row


def normalize_request_log(row: WorkspaceRequestLog) -> NormalizedLog:
    return NormalizedLog(
        source_table=row.source_table,
        source_id=row.source_id,
        request_kind=row.request_kind,
        request_path=row.request_path,
        model=row.model,
        provider=row.provider,
        status=row.status,
        prompt_preview=row.prompt_preview,
        response_preview=row.response_preview,
        request_json=row.request_json,
        response_json=row.response_json,
        error_message=row.error_message,
        tokens_in=int(row.tokens_in or 0),
        tokens_out=int(row.tokens_out or 0),
        latency_ms=int(row.latency_ms or 0),
        cost_usd=Decimal(row.cost_usd or 0),
        created_at=row.created_at,
        user_id=row.user_id,
        api_key_id=row.api_key_id,
    )


def normalize_exec_log(row: ExecutionLog) -> NormalizedLog:
    cost_usd = _usd_from_tokens(int(row.total_tokens or 0))
    return NormalizedLog(
        source_table="execution_logs",
        source_id=row.id,
        request_kind="exec",
        request_path="/v1/exec",
        model=row.model,
        provider=None,
        status="success" if row.success else "error",
        prompt_preview=(row.prompt or "")[:500],
        response_preview=(row.response or "")[:500] if row.response else None,
        request_json=json.dumps(
            {
                "prompt": row.prompt,
                "model": row.model,
                "provider": None,
            },
            ensure_ascii=False,
        ),
        response_json=json.dumps(
            {
                "response": row.response,
                "prompt_tokens": row.prompt_tokens,
                "completion_tokens": row.completion_tokens,
                "total_tokens": row.total_tokens,
            },
            ensure_ascii=False,
        ),
        error_message=row.error_message,
        tokens_in=int(row.prompt_tokens or 0),
        tokens_out=int(row.completion_tokens or 0),
        latency_ms=int(row.latency_ms or 0),
        cost_usd=cost_usd,
        created_at=row.created_at,
    )


def normalize_audit_log(row: AIAuditLog) -> NormalizedLog:
    cost_usd = Decimal(row.cost or 0).quantize(Decimal("0.000001"))
    return NormalizedLog(
        source_table="ai_audit_logs",
        source_id=row.id,
        request_kind="ai.complete",
        request_path="/api/v1/ai/complete",
        model=row.model,
        provider=row.provider,
        status="success",
        prompt_preview=row.input_preview,
        response_preview=row.output_preview,
        request_json=json.dumps(
            {
                "operation_type": row.operation_type,
                "provider": row.provider,
                "model": row.model,
            },
            ensure_ascii=False,
        ),
        response_json=json.dumps(
            {
                "cost": str(row.cost),
                "tokens_input": row.tokens_input,
                "tokens_output": row.tokens_output,
            },
            ensure_ascii=False,
        ),
        error_message=None,
        tokens_in=int(row.tokens_input or 0),
        tokens_out=int(row.tokens_output or 0),
        latency_ms=0,
        cost_usd=cost_usd,
        created_at=row.created_at,
    )


def record_request_log(
    db: Session,
    *,
    workspace_id: str,
    request_kind: str,
    request_path: str,
    model: str | None,
    provider: str | None,
    status: str,
    prompt_preview: str | None,
    response_preview: str | None,
    request_json: dict | None,
    response_json: dict | None,
    tokens_in: int,
    tokens_out: int,
    latency_ms: int,
    cost_usd: Decimal,
    source_table: str,
    source_id: str,
    user_id: str | None = None,
    api_key_id: str | None = None,
    error_message: str | None = None,
) -> WorkspaceRequestLog:
    row = WorkspaceRequestLog(
        workspace_id=workspace_id,
        user_id=user_id,
        api_key_id=api_key_id,
        source_table=source_table,
        source_id=source_id,
        request_kind=request_kind,
        request_path=request_path,
        model=model,
        provider=provider,
        status=status,
        prompt_preview=prompt_preview,
        response_preview=response_preview,
        request_json=json.dumps(request_json, ensure_ascii=False) if request_json is not None else None,
        response_json=json.dumps(response_json, ensure_ascii=False) if response_json is not None else None,
        error_message=error_message,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        latency_ms=latency_ms,
        cost_usd=cost_usd,
    )
    db.add(row)
    db.commit()
    if hasattr(db, "refresh"):
        db.refresh(row)
    return row


def _source_ids(rows: Iterable[WorkspaceRequestLog], source_table: str) -> set[str]:
    return {row.source_id for row in rows if row.source_table == source_table}


def fetch_normalized_logs(
    db: Session,
    *,
    workspace_id: str,
    start_date: datetime,
    end_date: datetime,
    limit: int = 100,
    offset: int = 0,
    model: str | None = None,
    status: str | None = None,
    request_kind: str | None = None,
) -> tuple[list[NormalizedLog], int]:
    workspace_rows = (
        db.query(WorkspaceRequestLog)
        .filter(
            WorkspaceRequestLog.workspace_id == workspace_id,
            WorkspaceRequestLog.created_at >= start_date,
            WorkspaceRequestLog.created_at <= end_date,
        )
        .order_by(desc(WorkspaceRequestLog.created_at))
        .all()
    )
    exec_source_ids = _source_ids(workspace_rows, "execution_logs")
    audit_source_ids = _source_ids(workspace_rows, "ai_audit_logs")
    normalized: list[NormalizedLog] = [normalize_request_log(row) for row in workspace_rows]

    exec_query = db.query(ExecutionLog).filter(
        ExecutionLog.workspace_id == workspace_id,
        ExecutionLog.created_at >= start_date,
        ExecutionLog.created_at <= end_date,
    )
    if exec_source_ids:
        exec_query = exec_query.filter(~ExecutionLog.id.in_(exec_source_ids))
    exec_rows = exec_query.all()
    normalized.extend(normalize_exec_log(row) for row in exec_rows)

    audit_query = db.query(AIAuditLog).filter(
        AIAuditLog.workspace_id == workspace_id,
        AIAuditLog.created_at >= start_date,
        AIAuditLog.created_at <= end_date,
    )
    if audit_source_ids:
        audit_query = audit_query.filter(~AIAuditLog.id.in_(audit_source_ids))
    audit_rows = audit_query.all()
    normalized.extend(normalize_audit_log(row) for row in audit_rows)

    def _matches(row: NormalizedLog) -> bool:
        if model and (row.model or "") != model:
            return False
        if status and row.status != status:
            return False
        if request_kind and row.request_kind != request_kind:
            return False
        return True

    filtered = [row for row in normalized if _matches(row)]
    filtered.sort(key=lambda row: row.created_at, reverse=True)
    total = len(filtered)
    return filtered[offset : offset + limit], total


def fetch_overview(db: Session, *, workspace_id: str) -> dict:
    start = month_start()
    end = datetime.utcnow()
    logs, _ = fetch_normalized_logs(db, workspace_id=workspace_id, start_date=start, end_date=end, limit=2000)

    total_tokens = sum((row.tokens_in + row.tokens_out) for row in logs)
    total_cost = sum((row.cost_usd for row in logs), Decimal("0"))
    active_models = sorted({row.model for row in logs if row.model})

    recent_feed = [
        {
            "id": row.source_id,
            "kind": row.request_kind,
            "model": row.model,
            "latency_ms": row.latency_ms,
            "tokens": row.tokens_out or row.tokens_in,
            "status": row.status,
            "created_at": row.created_at.isoformat(),
        }
        for row in logs[:10]
    ]

    return {
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "total_api_calls": len(logs),
        "total_tokens_used": total_tokens,
        "total_cost_usd": float(total_cost.quantize(Decimal("0.000001"))),
        "active_models": active_models,
        "live_feed": recent_feed,
    }


def fetch_model_rows(db: Session, *, workspace_id: str) -> list[dict]:
    models = get_model_settings(db, workspace_id)
    return [
        {
            "model_slug": row.model_slug,
            "display_name": row.display_name,
            "bedrock_model_id": row.bedrock_model_id,
            "provider": row.provider,
            "enabled": row.enabled,
            "connected": row.connected,
            "input_cost_per_1m_tokens": float(row.input_cost_per_1m_tokens or 0),
            "output_cost_per_1m_tokens": float(row.output_cost_per_1m_tokens or 0),
            "workspace_cost_per_1k_output_tokens": float((Decimal(row.output_cost_per_1m_tokens or 0) / Decimal("1000")).quantize(Decimal("0.000001"))),
        }
        for row in models
    ]


def fetch_api_key_rows(db: Session, *, workspace_id: str, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> list[dict]:
    start_date = start_date or month_start()
    end_date = end_date or datetime.utcnow()
    keys = (
        db.query(APIKey)
        .filter(APIKey.workspace_id == workspace_id)
        .order_by(APIKey.created_at.desc())
        .all()
    )
    logs, _ = fetch_normalized_logs(db, workspace_id=workspace_id, start_date=start_date, end_date=end_date, limit=5000)
    stats_by_key: dict[str, dict] = {}
    for row in logs:
        if not row.api_key_id:
            continue
        bucket = stats_by_key.setdefault(
            row.api_key_id,
            {"total_calls": 0, "total_cost_usd": Decimal("0"), "last_used_at": None},
        )
        bucket["total_calls"] += 1
        bucket["total_cost_usd"] += row.cost_usd
        if not bucket["last_used_at"] or row.created_at > bucket["last_used_at"]:
            bucket["last_used_at"] = row.created_at

    result = []
    for key in keys:
        bucket = stats_by_key.get(key.id, {"total_calls": 0, "total_cost_usd": Decimal("0"), "last_used_at": None})
        result.append(
            {
                "id": key.id,
                "name": key.name,
                "key_prefix": key.key_prefix,
                "scopes": key.scopes,
                "is_active": key.is_active,
                "created_at": key.created_at.isoformat(),
                "last_used_at": bucket["last_used_at"].isoformat() if bucket["last_used_at"] else (key.last_used_at.isoformat() if key.last_used_at else None),
                "total_calls": bucket["total_calls"],
                "total_cost_usd": float(bucket["total_cost_usd"].quantize(Decimal("0.000001"))),
            }
        )
    return result


def fetch_observability_payload(
    db: Session,
    *,
    workspace_id: str,
    start_date: datetime,
    end_date: datetime,
    model: str | None = None,
    status: str | None = None,
) -> dict:
    rows, total = fetch_normalized_logs(
        db,
        workspace_id=workspace_id,
        start_date=start_date,
        end_date=end_date,
        model=model,
        status=status,
        limit=500,
        offset=0,
    )

    series_days: dict[str, dict] = {}
    for row in rows:
        day_key = row.created_at.strftime("%Y-%m-%d")
        bucket = series_days.setdefault(
            day_key,
            {"date": day_key, "errors": 0, "calls": 0, "latency_total": 0, "latency_count": 0},
        )
        bucket["calls"] += 1
        bucket["latency_total"] += row.latency_ms
        bucket["latency_count"] += 1
        if row.status != "success":
            bucket["errors"] += 1

    daily = list(series_days.values())
    daily.sort(key=lambda item: item["date"])

    error_chart = [
        {"date": item["date"], "error_rate": round((item["errors"] / item["calls"]) * 100, 2) if item["calls"] else 0}
        for item in daily
    ]
    latency_chart = [
        {"date": item["date"], "avg_latency_ms": round(item["latency_total"] / item["latency_count"], 2) if item["latency_count"] else 0}
        for item in daily
    ]

    payload_rows = [
        {
            "id": row.source_id,
            "timestamp": row.created_at.isoformat(),
            "model": row.model,
            "prompt_preview": row.prompt_preview,
            "tokens_in": row.tokens_in,
            "tokens_out": row.tokens_out,
            "latency_ms": row.latency_ms,
            "cost_usd": float(row.cost_usd.quantize(Decimal("0.000001"))),
            "status": row.status,
            "request_kind": row.request_kind,
            "request_path": row.request_path,
            "request_json": row.request_json,
            "response_json": row.response_json,
            "response_preview": row.response_preview,
            "error_message": row.error_message,
            "api_key_id": row.api_key_id,
            "user_id": row.user_id,
        }
        for row in rows
    ]

    return {
        "total": total,
        "rows": payload_rows,
        "error_rate_chart": error_chart,
        "latency_chart": latency_chart,
    }


def fetch_cost_budget_payload(db: Session, *, workspace_id: str) -> dict:
    start = month_start()
    end = datetime.utcnow()
    rows, _ = fetch_normalized_logs(db, workspace_id=workspace_id, start_date=start, end_date=end, limit=5000)
    key_name_map = {
        row.id: row.name
        for row in db.query(APIKey).filter(APIKey.workspace_id == workspace_id).all()
    }

    total_cost = sum((row.cost_usd for row in rows), Decimal("0"))
    by_model: dict[str, Decimal] = {}
    by_key: dict[str, Decimal] = {}
    monthly: dict[str, Decimal] = {}
    for row in rows:
        if row.model:
            by_model[row.model] = by_model.get(row.model, Decimal("0")) + row.cost_usd
        if row.api_key_id:
            by_key[row.api_key_id] = by_key.get(row.api_key_id, Decimal("0")) + row.cost_usd
        day = row.created_at.strftime("%Y-%m-%d")
        monthly[day] = monthly.get(day, Decimal("0")) + row.cost_usd

    budgets = db.query(Budget).filter(Budget.workspace_id == workspace_id).order_by(Budget.period_end.asc()).all()
    monthly_budget = next((b for b in budgets if b.budget_type == "monthly"), None)

    return {
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "total_cost_usd": float(total_cost.quantize(Decimal("0.000001"))),
        "monthly_spend_chart": [
            {"date": day, "cost_usd": float(cost.quantize(Decimal("0.000001")))}
            for day, cost in sorted(monthly.items())
        ],
        "cost_by_model": [
            {"model": model, "cost_usd": float(cost.quantize(Decimal("0.000001")))}
            for model, cost in sorted(by_model.items(), key=lambda item: item[1], reverse=True)
        ],
        "cost_by_api_key": [
            {
                "api_key_id": key_id,
                "api_key_name": key_name_map.get(key_id),
                "label": key_name_map.get(key_id) or key_id,
                "cost_usd": float(cost.quantize(Decimal("0.000001"))),
            }
            for key_id, cost in sorted(by_key.items(), key=lambda item: item[1], reverse=True)
        ],
        "budget": {
            "id": monthly_budget.id if monthly_budget else None,
            "amount": str(monthly_budget.amount) if monthly_budget else None,
            "current_spend": str(monthly_budget.current_spend) if monthly_budget else "0",
            "remaining": str((monthly_budget.amount - monthly_budget.current_spend) if monthly_budget else Decimal("0")),
            "is_hard_stop": bool(monthly_budget and monthly_budget.amount and monthly_budget.current_spend >= monthly_budget.amount),
            "period_end": monthly_budget.period_end.isoformat() if monthly_budget else None,
        },
    }


def fetch_public_status_payload(db: Session) -> dict:
    now = datetime.utcnow()
    services = ["api", "auth", "marketplace", "ai-proxy"]
    incidents = (
        db.query(IncidentLog)
        .filter(IncidentLog.status.in_(["open", "investigating"]))
        .order_by(desc(IncidentLog.created_at))
        .limit(10)
        .all()
    )
    maintenance_alerts = (
        db.query(Alert)
        .filter(
            Alert.alert_type.in_(["maintenance", "scheduled_maintenance"]),
            Alert.status == "open",
        )
        .order_by(desc(Alert.created_at))
        .limit(10)
        .all()
    )
    uptime = {}
    for service in services:
        recent = (
            db.query(func.avg(WorkspaceRequestLog.latency_ms))
            .filter(
                WorkspaceRequestLog.request_path.ilike(f"%{service}%"),
                WorkspaceRequestLog.created_at >= now - timedelta(days=90),
            )
            .scalar()
        )
        uptime[service] = 99.99 if recent is None else max(95.0, min(99.99, 100.0 - float(recent) / 1000.0))

    return {
        "timestamp": now.isoformat(),
        "services": [
            {
                "name": "API",
                "status": "operational",
                "uptime_90d": uptime["api"],
            },
            {
                "name": "Auth",
                "status": "operational",
                "uptime_90d": uptime["auth"],
            },
            {
                "name": "Marketplace",
                "status": "operational",
                "uptime_90d": uptime["marketplace"],
            },
            {
                "name": "AI Proxy",
                "status": "operational",
                "uptime_90d": uptime["ai-proxy"],
            },
        ],
        "incidents": [
            {
                "id": incident.id,
                "title": incident.title,
                "severity": incident.severity.value,
                "status": incident.status.value,
                "created_at": incident.created_at.isoformat(),
                "description": incident.description,
            }
            for incident in incidents
        ],
        "maintenance": [
            {
                "id": item.id,
                "title": item.title,
                "severity": item.severity.value,
                "created_at": item.created_at.isoformat(),
                "description": item.description,
            }
            for item in maintenance_alerts
        ],
    }
