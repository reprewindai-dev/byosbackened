from __future__ import annotations

import asyncio
import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from apps.api.routers.auth import FREE_TRIAL_CREDITS, _totp_qr_data_uri
from db.models import APIKey, SecurityAuditLog, TokenWallet
from herald.resend_sequences import HeraldContact, build_sequence
from onboarding import trial as trial_onboarding


def test_free_evaluation_no_longer_grants_hardcoded_50k_credits():
    assert FREE_TRIAL_CREDITS == 0


def test_mfa_qr_uses_csp_safe_data_uri():
    qr_url = _totp_qr_data_uri("otpauth://totp/Veklom:buyer@example.com?secret=ABCDEF&issuer=Veklom")

    assert qr_url.startswith("data:image/svg+xml;base64,")
    assert "api.qrserver.com" not in qr_url


def test_herald_sequences_do_not_advertise_50k_trial_credit_pool():
    contact = HeraldContact(
        email="buyer@example.com",
        first_name="Buyer",
        workspace_id="workspace-1",
        user_id="user-1",
        signup_type="regulated",
    )

    content = "\n".join(
        f"{message.subject}\n{message.text}\n{message.html}" for message in build_sequence(contact)
    ).lower()

    assert "50k" not in content
    assert "50,000" not in content
    assert "50000" not in content
    assert "unlimited token pool" in content
    assert "entitlement and usage controls" in content


def test_post_signup_onboarding_returns_actual_wallet_balance_without_granting_credits(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for table in (TokenWallet.__table__, APIKey.__table__, SecurityAuditLog.__table__):
        table.create(engine, checkfirst=True)
    session_factory = sessionmaker(bind=engine)
    db = session_factory()
    db.add(TokenWallet(workspace_id="workspace-1", balance=1234))
    db.commit()

    scheduled = []
    monkeypatch.setattr(trial_onboarding, "enqueue_signup", lambda contact: scheduled.append(contact))

    result = asyncio.run(
        trial_onboarding.post_signup_onboarding(
            user_id="user-1",
            email="buyer@example.com",
            first_name="Buyer",
            workspace_id="workspace-1",
            signup_type="regulated",
            db=db,
        )
    )

    api_key = db.query(APIKey).one()
    audit = db.query(SecurityAuditLog).one()
    details = json.loads(audit.details)

    assert result["api_key"].startswith("byos_")
    assert result["wallet_balance"] == 1234
    assert api_key.name == "Trial evaluation key"
    assert api_key.scopes == ["READ", "EXEC"]
    assert details["wallet_balance"] == 1234
    assert details["trial_api_key_issued"] is True
    assert scheduled[0].email == "buyer@example.com"
