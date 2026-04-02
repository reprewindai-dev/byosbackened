"""Test feedback evaluation loop and anomaly auto-mitigation."""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
import uuid

import pytest
from sqlalchemy.orm import Session

from core.feedback.evaluation import get_feedback_evaluator
from core.cost_intelligence.anomaly_detector import get_anomaly_detector
from db.models import Workspace, User, AIAuditLog, AIFeedback, RoutingPolicy
from db.session import SessionLocal, engine, Base

Base.metadata.create_all(bind=engine)


@pytest.fixture
def db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def workspace(db: Session):
    ws = Workspace(
        id=str(uuid.uuid4()),
        name="Test Workspace",
        slug=f"ws-{uuid.uuid4().hex[:8]}",
        is_active=True,
    )
    db.add(ws)
    db.commit()
    db.refresh(ws)
    return ws


@pytest.fixture
def user(db: Session, workspace: Workspace):
    u = User(
        id=str(uuid.uuid4()),
        workspace_id=workspace.id,
        email=f"user-{uuid.uuid4().hex[:8]}@test.com",
        hashed_password="hashed",
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _mk_audit(
    db: Session,
    workspace_id: str,
    user_id: str,
    cost: Decimal,
    created_at: datetime,
    provider: str = "openai",
    operation_type: str = "extract",
):
    a = AIAuditLog(
        id=str(uuid.uuid4()),
        workspace_id=workspace_id,
        user_id=user_id,
        operation_type=operation_type,
        provider=provider,
        model="m",
        input_hash="in",
        output_hash="out",
        input_preview="",
        output_preview="",
        cost=cost,
        tokens_input=1,
        tokens_output=1,
        pii_detected=False,
        pii_types=[],
        sensitive_data_flags={},
        log_hash="h",
        previous_log_hash=None,
        created_at=created_at,
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


def test_feedback_evaluator_applies_quality_score(db: Session, workspace: Workspace, user: User):
    audit = _mk_audit(
        db=db,
        workspace_id=workspace.id,
        user_id=user.id,
        cost=Decimal("0.01"),
        created_at=datetime.utcnow(),
    )

    fb = AIFeedback(
        id=str(uuid.uuid4()),
        workspace_id=workspace.id,
        audit_log_id=audit.id,
        source="user",
        quality_score=Decimal("0.80"),
        created_at=datetime.utcnow(),
    )
    db.add(fb)
    db.commit()

    evaluator = get_feedback_evaluator()
    result = evaluator.apply_feedback_signals(
        db=db, workspace_id=workspace.id, lookback_hours=24, limit=100
    )

    assert result["updated_audit_logs"] >= 1
    db.refresh(audit)
    assert float(audit.actual_quality) == 0.8


def test_cost_spike_auto_mitigation_updates_policy(db: Session, workspace: Workspace, user: User):
    detector = get_anomaly_detector()

    # Create previous window audit logs (lower cost)
    now = datetime.utcnow()
    prev_start = now - timedelta(minutes=120)
    for i in range(6):
        _mk_audit(
            db=db,
            workspace_id=workspace.id,
            user_id=user.id,
            cost=Decimal("0.01"),
            created_at=prev_start + timedelta(minutes=i),
            provider="openai",
            operation_type="extract",
        )

    # Create recent window audit logs (higher cost)
    recent_start = now - timedelta(minutes=60)
    for i in range(6):
        _mk_audit(
            db=db,
            workspace_id=workspace.id,
            user_id=user.id,
            cost=Decimal("0.10"),
            created_at=recent_start + timedelta(minutes=i),
            provider="openai",
            operation_type="extract",
        )

    anomaly = detector.detect_cost_spike(
        db=db,
        workspace_id=workspace.id,
        lookback_minutes=60,
        spike_multiplier=3.0,
        min_events=5,
    )

    assert anomaly is not None
    db.refresh(anomaly)
    assert anomaly.remediated_at is not None
    assert anomaly.remediation_action is not None

    policy = db.query(RoutingPolicy).filter(RoutingPolicy.workspace_id == workspace.id).first()
    assert policy is not None
    assert policy.strategy == "cost_optimized"
    assert policy.version >= 1
