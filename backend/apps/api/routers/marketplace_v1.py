"""Marketplace V1 endpoints: vendors, listings, files, evidence, orders, payments, payouts."""
from datetime import datetime
import json
import uuid
from typing import Optional

import boto3
import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from apps.api.deps import get_current_user
from core.config import get_settings
from core.services.marketplace_catalog import real_marketplace_catalog
from db.models import (
    User,
    Vendor,
    Listing,
    MarketplaceFile,
    EvidencePackage,
    MarketplaceOrder,
    MarketplaceOrderItem,
    MarketplacePayout,
)
from db.session import get_db

router = APIRouter(tags=["marketplace-v1"])
settings = get_settings()
_PAID_VENDOR_PLANS = {"verified", "sovereign"}
_LISTING_VENDOR_EDITABLE_STATUSES = {"draft", "pending_review", "rejected"}
_LISTING_PUBLIC_STATUSES = {"active"}


def _is_marketplace_admin(user: User) -> bool:
    role = (getattr(user.role, "value", user.role) or "")
    role = str(role).lower()
    admin_emails = {e.strip().lower() for e in (settings.marketplace_admin_emails or []) if e}
    return bool(user.is_superuser) or role in {"admin"} or user.email.lower() in admin_emails


def _vendor_has_paid_marketplace_access(vendor: Vendor) -> bool:
    return (
        (vendor.subscription_status or "").lower() == "active"
        and (vendor.plan or "").lower() in _PAID_VENDOR_PLANS
    )


def _db_listing_payload(x: Listing) -> dict:
    return {
        "id": x.id,
        "vendor_id": x.vendor_id,
        "title": x.title,
        "provider": "Veklom",
        "category": "Managed Services",
        "description": x.description,
        "positioning": x.description,
        "price": "Free" if not x.price_cents else f"${x.price_cents / 100:,.0f}",
        "price_cents": x.price_cents,
        "currency": x.currency,
        "billing": "free" if not x.price_cents else "external",
        "install": "Veklom account",
        "target": ["veklom"],
        "rating": 5.0,
        "installs": 1,
        "badges": ["First-party", "Live backend", "Governed API"],
        "featured": True,
        "compliance": ["SOC2"],
        "source_url": "https://veklom.com/marketplace/",
        "use_url": "https://veklom.com/signup/",
        "status": x.status,
        "created_at": x.created_at.isoformat(),
    }


def _require_vendor(db: Session, user: User) -> Vendor:
    vendor = db.query(Vendor).filter(Vendor.user_id == user.id).first()
    if not vendor:
        raise HTTPException(status_code=403, detail="Vendor subscription required")
    return vendor


class VendorCreateRequest(BaseModel):
    display_name: str = Field(..., min_length=2, max_length=120)


