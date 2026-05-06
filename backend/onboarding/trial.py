"""Post-signup onboarding orchestration."""
from __future__ import annotations

import hashlib
import json
import logging
import secrets
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from db.models import APIKey, SecurityAuditLog, TokenWallet
from herald.resend_sequences import HeraldContact, enqueue_signup

logger = logging.getLogger(__name__)
_API_KEY_PREFIX = "byos_"


def _hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


def _current_wallet_balance(db: Session, workspace_id: str) -> int:
    wallet = db.query(TokenWallet).filter(TokenWallet.workspace_id == workspace_id).first()
    if not wallet:
        return 0
    return int(wallet.balance or 0)


def _create_trial_api_key(
    *,
    db: Session,
    workspace_id: str,
    user_id: str,
) -> str:
    raw_key = _API_KEY_PREFIX + secrets.token_urlsafe(40)
    db.add(
        APIKey(
            workspace_id=workspace_id,
            user_id=user_id,
            name="Trial evaluation key",
            key_hash=_hash_api_key(raw_key),
            key_prefix=raw_key[:12],
            scopes=["READ", "EXEC"],
            rate_limit_per_minute="60",
            allowed_ips=[],
            expires_at=None,
        )
    )
    return raw_key


def _audit_onboarding(
    *,
    db: Session,
    workspace_id: str,
    user_id: str,
    signup_type: str,
    wallet_balance: int,
    issued_api_key: bool,
) -> None:
    db.add(
        SecurityAuditLog(
            workspace_id=workspace_id,
            user_id=user_id,
            event_type="trial_onboarding",
            event_category="onboarding",
            success=True,
            details=json.dumps(
                {
                    "signup_type": signup_type,
                    "wallet_balance": wallet_balance,
                    "trial_api_key_issued": issued_api_key,
                    "generated_at": datetime.utcnow().isoformat() + "Z",
                },
                sort_keys=True,
            ),
        )
    )


async def post_signup_onboarding(
    *,
    user_id: str,
    email: str,
    first_name: str,
    workspace_id: str,
    signup_type: str,
    db: Session,
) -> dict[str, Any]:
    """Create one-time onboarding artifacts and enroll HERALD.

    This function deliberately does not grant hardcoded credits. The wallet
    balance returned is whatever the existing billing/trial logic created.
    """
    wallet_balance = _current_wallet_balance(db, workspace_id)
    raw_api_key = _create_trial_api_key(db=db, workspace_id=workspace_id, user_id=user_id)
    _audit_onboarding(
        db=db,
        workspace_id=workspace_id,
        user_id=user_id,
        signup_type=signup_type,
        wallet_balance=wallet_balance,
        issued_api_key=True,
    )
    enqueue_signup(
        HeraldContact(
            email=email,
            first_name=first_name,
            workspace_id=workspace_id,
            user_id=user_id,
            signup_type=signup_type,
        )
    )
    logger.info("post_signup_onboarding_completed workspace=%s signup_type=%s", workspace_id, signup_type)
    return {
        "api_key": raw_api_key,
        "wallet_balance": wallet_balance,
        "signup_type": signup_type,
    }
