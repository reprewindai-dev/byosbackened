"""Seed the first-party Veklom Backend marketplace listing.

This script is idempotent and safe to run during production deploys after
migrations. It guarantees the public marketplace has at least the core Veklom
Backend product available as an active listing.
"""
import os
import secrets
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.security import get_password_hash
from db.session import SessionLocal
from db.models import Workspace, User, UserRole, UserStatus, Vendor, Listing


WORKSPACE_SLUG = "veklom-first-party"
OWNER_EMAIL = os.getenv("MARKETPLACE_FIRST_PARTY_EMAIL", "marketplace@veklom.com")
LISTING_TITLE = "Veklom Backend"
LISTING_DESCRIPTION = (
    "The governed AI backend control layer behind Veklom: token-metered API "
    "execution, workspace API keys, audit-aware routing, cost controls, "
    "subscription access, marketplace payments, and sovereign-ready deployment "
    "paths for regulated teams."
)


def seed() -> None:
    db = SessionLocal()
    try:
        workspace = db.query(Workspace).filter(Workspace.slug == WORKSPACE_SLUG).first()
        if not workspace:
            workspace = Workspace(
                name="Veklom First Party",
                slug=WORKSPACE_SLUG,
                is_active=True,
            )
            db.add(workspace)
            db.flush()

        user = db.query(User).filter(User.email == OWNER_EMAIL).first()
        if not user:
            user = User(
                email=OWNER_EMAIL,
                hashed_password=get_password_hash(
                    os.getenv("MARKETPLACE_FIRST_PARTY_PASSWORD") or secrets.token_urlsafe(48)
                ),
                full_name="Veklom Marketplace",
                workspace_id=workspace.id,
                role=UserRole.OWNER,
                status=UserStatus.ACTIVE,
                is_active=True,
                is_superuser=True,
            )
            db.add(user)
            db.flush()

        vendor = db.query(Vendor).filter(Vendor.user_id == user.id).first()
        if not vendor:
            vendor = Vendor(
                user_id=user.id,
                workspace_id=workspace.id,
                display_name="Veklom",
                plan="sovereign",
                subscription_status="active",
                is_onboarded=True,
            )
            db.add(vendor)
            db.flush()

        listing = db.query(Listing).filter(
            Listing.vendor_id == vendor.id,
            Listing.title == LISTING_TITLE,
        ).first()
        if not listing:
            listing = Listing(
                vendor_id=vendor.id,
                workspace_id=workspace.id,
                title=LISTING_TITLE,
                description=LISTING_DESCRIPTION,
                price_cents=0,
                currency="usd",
                status="active",
            )
            db.add(listing)
        else:
            listing.description = LISTING_DESCRIPTION
            listing.price_cents = 0
            listing.currency = "usd"
            listing.status = "active"

        db.commit()
        print(f"Seeded active listing: {LISTING_TITLE}")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
