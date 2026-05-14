from __future__ import annotations

import json

import pyotp
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from apps.api.deps import get_current_user
from apps.api.routers.auth import _build_github_state, _hash_recovery_code, router as auth_router
from apps.api.routers.workspace import router as workspace_router
from core.security import get_password_hash
from core.services.workspace_profiles import ensure_workspace_profile_defaults
from db.models.product_usage_event import ProductUsageEvent
from db.models.security_audit import SecurityAuditLog
from db.models.token_wallet import TokenWallet
from db.models.user import User, UserRole, UserStatus
from db.models.user_session import UserSession
from db.models.workspace import Workspace
from db.models.workspace_github_repo_selection import WorkspaceGithubRepoSelection
from db.session import get_db


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Workspace.__table__.create(bind=engine, checkfirst=True)
User.__table__.create(bind=engine, checkfirst=True)
TokenWallet.__table__.create(bind=engine, checkfirst=True)
UserSession.__table__.create(bind=engine, checkfirst=True)
SecurityAuditLog.__table__.create(bind=engine, checkfirst=True)
WorkspaceGithubRepoSelection.__table__.create(bind=engine, checkfirst=True)
ProductUsageEvent.__table__.create(bind=engine, checkfirst=True)


class _FakeResponse:
    def __init__(self, status_code: int, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


class _FakeGithubAsyncClient:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, data=None, headers=None):
        return _FakeResponse(200, {"access_token": "gh_test_token"})

    async def get(self, url, headers=None, params=None):
        if url.endswith("/user"):
            return _FakeResponse(
                200,
                {
                    "id": 999001,
                    "login": "veklom-gh-user",
                    "name": "Veklom GH User",
                    "email": "github-linked@example.com",
                },
            )
        if url.endswith("/user/emails"):
            return _FakeResponse(200, [])
        if url.endswith("/user/repos"):
            return _FakeResponse(
                200,
                [
                    {
                        "id": 101,
                        "name": "governed-repo",
                        "full_name": "veklom/governed-repo",
                        "description": "Governed repo",
                        "html_url": "https://github.com/veklom/governed-repo",
                        "stargazers_count": 3,
                        "language": "Python",
                        "updated_at": "2026-05-13T12:00:00Z",
                        "private": True,
                        "visibility": "private",
                        "default_branch": "main",
                        "permissions": {"admin": True, "push": True, "pull": True},
                        "topics": ["governed", "ai"],
                    }
                ],
            )
        return _FakeResponse(404, {})


def _reset_db():
    db = TestingSessionLocal()
    for model in [
        ProductUsageEvent,
        WorkspaceGithubRepoSelection,
        SecurityAuditLog,
        UserSession,
        TokenWallet,
        User,
        Workspace,
    ]:
        db.query(model).delete()
    db.commit()
    return db


def _create_workspace_user(
    *,
    email: str,
    password: str = "Password1",
    workspace_name: str = "Acme Workspace",
    industry: str = "generic",
    role: UserRole = UserRole.OWNER,
    is_superuser: bool = False,
    mfa_enabled: bool = False,
    github_connected: bool = False,
):
    db = _reset_db()
    workspace = Workspace(name=workspace_name, slug=f"{workspace_name.lower().replace(' ', '-')}-slug")
    ensure_workspace_profile_defaults(workspace, industry)
    db.add(workspace)
    db.flush()
    user = User(
        email=email,
        hashed_password=get_password_hash(password),
        full_name="Operator",
        role=role,
        status=UserStatus.ACTIVE,
        is_superuser=is_superuser,
        workspace_id=workspace.id,
        github_id="999001" if github_connected else None,
        github_username="veklom-gh-user" if github_connected else None,
        github_access_token="gh_test_token" if github_connected else None,
    )
    if mfa_enabled:
        user.mfa_enabled = True
        user.mfa_secret = pyotp.random_base32()
    db.add(user)
    db.add(
        TokenWallet(
            workspace_id=workspace.id,
            balance=0,
            monthly_credits_included=0,
            monthly_credits_used=0,
            total_credits_purchased=0,
            total_credits_used=0,
        )
    )
    db.commit()
    db.refresh(workspace)
    db.refresh(user)
    return db, workspace, user


