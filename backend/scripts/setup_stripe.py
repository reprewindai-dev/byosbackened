"""
Veklom — Stripe one-shot setup script.

Creates / verifies all the Stripe objects the backend needs:
  • 3 Products (Sovereign Standard / Pro / Enterprise)
  • 6 Prices (monthly + yearly per tier)
  • 1 Webhook endpoint
  • Customer Portal configuration
  • Tax automation toggle

Run:
    python scripts/setup_stripe.py
    python scripts/setup_stripe.py --webhook-url https://api.veklom.com/api/v1/subscriptions/webhook
    python scripts/setup_stripe.py --dry-run

Reads STRIPE_SECRET_KEY from `.env.stripe` (preferred) or the environment.

The script is **idempotent** — re-running it will not create duplicates.
It looks up objects by `metadata.veklom_id` and updates in place.

Output is written to `stripe_setup_output.json` (gitignored) and printed
to the console as a green/red checklist.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

# ─── Pretty terminal output ──────────────────────────────────────────────────

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
DIM = "\033[2m"
BOLD = "\033[1m"
END = "\033[0m"

def ok(msg: str) -> None:
    print(f"{GREEN}✓{END} {msg}")

def fail(msg: str) -> None:
    print(f"{RED}✗{END} {msg}")

def info(msg: str) -> None:
    print(f"{CYAN}ℹ{END} {msg}")

def warn(msg: str) -> None:
    print(f"{YELLOW}⚠{END} {msg}")

def header(msg: str) -> None:
    print(f"\n{BOLD}{msg}{END}")
    print(DIM + "─" * len(msg) + END)


# ─── Config: Veklom plan catalog (mirrors apps/api/routers/subscriptions.py) ──

PLANS = [
    {
        "veklom_id": "veklom_sovereign_standard",
        "name": "Sovereign · Standard",
        "description": (
            "Self-host in your VPC or on-prem. Perpetual source access. "
            "14 business-day SLA. Quarterly version updates. Async written support."
        ),
        "monthly_cents":  750_000,    # $7,500
        "yearly_cents": 7_500_000,    # $75,000 (2 months free)
        "internal_tier": "starter",
    },
    {
        "veklom_id": "veklom_sovereign_pro",
        "name": "Sovereign · Pro",
        "description": (
            "Self-host. Perpetual source. 5 business-day SLA. Monthly updates. "
            "Direct-email support, 24h first response. Annual architecture review. "
            "White-label rights."
        ),
        "monthly_cents":  1_800_000,  # $18,000
        "yearly_cents": 18_000_000,   # $180,000
        "internal_tier": "pro",
    },
    {
        "veklom_id": "veklom_sovereign_enterprise",
        "name": "Sovereign · Enterprise",
        "description": (
            "Self-host. Perpetual source. 24-hour SLA. Monthly updates. Priority "
            "engineering channel. Per-quarter feature commitments. Compliance docs "
            "(SOC 2 mapping, pen-test report). Procurement-friendly MSA."
        ),
        "monthly_cents":  4_500_000,  # $45,000
        "yearly_cents": 45_000_000,   # $450,000
        "internal_tier": "enterprise",
    },
]

# The acquisition tier ($750k IP transfer) is intentionally NOT in this script.
# It is negotiated outside self-serve checkout — see landing page §vii.

WEBHOOK_EVENTS = [
    "checkout.session.completed",
    "customer.subscription.created",
    "customer.subscription.updated",
    "customer.subscription.deleted",
    "invoice.paid",
    "invoice.payment_failed",
    "customer.created",
    "customer.updated",
]

DEFAULT_WEBHOOK_URL = "https://api.veklom.com/api/v1/subscriptions/webhook"


# ─── Env loader ──────────────────────────────────────────────────────────────

def load_env() -> dict:
    """
    Load STRIPE_SECRET_KEY from .env.stripe (preferred), .env, or process env.
    The user's instructions are explicit: live keys go in .env.stripe only.
    """
    repo_root = Path(__file__).resolve().parent.parent
    candidates = [repo_root / ".env.stripe", repo_root / ".env"]
    loaded: dict = {}
    for path in candidates:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            loaded.setdefault(k.strip(), v.strip().strip('"').strip("'"))

    # Process env wins as a last resort (CI/CD).
    for k in ("STRIPE_SECRET_KEY", "STRIPE_PUBLISHABLE_KEY", "STRIPE_WEBHOOK_SECRET"):
        if k in os.environ and not loaded.get(k):
            loaded[k] = os.environ[k]
    return loaded


# ─── Stripe operations (idempotent) ──────────────────────────────────────────

def find_by_veklom_id(stripe, resource, veklom_id: str):
    """Look up an existing Stripe object by metadata.veklom_id."""
    items = resource.list(limit=100, active=None if resource is stripe.Product else True)
    for obj in items.auto_paging_iter():
        if (obj.metadata or {}).get("veklom_id") == veklom_id:
            return obj
    return None


def upsert_product(stripe, plan: dict, dry_run: bool):
    veklom_id = plan["veklom_id"]
    existing = find_by_veklom_id(stripe, stripe.Product, veklom_id)
    if existing:
        if dry_run:
            info(f"[dry-run] would update product {existing.id} ({plan['name']})")
            return existing
        product = stripe.Product.modify(
            existing.id,
            name=plan["name"],
            description=plan["description"],
            metadata={
                "veklom_id": veklom_id,
                "internal_tier": plan["internal_tier"],
            },
        )
        ok(f"product updated  {product.id}  {plan['name']}")
        return product
    if dry_run:
        info(f"[dry-run] would create product {plan['name']}")
        return None
    product = stripe.Product.create(
        name=plan["name"],
        description=plan["description"],
        metadata={
            "veklom_id": veklom_id,
            "internal_tier": plan["internal_tier"],
        },
    )
    ok(f"product created  {product.id}  {plan['name']}")
    return product


def upsert_price(stripe, product_id: str, plan: dict, interval: str, amount_cents: int, dry_run: bool):
    veklom_id = f"{plan['veklom_id']}__{interval}"
    existing = find_by_veklom_id(stripe, stripe.Price, veklom_id)
    if existing:
        # Stripe prices are immutable. If the amount matches, reuse. Else archive + recreate.
        if existing.unit_amount == amount_cents and existing.recurring and existing.recurring.interval == interval:
            ok(f"price reused     {existing.id}  {plan['name']}/{interval}  ${amount_cents/100:,.2f}")
            return existing
        if dry_run:
            info(f"[dry-run] would archive {existing.id} and recreate")
        else:
            stripe.Price.modify(existing.id, active=False)
            warn(f"archived stale price {existing.id} (amount changed)")
    if dry_run:
        info(f"[dry-run] would create price {plan['name']}/{interval} ${amount_cents/100:,.2f}")
        return None
    price = stripe.Price.create(
        product=product_id,
        unit_amount=amount_cents,
        currency="usd",
        recurring={"interval": interval},
        metadata={
            "veklom_id": veklom_id,
            "internal_tier": plan["internal_tier"],
            "interval": interval,
        },
    )
    ok(f"price created    {price.id}  {plan['name']}/{interval}  ${amount_cents/100:,.2f}")
    return price


def upsert_webhook(stripe, url: str, dry_run: bool):
    """
    Find a Veklom-tagged webhook endpoint or create one.
    Returns (endpoint, signing_secret_or_none).
    """
    for ep in stripe.WebhookEndpoint.list(limit=100).auto_paging_iter():
        if (ep.metadata or {}).get("veklom_id") == "veklom_primary_webhook":
            if ep.url == url:
                ok(f"webhook reused   {ep.id}  {url}")
                return ep, None  # secret only shown on creation
            if dry_run:
                info(f"[dry-run] would update webhook url {ep.url} → {url}")
                return ep, None
            ep = stripe.WebhookEndpoint.modify(ep.id, url=url, enabled_events=WEBHOOK_EVENTS)
            ok(f"webhook updated  {ep.id}  {url}")
            return ep, None
    if dry_run:
        info(f"[dry-run] would create webhook {url}")
        return None, None
    ep = stripe.WebhookEndpoint.create(
        url=url,
        enabled_events=WEBHOOK_EVENTS,
        description="Veklom backend — primary webhook (created by setup_stripe.py)",
        metadata={"veklom_id": "veklom_primary_webhook"},
    )
    ok(f"webhook created  {ep.id}  {url}")
    return ep, ep.secret  # only present on first create


def configure_customer_portal(stripe, products: list, dry_run: bool):
    """
    Configure the Stripe customer portal so customers can self-manage subscriptions.
    """
    if dry_run:
        info("[dry-run] would configure customer portal")
        return None

    config = stripe.billing_portal.Configuration.create(
        business_profile={
            "headline": "Manage your Veklom subscription",
            "privacy_policy_url": "https://veklom.com/legal/privacy.html",
            "terms_of_service_url": "https://veklom.com/legal/terms.html",
        },
        features={
            "customer_update": {
                "allowed_updates": ["email", "tax_id", "address", "name", "phone"],
                "enabled": True,
            },
            "invoice_history": {"enabled": True},
            "payment_method_update": {"enabled": True},
            "subscription_cancel": {
                "enabled": True,
                "mode": "at_period_end",
                "cancellation_reason": {
                    "enabled": True,
                    "options": [
                        "too_expensive",
                        "missing_features",
                        "switched_service",
                        "unused",
                        "customer_service",
                        "too_complex",
                        "low_quality",
                        "other",
                    ],
                },
            },
            "subscription_update": {
                "default_allowed_updates": ["price"],
                "enabled": True,
                "products": [
                    {"product": p.id, "prices": [pr.id for pr in p._veklom_prices]}
                    for p in products if hasattr(p, "_veklom_prices")
                ],
                "proration_behavior": "create_prorations",
            },
        },
        metadata={"veklom_id": "veklom_primary_portal"},
    )
    ok(f"portal configured {config.id}")
    return config


# ─── Main ────────────────────────────────────────────────────────────────────

def main() -> int:
    fail("setup_stripe.py is retired for the old recurring subscription model.")
    info("Current model: one-time activation plus USD Operating Reserve.")
    info("Use backend/PRICING_TRUTH.md and apps/api/routers/subscriptions.py as the source of truth.")
    return 2

    parser = argparse.ArgumentParser(description="Veklom Stripe setup")
    parser.add_argument("--webhook-url", default=DEFAULT_WEBHOOK_URL,
                        help=f"Webhook endpoint URL (default: {DEFAULT_WEBHOOK_URL})")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would happen without making changes")
    parser.add_argument("--skip-portal", action="store_true",
                        help="Skip customer-portal configuration")
    args = parser.parse_args()

    header("Veklom · Stripe setup")
    print(DIM + "Idempotent: safe to run multiple times. Reads .env.stripe.\n" + END)

    # 1. Load + sanity-check key
    env = load_env()
    secret_key = env.get("STRIPE_SECRET_KEY", "")
    if not secret_key:
        fail("STRIPE_SECRET_KEY not found in .env.stripe or environment.")
        info("Create backend/.env.stripe with:")
        info("  STRIPE_SECRET_KEY=rk_live_...   (or sk_test_...)")
        info("  STRIPE_PUBLISHABLE_KEY=pk_...")
        return 2

    if secret_key.startswith("sk_test_") or secret_key.startswith("rk_test_"):
        warn("TEST mode key detected — no real charges will occur.")
    elif secret_key.startswith("sk_live_") or secret_key.startswith("rk_live_"):
        warn("LIVE mode key detected — real money will be touched. Continuing in 3 seconds…")
        import time; time.sleep(3)
    else:
        fail(f"Unrecognized key prefix: {secret_key[:10]}...  expected sk_/rk_/test_/live_")
        return 2

    # 2. Import Stripe (after key validated, so failure mode is clear)
    try:
        import stripe
    except ImportError:
        fail("`stripe` Python library not installed. Run: pip install stripe")
        return 3
    stripe.api_key = secret_key
    # Pin the API version — Stripe's "stripe-best-practices" skill recommends
    # always using the latest, and pinning prevents silent breakage on Stripe-side updates.
    stripe.api_version = "2026-04-22.dahlia"

    # 3. Whoami
    header("1. Verifying Stripe credentials")
    try:
        acct = stripe.Account.retrieve()
        ok(f"connected to Stripe account: {acct.id}")
        biz = getattr(acct, "business_profile", None)
        biz_name = None
        if biz is not None:
            try:
                biz_name = biz.get("name") if hasattr(biz, "get") else getattr(biz, "name", None)
            except Exception:
                biz_name = None
        if biz_name:
            ok(f"business name: {biz_name}")
        country = getattr(acct, "country", "?") or "?"
        currency = getattr(acct, "default_currency", None) or "usd"
        ok(f"country: {country}  default currency: {currency.upper()}")
        charges_enabled = getattr(acct, "charges_enabled", False)
        payouts_enabled = getattr(acct, "payouts_enabled", False)
        if not charges_enabled:
            warn("charges_enabled = False  → account not fully activated. Setup will continue (test-mode products will be created); flip to live after dashboard activation.")
        if not payouts_enabled:
            warn("payouts_enabled = False  → bank account not yet verified.")
    except Exception as e:
        fail(f"could not authenticate ({type(e).__name__}): {e}")
        return 4

    # 4. Products + prices
    header("2. Products + prices")
    output: dict = {"products": [], "prices": []}
    products_with_prices = []
    for plan in PLANS:
        product = upsert_product(stripe, plan, args.dry_run)
        if product is None:
            continue
        prices = []
        prices.append(upsert_price(stripe, product.id, plan, "month", plan["monthly_cents"], args.dry_run))
        prices.append(upsert_price(stripe, product.id, plan, "year", plan["yearly_cents"], args.dry_run))
        if not args.dry_run:
            product._veklom_prices = [p for p in prices if p]
            products_with_prices.append(product)
            output["products"].append({"id": product.id, "name": product.name, "veklom_id": plan["veklom_id"]})
            for pr in prices:
                if pr is None: continue
                output["prices"].append({
                    "id": pr.id,
                    "product": product.id,
                    "interval": pr.recurring.interval,
                    "amount_cents": pr.unit_amount,
                    "veklom_id": pr.metadata.get("veklom_id"),
                })

    # 5. Webhook
    header("3. Webhook endpoint")
    ep, fresh_secret = upsert_webhook(stripe, args.webhook_url, args.dry_run)
    if ep and not args.dry_run:
        output["webhook"] = {"id": ep.id, "url": ep.url, "events": list(ep.enabled_events)}
        if fresh_secret:
            # Save the secret to .env.stripe (gitignored) instead of stdout.
            # This way the secret never crosses chat / logs / CI output.
            env_path = Path(__file__).resolve().parent.parent / ".env.stripe"
            existing = {}
            if env_path.exists():
                for line in env_path.read_text(encoding="utf-8").splitlines():
                    if "=" in line and not line.strip().startswith("#"):
                        k, v = line.split("=", 1)
                        existing[k.strip()] = v.strip()
            existing["STRIPE_WEBHOOK_SECRET"] = fresh_secret
            env_path.write_text(
                "# Veklom Stripe credentials — gitignored, never commit.\n"
                + "\n".join(f"{k}={v}" for k, v in existing.items()) + "\n",
                encoding="utf-8",
            )
            ok(f"webhook signing secret saved to .env.stripe (length={len(fresh_secret)})")
            # Also drop it under a redacted marker in the JSON summary so the file isn't useless.
            output["webhook"]["signing_secret_saved_to"] = ".env.stripe"
        else:
            info("Existing webhook reused. If you don't have its signing secret saved,")
            info("delete it in dashboard and re-run this script to regenerate.")

    # 6. Customer portal
    if not args.skip_portal:
        header("4. Customer portal")
        try:
            cfg = configure_customer_portal(stripe, products_with_prices, args.dry_run)
            if cfg:
                output["portal"] = {"id": cfg.id}
        except Exception as e:
            warn(f"portal config skipped: {e}")

    # 7. Persist output
    if not args.dry_run:
        out_path = Path(__file__).resolve().parent.parent / "stripe_setup_output.json"
        out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
        ok(f"summary written: {out_path}")

    header("Done")
    info("Next: run  python scripts/verify_stripe.py")
    info("Then : add the webhook signing secret to .env.stripe (if newly generated above)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
