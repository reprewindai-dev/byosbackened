from __future__ import annotations

import json
from datetime import datetime, timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from apps.api.deps import get_current_user
from apps.api.routers.admin import router as admin_router
from core.security import get_password_hash
from db.models import (
    AIAuditLog,
    APIKey,
    Deployment,
    Export,
    Job,
    Pipeline,
    PipelineRun,
    ProductUsageEvent,
    RoutingDecision,
    SecurityAuditLog,
    Subscription,
    User,
    UserRole,
    UserSession,
    UserStatus,
    Workspace,
    WorkspaceGithubRepoSelection,
    WorkspaceInvite,
    WorkspaceRequestLog,
)
from db.session import Base, get_db


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Importing the model classes above registers the relevant tables and FK targets.
Base.metadata.create_all(bind=engine)


def _reset_db():
    db = TestingSessionLocal()
    for model in [
        SecurityAuditLog,
        ProductUsageEvent,
        WorkspaceGithubRepoSelection,
        UserSession,
        WorkspaceRequestLog,
        WorkspaceInvite,
        APIKey,
        PipelineRun,
        Pipeline,
        Deployment,
        Export,
        AIAuditLog,
        RoutingDecision,
        Job,
        Subscription,
        User,
        Workspace,
    ]:
        db.query(model).delete()
    db.commit()
    return db


def _client_for(user: User):
    app = FastAPI()
    app.include_router(admin_router, prefix="/api/v1")

    def override_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    async def override_user():
        return user

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_user
    return TestClient(app)


def _seed_superuser_world():
    db = _reset_db()
    workspace = Workspace(
        name="Acme Regulated",
        slug="acme-regulated",
        industry="healthcare_hospital",
        playground_profile="healthcare_hospital",
        risk_tier="regulated",
    )
    db.add(workspace)
    db.flush()
    user = User(
        email="founder@example.com",
        hashed_password=get_password_hash("Password1"),
        full_name="Founder",
        role=UserRole.OWNER,
        status=UserStatus.ACTIVE,
        is_superuser=True,
        workspace_id=workspace.id,
        mfa_enabled=True,
    )
    db.add(user)
    db.flush()
    now = datetime.utcnow()
    db.add(
        UserSession(
            user_id=user.id,
            session_token="session-token",
            refresh_token="refresh-token",
            created_at=now - timedelta(minutes=11),
            expires_at=now + timedelta(hours=1),
            last_accessed=now,
            is_active=True,
        )
    )
    db.add(Subscription(workspace_id=workspace.id, status="active", plan="sovereign"))
    db.add(
        ProductUsageEvent(
            workspace_id=workspace.id,
            user_id=user.id,
            session_id="session-token",
            event_type="feature_use",
            surface="playground",
            route="/playground",
            feature="gpc_handoff_prepared",
            duration_ms=120000,
            metadata_json=json.dumps(
                {
                    "scenario_title": "PHI redaction check",
                    "prompt_category": "healthcare_triage",
                    "prompt": "RAW PATIENT TEXT MUST NOT BE RETURNED",
                    "evidence_requirements": ["PHI handling", "audit log"],
                    "blocking_rules": ["no external fallback"],
                }
            ),
        )
    )
    db.add(
        WorkspaceGithubRepoSelection(
            workspace_id=workspace.id,
            user_id=user.id,
            repo_full_name="veklom/private-runtime",
            repo_id=123,
            default_branch="main",
            selected_by=user.id,
        )
    )
    db.commit()
    db.refresh(user)
    return user


def test_command_center_requires_superuser():
    db = _reset_db()
    workspace = Workspace(name="Tenant", slug="tenant")
    db.add(workspace)
    db.flush()
    user = User(
        email="tenant@example.com",
        hashed_password=get_password_hash("Password1"),
        role=UserRole.USER,
        status=UserStatus.ACTIVE,
        is_superuser=False,
        workspace_id=workspace.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    client = _client_for(user)
    response = client.get("/api/v1/admin/command-center")

    assert response.status_code == 403


def test_command_center_returns_real_and_not_wired_metrics_without_raw_prompt_leak():
    user = _seed_superuser_world()
    client = _client_for(user)

    response = client.get("/api/v1/admin/command-center")

    assert response.status_code == 200
    payload = response.json()
    assert payload["overview"]["title"] == "Overview"
    assert payload["workspace_spine"]["sovereign_mode"] == "ON-PREM"
    assert any(section["key"] == "gpc" for section in payload["module_intelligence"])
    assert any(metric["status"] == "not_wired" for metric in payload["system_health"]["metrics"])
    assert payload["heatmap"]["rows"][0]["status"] in {"commercially_serious", "evaluation_ready"}
    serialized = json.dumps(payload)
    assert "RAW PATIENT TEXT MUST NOT BE RETURNED" not in serialized
    assert "command_center_access" in serialized
