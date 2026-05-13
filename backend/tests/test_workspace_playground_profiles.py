from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from apps.api.deps import get_current_user, require_superuser
from apps.api.routers.admin import router as admin_router
from apps.api.routers.telemetry import router as telemetry_router
from apps.api.routers.workspace import router as workspace_router
from core.services.workspace_profiles import ensure_workspace_profile_defaults
from db.models.commercial_artifact import CommercialArtifact
from db.models.product_usage_event import ProductUsageEvent
from db.models.user import User, UserRole, UserStatus
from db.models.workspace import Workspace
from db.session import get_db


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Workspace.__table__.create(bind=engine, checkfirst=True)
User.__table__.create(bind=engine, checkfirst=True)
ProductUsageEvent.__table__.create(bind=engine, checkfirst=True)
CommercialArtifact.__table__.create(bind=engine, checkfirst=True)


def _build_workspace_user(*, industry: str = "healthcare_hospital", superuser: bool = False):
    db = TestingSessionLocal()
    db.query(CommercialArtifact).delete()
    db.query(ProductUsageEvent).delete()
    db.query(User).delete()
    db.query(Workspace).delete()
    workspace = Workspace(name="Acme Health", slug="acme-health")
    ensure_workspace_profile_defaults(workspace, industry)
    user = User(
        email="owner@example.com" if not superuser else "root@example.com",
        hashed_password="not-used",
        full_name="Owner",
        role=UserRole.OWNER,
        status=UserStatus.ACTIVE,
        is_superuser=superuser,
        workspace_id=workspace.id,
    )
    db.add(workspace)
    db.flush()
    user.workspace_id = workspace.id
    db.add(user)
    db.commit()
    db.refresh(workspace)
    db.refresh(user)
    return db, workspace, user


def _client_for(user: User, db_session):
    app = FastAPI()
    app.include_router(workspace_router, prefix="/api/v1")
    app.include_router(admin_router, prefix="/api/v1")
    app.include_router(telemetry_router, prefix="/api/v1")

    def override_db():
        try:
            yield db_session
        finally:
            pass

    async def override_current_user():
        return user

    async def override_superuser():
        return user

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[require_superuser] = override_superuser
    return TestClient(app)


def test_workspace_playground_profile_returns_vertical_defaults():
    db, workspace, user = _build_workspace_user(industry="healthcare_hospital")
    client = _client_for(user, db)

    response = client.get("/api/v1/workspace/playground/profile")

    assert response.status_code == 200
    payload = response.json()
    assert payload["workspaceId"] == workspace.id
    assert payload["tenantId"] == workspace.id
    assert payload["industry"] == "healthcare_hospital"
    assert payload["playground_profile"] == "healthcare_hospital"
    assert payload["risk_tier"] == "regulated"
    assert payload["policy_pack"] == "healthcare_phi_guardrails_v1"
    assert payload["regulated_defaults"]["human_review_required_for_high_risk"] is True
    scenario_titles = {item["title"] for item in payload["default_demo_scenarios"]}
    assert "Patient intake summary" in scenario_titles
    assert "PHI redaction check" in scenario_titles


def test_playground_handoff_and_commercial_artifact_flow_updates_scorecard():
    db, workspace, user = _build_workspace_user(industry="banking_fintech", superuser=True)
    client = _client_for(user, db)

    handoff_response = client.post(
        "/api/v1/workspace/playground/handoff",
        json={
            "scenario_id": "banking_suspicious_transaction_triage",
            "scenario_title": "Suspicious transaction triage",
            "user_input": "Route urgent transaction alerts and preserve the review trail.",
        },
    )
    assert handoff_response.status_code == 201
    handoff = handoff_response.json()
    assert handoff["handoff_status"] == "prepared"
    assert handoff["claim_level"] == "draft"
    assert handoff["industry"] == "banking_fintech"
    assert handoff["scenario_id"] == "banking_suspicious_transaction_triage"

    artifact_response = client.post(
        "/api/v1/workspace/commercial/community-awareness-run",
        json={
            "title": "Banking suspicious transaction founder-review draft",
            "handoff": handoff,
            "community_or_source": "linkedin",
            "audience_type": "ai_platform_ops_compliance",
            "pain_signal": "Demo works but approval path is missing.",
            "why_veklom_fits": "Governed workflow plus replay evidence.",
            "suggested_reply_or_post": "The workflow needs policy, approval, and replay before rollout.",
            "cta": "Try the GPC demo",
        },
    )
    assert artifact_response.status_code == 201
    artifact = artifact_response.json()
    assert artifact["founderReviewStatus"] == "pending_founder_review"
    assert artifact["artifact"]["run_type"] == "Community Awareness Run"
    assert artifact["artifact"]["rules"]["auto_posting"] is False

    approve_response = client.patch(
        f"/api/v1/workspace/commercial/artifacts/{artifact['id']}",
        json={"founder_review_status": "approved_by_founder", "outcome": "founder_review_complete"},
    )
    assert approve_response.status_code == 200
    assert approve_response.json()["founderReviewStatus"] == "approved_by_founder"

    mark_eval = client.post(
        "/api/v1/telemetry/events",
        json={
            "events": [
                {
                    "event_type": "feature_use",
                    "surface": "playground",
                    "route": "/playground",
                    "feature": "vertical_demo_generated",
                    "metadata": {"scenario_id": handoff["scenario_id"], "industry": handoff["industry"]},
                },
                {
                    "event_type": "feature_use",
                    "surface": "playground",
                    "route": "/playground",
                    "feature": "evaluation_conversation_influenced_by_vertical_demo",
                    "metadata": {"scenario_id": handoff["scenario_id"], "industry": handoff["industry"]},
                },
            ]
        },
    )
    assert mark_eval.status_code == 200

    workspace_scorecard = client.get("/api/v1/workspace/commercial/scorecard")
    assert workspace_scorecard.status_code == 200
    counters = workspace_scorecard.json()["counters"]
    assert counters["vertical_demos_generated"] == 1
    assert counters["gpc_handoffs_prepared"] == 1
    assert counters["founder_reviewed_vertical_artifacts"] == 1
    assert counters["evaluation_conversations_influenced_by_vertical_demo"] == 1

    admin_scorecard = client.get("/api/v1/admin/commercial-scorecard")
    assert admin_scorecard.status_code == 200
    admin_payload = admin_scorecard.json()
    assert admin_payload["vertical_demos_generated"] == 1
    assert admin_payload["gpc_handoffs_prepared"] == 1
    assert admin_payload["founder_reviewed_vertical_artifacts"] == 1