def _client_for(user: User, db_session):
    app = FastAPI()
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(workspace_router, prefix="/api/v1")

    def override_db():
        try:
            yield db_session
        finally:
            pass

    async def override_current_user():
        db_session.refresh(user)
        return user

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_current_user
    return TestClient(app)


def test_mfa_verify_generates_hashed_backup_codes_only():
    db, _workspace, user = _create_workspace_user(email="mfa-owner@example.com")
    client = _client_for(user, db)

    setup = client.post("/api/v1/auth/mfa/setup")
    assert setup.status_code == 200

    db.refresh(user)
    code = pyotp.TOTP(user.mfa_secret).now()
    verify = client.post("/api/v1/auth/mfa/verify", params={"code": code})

    assert verify.status_code == 200
    payload = verify.json()
    assert payload["mfa_enabled"] is True
    assert len(payload["backup_codes"]) == 10

    db.refresh(user)
    stored = json.loads(user.mfa_recovery_codes_json)
    assert len(stored) == 10
    assert all("code_hash" in item for item in stored)
    assert all("used_at" in item for item in stored)
    for backup_code in payload["backup_codes"]:
        assert backup_code not in user.mfa_recovery_codes_json


def test_login_accepts_unused_backup_code_and_rejects_reuse():
    db, _workspace, user = _create_workspace_user(email="backup-login@example.com")
    client = _client_for(user, db)

    client.post("/api/v1/auth/mfa/setup")
    db.refresh(user)
    verify = client.post("/api/v1/auth/mfa/verify", params={"code": pyotp.TOTP(user.mfa_secret).now()})
    backup_code = verify.json()["backup_codes"][0]

    login = client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": "Password1", "mfa_code": backup_code},
    )
    assert login.status_code == 200
    assert login.json()["access_token"]

    second = client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": "Password1", "mfa_code": backup_code},
    )
    assert second.status_code == 401
    assert second.json()["detail"] == "Invalid MFA code"


def test_admin_mfa_reset_clears_state_and_writes_audit():
    db = _reset_db()
    workspace = Workspace(name="Admin Workspace", slug="admin-workspace")
    ensure_workspace_profile_defaults(workspace, "generic")
    db.add(workspace)
    db.flush()

    admin = User(
        email="admin@example.com",
        hashed_password=get_password_hash("Password1"),
        full_name="Admin",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
        workspace_id=workspace.id,
    )
    target = User(
        email="target@example.com",
        hashed_password=get_password_hash("Password1"),
        full_name="Target",
        role=UserRole.USER,
        status=UserStatus.ACTIVE,
        workspace_id=workspace.id,
        mfa_enabled=True,
        mfa_secret=pyotp.random_base32(),
        mfa_recovery_codes_json=json.dumps([{"code_hash": "x", "used_at": None}]),
        failed_login_attempts=3,
    )
    db.add_all([admin, target])
    db.add(TokenWallet(workspace_id=workspace.id, balance=0, monthly_credits_included=0, monthly_credits_used=0, total_credits_purchased=0, total_credits_used=0))
    db.commit()
    db.refresh(admin)
    db.refresh(target)

    client = _client_for(admin, db)
    response = client.post(f"/api/v1/auth/mfa/admin-reset/{target.id}", json={"reason": "founder_recovery"})

    assert response.status_code == 200
    db.refresh(target)
    assert target.mfa_enabled is False
    assert target.mfa_secret is None
    assert target.mfa_recovery_codes_json is None
    audit = db.query(SecurityAuditLog).filter(SecurityAuditLog.event_type == "mfa_admin_reset").one()
    assert "founder_recovery" in (audit.details or "")


def test_github_callback_requires_mfa_then_completes_with_backup_code(monkeypatch):
    monkeypatch.setattr("apps.api.routers.auth.httpx.AsyncClient", _FakeGithubAsyncClient)
    db, _workspace, user = _create_workspace_user(
        email="github-linked@example.com",
        mfa_enabled=True,
    )
    plain_codes = ["BACKUP01"]
    user.mfa_recovery_codes_json = json.dumps([{"code_hash": _hash_recovery_code(plain_codes[0]), "used_at": None}])
    db.commit()
    client = _client_for(user, db)

    callback = client.post(
        "/api/v1/auth/github/callback",
        json={"code": "gh_code", "state": _build_github_state()},
    )
    assert callback.status_code == 200
    payload = callback.json()
    assert payload["mfa_required"] is True
    assert payload["github_username"] == "veklom-gh-user"

    complete = client.post(
        "/api/v1/auth/github/mfa/complete",
        json={"challenge_token": payload["mfa_challenge_token"], "mfa_code": plain_codes[0]},
    )
    assert complete.status_code == 200
    assert complete.json()["access_token"]


