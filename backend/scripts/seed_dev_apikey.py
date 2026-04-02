"""
Seed a dev workspace + user + API key for local testing.

Usage (from backend/ directory):
    python scripts/seed_dev_apikey.py

Output:
    Prints the raw API key to copy into your .env or curl commands.
    The key is only shown ONCE — it's stored hashed in the DB.

Run after migrations:
    alembic upgrade head
    python scripts/seed_dev_apikey.py
"""
import hashlib
import secrets
import sys
import os

# Add backend root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.session import SessionLocal
from db.models.workspace import Workspace
from db.models.user import User, UserRole, UserStatus
from db.models.api_key import APIKey
from core.security.auth_utils import get_password_hash


DEV_WORKSPACE_NAME = "dev-local"
DEV_WORKSPACE_SLUG = "dev-local"
DEV_USER_EMAIL = "dev@byos.local"
DEV_USER_PASSWORD = "devpassword123"
DEV_APIKEY_NAME = "dev-local-key"


def seed():
    db = SessionLocal()
    try:
        # ── Workspace ─────────────────────────────────────────────────────────
        workspace = db.query(Workspace).filter(Workspace.slug == DEV_WORKSPACE_SLUG).first()
        if not workspace:
            workspace = Workspace(
                name=DEV_WORKSPACE_NAME,
                slug=DEV_WORKSPACE_SLUG,
                is_active=True,
            )
            db.add(workspace)
            db.flush()
            print(f"[seed] Created workspace: {workspace.id} ({workspace.slug})")
        else:
            print(f"[seed] Workspace exists: {workspace.id} ({workspace.slug})")

        # ── User ──────────────────────────────────────────────────────────────
        user = db.query(User).filter(User.email == DEV_USER_EMAIL).first()
        if not user:
            user = User(
                email=DEV_USER_EMAIL,
                hashed_password=get_password_hash(DEV_USER_PASSWORD),
                full_name="Dev User",
                role=UserRole.OWNER,
                status=UserStatus.ACTIVE,
                is_active=True,
                is_superuser=True,
                workspace_id=workspace.id,
            )
            db.add(user)
            db.flush()
            print(f"[seed] Created user: {user.id} ({user.email})")
        else:
            print(f"[seed] User exists: {user.id} ({user.email})")

        # ── API Key ───────────────────────────────────────────────────────────
        existing = (
            db.query(APIKey)
            .filter(APIKey.workspace_id == workspace.id, APIKey.name == DEV_APIKEY_NAME)
            .first()
        )
        if existing:
            print(f"[seed] API key '{DEV_APIKEY_NAME}' already exists (cannot show raw key again)")
            print(f"       Delete it from the DB and re-run to generate a fresh key.")
            db.close()
            return

        raw_key = "byos_" + secrets.token_hex(32)
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        prefix = raw_key[:12]

        api_key = APIKey(
            workspace_id=workspace.id,
            user_id=user.id,
            name=DEV_APIKEY_NAME,
            key_hash=key_hash,
            key_prefix=prefix,
            scopes=["exec", "read", "write"],
            rate_limit_per_minute="120",
            is_active=True,
        )
        db.add(api_key)
        db.commit()

        print()
        print("=" * 60)
        print("  DEV API KEY (copy this — shown only once)")
        print("=" * 60)
        print(f"  {raw_key}")
        print("=" * 60)
        print()
        print(f"  workspace_id : {workspace.id}")
        print(f"  user_email   : {DEV_USER_EMAIL}")
        print(f"  user_password: {DEV_USER_PASSWORD}")
        print()
        print("  Test /v1/exec:")
        print(f"  curl -X POST http://localhost:8000/v1/exec \\")
        print(f'    -H "X-API-Key: {raw_key}" \\')
        print(f'    -H "Content-Type: application/json" \\')
        print(f"    -d '{{\"prompt\": \"Say hello in one sentence.\"}}'")
        print()
        print("  Test /status:")
        print("  curl http://localhost:8000/status")
        print()

    except Exception as exc:
        db.rollback()
        print(f"[seed] ERROR: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