@router.post("/vendors/create")
async def vendors_create(
    payload: VendorCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    existing = db.query(Vendor).filter(Vendor.user_id == current_user.id).first()
    if not existing:
        if not _is_marketplace_admin(current_user):
            raise HTTPException(status_code=403, detail="Vendor subscription required")
        # Admin bypass: bootstrap vendor profile without paid vendor plan.
        existing = Vendor(
            user_id=current_user.id,
            workspace_id=current_user.workspace_id,
            display_name=payload.display_name.strip(),
            plan="verified",
            subscription_status="inactive",
        )
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return {
            "id": existing.id,
            "display_name": existing.display_name,
            "is_onboarded": existing.is_onboarded,
            "plan": existing.plan,
            "subscription_status": existing.subscription_status,
            "admin_bypass": True,
        }

    if not _is_marketplace_admin(current_user) and not _vendor_has_paid_marketplace_access(existing):
        raise HTTPException(status_code=403, detail="Active paid vendor plan required")
    existing.display_name = payload.display_name.strip()
    db.commit()
    db.refresh(existing)
    return {
        "id": existing.id,
        "display_name": existing.display_name,
        "is_onboarded": existing.is_onboarded,
        "plan": existing.plan,
        "subscription_status": existing.subscription_status,
    }


@router.post("/vendors/onboard")
async def vendors_onboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Stripe is not configured")
    stripe.api_key = settings.stripe_secret_key
    vendor = _require_vendor(db, current_user)
    if not vendor.stripe_account_id:
        acct = stripe.Account.create(type="express", email=current_user.email)
        vendor.stripe_account_id = acct["id"]
        db.commit()
    link = stripe.AccountLink.create(
        account=vendor.stripe_account_id,
        refresh_url="https://veklom.com/dashboard",
        return_url="https://veklom.com/dashboard",
        type="account_onboarding",
    )
    return {"onboarding_url": link.url, "stripe_account_id": vendor.stripe_account_id}


@router.get("/vendors/{vendor_id}")
async def vendors_get(
    vendor_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id, Vendor.workspace_id == current_user.workspace_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return {
        "id": vendor.id,
        "display_name": vendor.display_name,
        "stripe_account_id": vendor.stripe_account_id,
        "is_onboarded": vendor.is_onboarded,
        "plan": vendor.plan,
        "subscription_status": vendor.subscription_status,
        "created_at": vendor.created_at.isoformat(),
    }


class ListingCreateRequest(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = None
    price_cents: int = Field(..., ge=0)
    currency: str = Field(default="usd", min_length=3, max_length=3)


@router.post("/listings/create")
async def listings_create(
    payload: ListingCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    vendor = db.query(Vendor).filter(Vendor.user_id == current_user.id).first()
    if not vendor:
        if not _is_marketplace_admin(current_user):
            raise HTTPException(status_code=403, detail="Vendor subscription required")
        # Admin bypass: allow listing creation by bootstrapping a vendor record.
        vendor = Vendor(
            user_id=current_user.id,
            workspace_id=current_user.workspace_id,
            display_name=(current_user.full_name or current_user.email.split("@")[0]).strip(),
            plan="verified",
            subscription_status="inactive",
        )
        db.add(vendor)
        db.commit()
        db.refresh(vendor)

    if not _is_marketplace_admin(current_user) and not _vendor_has_paid_marketplace_access(vendor):
        raise HTTPException(status_code=403, detail="Active paid vendor plan required")
    listing = Listing(
        vendor_id=vendor.id,
        workspace_id=current_user.workspace_id,
        title=payload.title.strip(),
        description=(payload.description or "").strip(),
        price_cents=payload.price_cents,
        currency=payload.currency.lower(),
        status="draft",
    )
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return {"id": listing.id, "status": listing.status}


@router.get("/listings")
async def listings_list(
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(Listing)
    if status_filter:
        q = q.filter(Listing.status == status_filter.strip().lower())
    else:
        q = q.filter(Listing.status.in_(_LISTING_PUBLIC_STATUSES))
    rows = q.order_by(Listing.created_at.desc()).all()
    catalog_rows = real_marketplace_catalog()
    db_rows = [_db_listing_payload(x) for x in rows]
    return catalog_rows + db_rows


@router.get("/categories")
async def listings_categories(db: Session = Depends(get_db)):
    rows = real_marketplace_catalog()
    rows.extend(
        _db_listing_payload(row)
        for row in db.query(Listing).filter(Listing.status.in_(_LISTING_PUBLIC_STATUSES)).all()
    )
    total = len(rows)
    paid = sum(1 for row in rows if row.get("price_cents") and row["price_cents"] > 0)
    free = total - paid
    categories: dict[str, int] = {}
    for row in rows:
        category = row.get("category") or "Other"
        categories[category] = categories.get(category, 0) + 1
    return [
        {"id": "all", "label": "All", "count": total},
        {"id": "paid", "label": "Paid", "count": paid},
        {"id": "free", "label": "Free", "count": free},
        *[
            {"id": key.lower().replace(" ", "-"), "label": key, "count": value}
            for key, value in sorted(categories.items())
        ],
    ]


@router.get("/listings/{listing_id}")
async def listings_get(listing_id: str, db: Session = Depends(get_db)):
    for listing in real_marketplace_catalog():
        if listing["id"] == listing_id:
            return listing
    x = db.query(Listing).filter(Listing.id == listing_id).first()
    if not x:
        raise HTTPException(status_code=404, detail="Listing not found")
    return {
        "id": x.id,
        "vendor_id": x.vendor_id,
        "title": x.title,
        "description": x.description,
        "price_cents": x.price_cents,
        "currency": x.currency,
        "status": x.status,
        "created_at": x.created_at.isoformat(),
        "updated_at": x.updated_at.isoformat(),
    }


class ListingPatchRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    price_cents: Optional[int] = Field(default=None, ge=0)
    currency: Optional[str] = None
    status: Optional[str] = None


@router.patch("/listings/{listing_id}")
async def listings_patch(
    listing_id: str,
    payload: ListingPatchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    vendor = _require_vendor(db, current_user)
    is_admin = _is_marketplace_admin(current_user)
    if not is_admin and not _vendor_has_paid_marketplace_access(vendor):
        raise HTTPException(status_code=403, detail="Active paid vendor plan required")
    x = db.query(Listing).filter(Listing.id == listing_id, Listing.vendor_id == vendor.id).first()
    if not x:
        raise HTTPException(status_code=404, detail="Listing not found")
    if not is_admin and x.status not in _LISTING_VENDOR_EDITABLE_STATUSES:
        raise HTTPException(status_code=409, detail="Listing is locked while under review or published")
    if payload.title is not None:
        x.title = payload.title.strip()
    if payload.description is not None:
        x.description = payload.description.strip()
    if payload.price_cents is not None:
        x.price_cents = payload.price_cents
    if payload.currency is not None:
        x.currency = payload.currency.lower()
    if payload.status is not None:
        next_status = payload.status.strip().lower()
        if next_status not in {"draft", "pending_review"}:
            raise HTTPException(status_code=400, detail="Invalid listing status")
        x.status = next_status
    x.updated_at = datetime.utcnow()
    db.commit()
    return {"id": x.id, "status": x.status}


class ListingSubmitRequest(BaseModel):
    listing_id: str


@router.post("/listings/submit")
async def listings_submit(
    payload: ListingSubmitRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    vendor = _require_vendor(db, current_user)
    is_admin = _is_marketplace_admin(current_user)
    if not is_admin and not _vendor_has_paid_marketplace_access(vendor):
        raise HTTPException(status_code=403, detail="Active paid vendor plan required")

    listing = db.query(Listing).filter(Listing.id == payload.listing_id, Listing.vendor_id == vendor.id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    if not is_admin and listing.status not in {"draft", "rejected"}:
        raise HTTPException(status_code=409, detail="Listing cannot be submitted from current status")

    listing.status = "pending_review"
    listing.updated_at = datetime.utcnow()
    db.commit()
    return {"id": listing.id, "status": listing.status}


class ListingReviewRequest(BaseModel):
    listing_id: str
    status: str = Field(..., description="active|rejected|disabled|draft")
    note: Optional[str] = Field(default=None, max_length=500)


@router.post("/listings/review")
async def listings_review(
    payload: ListingReviewRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not _is_marketplace_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")

    target_status = payload.status.strip().lower()
    if target_status not in {"active", "rejected", "disabled", "draft"}:
        raise HTTPException(status_code=400, detail="Invalid review status")

    listing = db.query(Listing).filter(Listing.id == payload.listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing.status not in {"pending_review", "active", "rejected", "disabled", "draft"}:
        raise HTTPException(status_code=409, detail="Listing is not in a reviewable state")

    listing.status = target_status
    listing.updated_at = datetime.utcnow()
    db.commit()
    return {
        "id": listing.id,
        "status": listing.status,
        "reviewed_by": current_user.email,
        "note": (payload.note or "").strip(),
    }


@router.get("/vendors/me/listings")
async def vendors_me_listings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    vendor = _require_vendor(db, current_user)
    is_admin = _is_marketplace_admin(current_user)
    if not is_admin and not _vendor_has_paid_marketplace_access(vendor):
        raise HTTPException(status_code=403, detail="Active paid vendor plan required")
    rows = db.query(Listing).filter(Listing.vendor_id == vendor.id).order_by(Listing.created_at.desc()).all()
    return [
        {
            "id": x.id,
            "vendor_id": x.vendor_id,
            "title": x.title,
            "description": x.description,
            "price_cents": x.price_cents,
            "currency": x.currency,
            "status": x.status,
            "created_at": x.created_at.isoformat(),
            "updated_at": x.updated_at.isoformat(),
        }
        for x in rows
    ]


class FileUploadUrlRequest(BaseModel):
    listing_id: str
    file_name: str
    file_type: Optional[str] = None


@router.post("/files/upload-url")
async def files_upload_url(
    payload: FileUploadUrlRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    vendor = _require_vendor(db, current_user)
    listing = db.query(Listing).filter(Listing.id == payload.listing_id, Listing.vendor_id == vendor.id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    s3 = boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key_id,
        aws_secret_access_key=settings.s3_secret_access_key,
        region_name=settings.s3_region,
    )
    ext = payload.file_name.split(".")[-1].lower() if "." in payload.file_name else "bin"
    if ext not in {"zip", "json", "yaml", "yml", "md", "txt", "pdf", "png", "jpg", "jpeg"}:
        raise HTTPException(status_code=400, detail="Unsupported file extension")
    key = f"marketplace/{vendor.id}/{listing.id}/{uuid.uuid4().hex}.{ext}"
    params = {"Bucket": settings.s3_bucket_name, "Key": key}
    if payload.file_type:
        params["ContentType"] = payload.file_type
    upload_url = s3.generate_presigned_url("put_object", Params=params, ExpiresIn=900)
    return {"url": upload_url, "key": key}


class FileConfirmRequest(BaseModel):
    listing_id: str
    s3_key: str
    size: Optional[int] = None
    checksum: Optional[str] = None
    file_type: Optional[str] = None


@router.post("/files/confirm")
async def files_confirm(
    payload: FileConfirmRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    vendor = _require_vendor(db, current_user)
    listing = db.query(Listing).filter(Listing.id == payload.listing_id, Listing.vendor_id == vendor.id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    expected_prefix = f"marketplace/{vendor.id}/{listing.id}/"
    if not payload.s3_key.startswith(expected_prefix):
        raise HTTPException(status_code=400, detail="Invalid s3 key for listing")
    row = MarketplaceFile(
        listing_id=listing.id,
        vendor_id=vendor.id,
        workspace_id=current_user.workspace_id,
        s3_key=payload.s3_key,
        file_type=payload.file_type,
        size_bytes=payload.size,
        checksum=payload.checksum,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "s3_key": row.s3_key}


@router.get("/files/{file_id}/download")
async def files_download(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = db.query(MarketplaceFile).filter(
        MarketplaceFile.id == file_id,
        MarketplaceFile.workspace_id == current_user.workspace_id,
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="File not found")
    s3 = boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key_id,
        aws_secret_access_key=settings.s3_secret_access_key,
        region_name=settings.s3_region,
    )
    url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.s3_bucket_name, "Key": row.s3_key},
        ExpiresIn=900,
    )
    return {"url": url}


class EvidenceCreateRequest(BaseModel):
    listing_id: str
    metadata: dict = Field(default_factory=dict)


@router.post("/evidence/create")
async def evidence_create(
    payload: EvidenceCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    vendor = _require_vendor(db, current_user)
    listing = db.query(Listing).filter(Listing.id == payload.listing_id, Listing.vendor_id == vendor.id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    row = EvidencePackage(
        listing_id=listing.id,
        workspace_id=current_user.workspace_id,
        metadata_json=json.dumps(payload.metadata),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id}


@router.get("/evidence/{listing_id}")
async def evidence_get(listing_id: str, db: Session = Depends(get_db)):
    rows = db.query(EvidencePackage).filter(EvidencePackage.listing_id == listing_id).order_by(EvidencePackage.created_at.desc()).all()
    return [
        {
            "id": x.id,
            "listing_id": x.listing_id,
            "metadata": json.loads(x.metadata_json) if x.metadata_json else {},
            "created_at": x.created_at.isoformat(),
        }
        for x in rows
    ]


class OrderCreateRequest(BaseModel):
    items: list[str] = Field(default_factory=list, description="Listing IDs")


def _create_order_for_listing_ids(
    *,
    db: Session,
    current_user: User,
    listing_ids: list[str],
) -> MarketplaceOrder:
    if not listing_ids:
        raise HTTPException(status_code=400, detail="No order items provided")

    deduped_items = list(dict.fromkeys(listing_ids))
    listings = db.query(Listing).filter(Listing.id.in_(deduped_items), Listing.status == "active").all()
    found_ids = {x.id for x in listings}
    missing_ids = [x for x in deduped_items if x not in found_ids]
    if missing_ids:
        raise HTTPException(status_code=404, detail="One or more active listings were not found")

    currencies = {x.currency for x in listings}
    if len(currencies) != 1:
        raise HTTPException(status_code=400, detail="All listings in an order must have matching currency")

    total = sum(x.price_cents for x in listings)
    order = MarketplaceOrder(
        buyer_id=current_user.id,
        workspace_id=current_user.workspace_id,
        status="pending",
        total_cents=total,
        currency=list(currencies)[0],
    )
    db.add(order)
    db.flush()
    for x in listings:
        db.add(
            MarketplaceOrderItem(
                order_id=order.id,
                listing_id=x.id,
                vendor_id=x.vendor_id,
                price_cents=x.price_cents,
                status="pending",
            )
        )
    db.commit()
    db.refresh(order)
    return order


@router.post("/orders/create")
async def orders_create(
    payload: OrderCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    order = _create_order_for_listing_ids(db=db, current_user=current_user, listing_ids=payload.items)
    return {"id": order.id, "total_cents": order.total_cents, "currency": order.currency}


@router.get("/orders/{order_id}")
async def orders_get(
    order_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = db.query(MarketplaceOrder).filter(
        MarketplaceOrder.id == order_id,
        MarketplaceOrder.buyer_id == current_user.id,
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Order not found")
    return {
        "id": row.id,
        "status": row.status,
        "total_cents": row.total_cents,
        "currency": row.currency,
        "stripe_payment_intent": row.stripe_payment_intent,
        "items": [
            {"id": i.id, "listing_id": i.listing_id, "vendor_id": i.vendor_id, "price_cents": i.price_cents, "status": i.status}
            for i in row.items
        ],
        "created_at": row.created_at.isoformat(),
    }


class PaymentIntentRequest(BaseModel):
    order_id: str


@router.post("/payments/create-intent")
async def payments_create_intent(
    payload: PaymentIntentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Stripe is not configured")
    stripe.api_key = settings.stripe_secret_key
    order = db.query(MarketplaceOrder).filter(
        MarketplaceOrder.id == payload.order_id,
        MarketplaceOrder.buyer_id == current_user.id,
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.total_cents <= 0:
        raise HTTPException(status_code=400, detail="Order total must be positive")

    intent = stripe.PaymentIntent.create(
        amount=order.total_cents,
        currency=order.currency,
        automatic_payment_methods={"enabled": True},
        metadata={"order_id": order.id, "workspace_id": order.workspace_id},
    )
    order.stripe_payment_intent = intent["id"]
    db.commit()
    return {"payment_intent_id": intent["id"], "client_secret": intent["client_secret"], "status": intent["status"]}


class CheckoutSessionRequest(BaseModel):
    order_id: Optional[str] = None
    listing_id: Optional[str] = None
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


@router.post("/payments/create-checkout")
async def payments_create_checkout(
    payload: CheckoutSessionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Stripe is not configured")
    stripe.api_key = settings.stripe_secret_key
    if payload.order_id:
        order = db.query(MarketplaceOrder).filter(
            MarketplaceOrder.id == payload.order_id,
            MarketplaceOrder.buyer_id == current_user.id,
        ).first()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
    elif payload.listing_id:
        order = _create_order_for_listing_ids(db=db, current_user=current_user, listing_ids=[payload.listing_id])
    else:
        raise HTTPException(status_code=400, detail="order_id or listing_id is required")

    if order.total_cents <= 0:
        raise HTTPException(status_code=400, detail="Order total must be positive")
    if order.status == "paid":
        raise HTTPException(status_code=409, detail="Order already paid")

    success_url = (payload.success_url or f"https://veklom.com/marketplace/?checkout=success&order_id={order.id}").strip()
    cancel_url = (payload.cancel_url or f"https://veklom.com/marketplace/?checkout=cancel&order_id={order.id}").strip()

    line_items = []
    for item in order.items:
        if item.price_cents <= 0:
            continue
        listing = db.query(Listing).filter(Listing.id == item.listing_id).first()
        title = listing.title if listing else f"Listing {item.listing_id}"
        line_items.append(
            {
                "quantity": 1,
                "price_data": {
                    "currency": order.currency,
                    "unit_amount": item.price_cents,
                    "product_data": {
                        "name": title,
                        "description": (listing.description[:500] if listing and listing.description else "Marketplace listing purchase"),
                    },
                },
            }
        )
    if not line_items:
        raise HTTPException(status_code=400, detail="Order has no paid checkout items")

    session = stripe.checkout.Session.create(
        mode="payment",
        payment_method_types=["card"],
        customer_email=current_user.email,
        line_items=line_items,
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"order_id": order.id, "workspace_id": order.workspace_id},
    )
    return {"checkout_url": session.url, "checkout_session_id": session.id, "order_id": order.id}


@router.post("/payments/webhook")
async def payments_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(default=None, alias="Stripe-Signature"),
    db: Session = Depends(get_db),
):
    if not settings.stripe_secret_key or not settings.stripe_webhook_secret:
        raise HTTPException(status_code=503, detail="Stripe webhook is not configured")
    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature header")
    stripe.api_key = settings.stripe_secret_key
    payload = await request.body()
    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=stripe_signature,
            secret=settings.stripe_webhook_secret,
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid webhook payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    event_type = event["type"]
    if event_type == "checkout.session.completed":
        checkout = event["data"]["object"]
        order_id = (checkout.get("metadata") or {}).get("order_id")
        if order_id:
            order = db.query(MarketplaceOrder).filter(MarketplaceOrder.id == order_id).first()
            if order:
                order.status = "paid"
                for item in order.items:
                    item.status = "accepted"
                db.commit()

    if event_type in {"payment_intent.succeeded", "payment_intent.payment_failed"}:
        intent = event["data"]["object"]
        pi_id = intent.get("id")
        order = db.query(MarketplaceOrder).filter(MarketplaceOrder.stripe_payment_intent == pi_id).first()
        if order:
            if event_type == "payment_intent.succeeded":
                order.status = "paid"
                for item in order.items:
                    item.status = "accepted"
            else:
                order.status = "failed"
                for item in order.items:
                    item.status = "rejected"
            db.commit()

    return {"ok": True}


class PayoutCreateRequest(BaseModel):
    order_id: str
    vendor_id: str
    amount_cents: int = Field(..., ge=0)


@router.post("/payouts/create")
async def payouts_create(
    payload: PayoutCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Stripe is not configured")
    stripe.api_key = settings.stripe_secret_key
    order = db.query(MarketplaceOrder).filter(MarketplaceOrder.id == payload.order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.workspace_id != current_user.workspace_id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized")

    vendor = db.query(Vendor).filter(Vendor.id == payload.vendor_id).first()
    if not vendor or not vendor.stripe_account_id:
        raise HTTPException(status_code=400, detail="Vendor Stripe account is not configured")

    transfer = stripe.Transfer.create(
        amount=payload.amount_cents,
        currency=order.currency,
        destination=vendor.stripe_account_id,
        metadata={"order_id": order.id, "vendor_id": vendor.id},
    )
    row = MarketplacePayout(
        vendor_id=vendor.id,
        order_id=order.id,
        workspace_id=order.workspace_id,
        amount_cents=payload.amount_cents,
        stripe_transfer_id=transfer["id"],
        status="paid",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "stripe_transfer_id": row.stripe_transfer_id, "status": row.status}


@router.get("/payouts/vendor/{vendor_id}")
async def payouts_by_vendor(
    vendor_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = db.query(MarketplacePayout).filter(
        MarketplacePayout.vendor_id == vendor_id,
        MarketplacePayout.workspace_id == current_user.workspace_id,
    ).order_by(MarketplacePayout.created_at.desc()).all()
    return [
        {
            "id": x.id,
            "vendor_id": x.vendor_id,
            "order_id": x.order_id,
            "amount_cents": x.amount_cents,
            "stripe_transfer_id": x.stripe_transfer_id,
            "status": x.status,
            "created_at": x.created_at.isoformat(),
        }
        for x in rows
    ]