def test_connected_accounts_repos_selection_and_handoff_are_workspace_scoped(monkeypatch):
    monkeypatch.setattr("apps.api.routers.auth.httpx.AsyncClient", _FakeGithubAsyncClient)
    db = _reset_db()

    workspace_a = Workspace(name="Workspace A", slug="workspace-a")
    workspace_b = Workspace(name="Workspace B", slug="workspace-b")
    ensure_workspace_profile_defaults(workspace_a, "enterprise_operations")
    ensure_workspace_profile_defaults(workspace_b, "generic")
    db.add_all([workspace_a, workspace_b])
    db.flush()

    user_a = User(
        email="repo-a@example.com",
        hashed_password=get_password_hash("Password1"),
        full_name="Repo A",
        role=UserRole.OWNER,
        status=UserStatus.ACTIVE,
        workspace_id=workspace_a.id,
        github_id="999001",
        github_username="veklom-gh-user",
        github_access_token="gh_test_token",
    )
    user_b = User(
        email="repo-b@example.com",
        hashed_password=get_password_hash("Password1"),
        full_name="Repo B",
        role=UserRole.OWNER,
        status=UserStatus.ACTIVE,
        workspace_id=workspace_b.id,
    )
    db.add_all([user_a, user_b])
    db.add_all([
        TokenWallet(workspace_id=workspace_a.id, balance=0, monthly_credits_included=0, monthly_credits_used=0, total_credits_purchased=0, total_credits_used=0),
        TokenWallet(workspace_id=workspace_b.id, balance=0, monthly_credits_included=0, monthly_credits_used=0, total_credits_purchased=0, total_credits_used=0),
    ])
    db.commit()
    db.refresh(user_a)
    db.refresh(user_b)

    client_a = _client_for(user_a, db)
    connected = client_a.get("/api/v1/auth/connected-accounts")
    assert connected.status_code == 200
    assert connected.json()["github_connected"] is True

    repos = client_a.get("/api/v1/auth/github/repos")
    assert repos.status_code == 200
    assert repos.json()["repos"][0]["full_name"] == "veklom/governed-repo"

    select = client_a.post(
        "/api/v1/workspace/integrations/github/select-repo",
        json={
            "repo_full_name": "veklom/governed-repo",
            "repo_id": 101,
            "default_branch": "main",
            "visibility": "private",
            "permissions": {"admin": True, "push": True, "pull": True},
        },
    )
    assert select.status_code == 201

    integration = client_a.get("/api/v1/workspace/integrations/github")
    assert integration.status_code == 200
    assert integration.json()["selected_repos"][0]["repo_full_name"] == "veklom/governed-repo"

    handoff = client_a.post(
        "/api/v1/workspace/playground/handoff",
        json={
            "scenario_id": "ops_support_ticket_triage",
            "scenario_title": "Support ticket triage",
            "user_input": "Route urgent support tickets with evidence.",
            "selected_repo_full_name": "veklom/governed-repo",
        },
    )
    assert handoff.status_code == 201
    handoff_payload = handoff.json()
    assert handoff_payload["github_connected"] is True
    assert handoff_payload["selected_repo_full_name"] == "veklom/governed-repo"
    assert handoff_payload["repo_context_scope"] == "metadata_only"

    client_b = _client_for(user_b, db)
    other_workspace = client_b.post(
        "/api/v1/workspace/playground/handoff",
        json={
            "scenario_id": "generic_support_triage",
            "scenario_title": "Support ticket triage",
            "user_input": "Route urgent support tickets with evidence.",
            "selected_repo_full_name": "veklom/governed-repo",
        },
    )
    assert other_workspace.status_code == 400
    assert other_workspace.json()["detail"] == "Selected repo is not connected to this workspace"
