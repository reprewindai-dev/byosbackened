"""Test strict vs fallback provider allowlist enforcement."""

import json
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from apps.api.main import app
from core.security import create_access_token
from db.models import Workspace, User, RoutingPolicy, Asset
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


@pytest.fixture
def token(workspace: Workspace, user: User):
    return create_access_token(
        data={"sub": user.email, "workspace_id": workspace.id, "user_id": user.id}
    )


@pytest.fixture
def asset(db: Session, workspace: Workspace):
    a = Asset(
        id=str(uuid.uuid4()),
        workspace_id=workspace.id,
        filename="f.wav",
        original_filename="f.wav",
        content_type="audio/wav",
        file_size=123,
        s3_key=f"k-{uuid.uuid4().hex}",
        s3_bucket="b",
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


class DummyChatResult:
    def __init__(self):
        self.content = "ok"
        self.model = "dummy"


class DummyProvider:
    def __init__(self, name: str):
        self._name = name

    def get_name(self):
        return self._name

    async def chat(self, messages, temperature=0.7):
        return DummyChatResult()


def test_extract_strict_blocks_disallowed_provider(
    db: Session, workspace: Workspace, token: str, monkeypatch
):
    policy = RoutingPolicy(
        workspace_id=workspace.id,
        strategy="cost_optimized",
        constraints_json=json.dumps(
            {"allowed_providers": ["huggingface"], "enforcement_mode": "strict"}
        ),
        enabled=True,
        version=1,
    )
    db.add(policy)
    db.commit()

    from apps.api.routers import extract as extract_router

    def _dummy_get_llm_provider(_db, _workspace_id, provider_name):
        return DummyProvider(provider_name)

    monkeypatch.setattr(
        extract_router.provider_factory, "get_llm_provider", _dummy_get_llm_provider
    )

    client = TestClient(app)
    resp = client.post(
        "/api/v1/extract",
        headers={"Authorization": f"Bearer {token}"},
        json={"task": "summary", "text": "hello", "provider": "openai"},
    )
    assert resp.status_code == 403
    body = resp.json()
    assert body["detail"]["error_code"] == "PROVIDER_NOT_ALLOWED"
    assert "openai" in body["detail"]["message"]
    assert body["detail"]["allowed_providers"] == ["huggingface"]


def test_extract_fallback_swaps_provider_and_warns(
    db: Session, workspace: Workspace, token: str, monkeypatch
):
    policy = RoutingPolicy(
        workspace_id=workspace.id,
        strategy="cost_optimized",
        constraints_json=json.dumps(
            {"allowed_providers": ["huggingface"], "enforcement_mode": "fallback"}
        ),
        enabled=True,
        version=1,
    )
    db.add(policy)
    db.commit()

    from apps.api.routers import extract as extract_router

    def _dummy_get_llm_provider(_db, _workspace_id, provider_name):
        return DummyProvider(provider_name)

    monkeypatch.setattr(
        extract_router.provider_factory, "get_llm_provider", _dummy_get_llm_provider
    )

    client = TestClient(app)
    resp = client.post(
        "/api/v1/extract",
        headers={"Authorization": f"Bearer {token}"},
        json={"task": "summary", "text": "hello", "provider": "openai"},
    )
    assert resp.status_code == 200
    assert resp.headers.get("warning") == "ProviderNotAllowedFallbackApplied"
    body = resp.json()
    assert body["requested_provider"] == "openai"
    assert body["resolved_provider"] == "huggingface"
    assert body["policy_enforcement"] == "fallback"
    assert body["was_fallback"] is True


def test_transcribe_strict_blocks_disallowed_provider(
    db: Session, workspace: Workspace, token: str, asset: Asset
):
    policy = RoutingPolicy(
        workspace_id=workspace.id,
        strategy="cost_optimized",
        constraints_json=json.dumps(
            {"allowed_providers": ["huggingface"], "enforcement_mode": "strict"}
        ),
        enabled=True,
        version=1,
    )
    db.add(policy)
    db.commit()

    client = TestClient(app)
    resp = client.post(
        "/api/v1/transcribe",
        headers={"Authorization": f"Bearer {token}"},
        json={"asset_id": asset.id, "provider": "openai"},
    )
    assert resp.status_code == 403
    body = resp.json()
    assert body["detail"]["error_code"] == "PROVIDER_NOT_ALLOWED"
    assert body["detail"]["allowed_providers"] == ["huggingface"]


def test_transcribe_fallback_swaps_provider_and_warns(
    db: Session, workspace: Workspace, token: str, asset: Asset
):
    policy = RoutingPolicy(
        workspace_id=workspace.id,
        strategy="cost_optimized",
        constraints_json=json.dumps(
            {"allowed_providers": ["huggingface"], "enforcement_mode": "fallback"}
        ),
        enabled=True,
        version=1,
    )
    db.add(policy)
    db.commit()

    client = TestClient(app)
    resp = client.post(
        "/api/v1/transcribe",
        headers={"Authorization": f"Bearer {token}"},
        json={"asset_id": asset.id, "provider": "openai"},
    )
    assert resp.status_code == 200
    assert resp.headers.get("warning") == "ProviderNotAllowedFallbackApplied"
    body = resp.json()
    assert body["requested_provider"] == "openai"
    assert body["resolved_provider"] == "huggingface"
    assert body["policy_enforcement"] == "fallback"
    assert body["was_fallback"] is True
