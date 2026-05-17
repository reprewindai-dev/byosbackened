"""
Veklom — Stripe one-shot setup script (activation + operating reserve model).

Creates / verifies all the Stripe objects the backend needs:
  • 4 Products (Founding / Standard / Regulated / Enterprise)
  • 4 One-time Activation Prices (matching subscriptions.py PLANS)
  • 1 Webhook endpoint
  • Customer Portal configuration

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
from typing import Any

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
# Pricing model: one-time activation fee + USD operating reserve (wallet).
# No recurring subscriptions — customers pre-fund a reserve, events draw from it.

PLANS = [
    {
        "veklom_id": "veklom_founding",
        "name": "Veklom Founding",
        "description": (
            "Activation fee for the Founding tier. Governed playground, "
            "model compare, pipeline testing, deployment verification. "
            "Async written support. $150 minimum operating reserve."
        ),
        "activation_cents": 39_500,       # $395
        "minimum_reserve_cents": 15_000,   # $150
        "internal_tier": "starter",
    },
    {
        "veklom_id": "veklom_standard",
        "name": "Veklom Standard",
        "description": (
            "Activation fee for the Standard tier. Everything in Founding plus "
            "UACP autonomous control plane, signed audit exports, compliance "
            "evidence packages. 24h email support. $300 minimum operating reserve."
        ),
        "activation_cents": 79_500,       # $795
        "minimum_reserve_cents": 30_000,   # $300
        "internal_tier": "pro",
    },
    {
        "veklom_id": "veklom_regulated",
        "name": "Veklom Regulated",
        "description": (
            "Activation fee for the Regulated tier. Full sovereign deployment, "
            "kill-switch, auditor bundles, white-label rights, dedicated Slack "
            "channel. $2,500 minimum operating reserve."
        ),
        "activation_cents": 250_000,      # $2,500
        "minimum_reserve_cents": 250_000,  # $2,500
        "internal_tier": "sovereign",
    },
    {
        "veklom_id": "veklom_enterprise",
        "name": "Veklom Enterprise",
        "description": (
            "Enterprise tier — custom pricing, procurement-friendly MSA, "
            "dedicated engineering channel, quarterly feature commitments, "
            "SOC 2 mapping, pen-test report. Contact sales."
        ),
        "activation_cents": None,  # sales-led, no self-serve price
        "minimum_reserve_cents": None,
        "internal_tier": "enterprise",
    },
]

WEBHOOK_EVENTS = [
    "checkout.session.completed",
    "customer.subscription.created",
    "customer.subscription.updated",
    "customer.subscription.deleted",
    "invoice.paid",
    "invoice.payment_failed",
    "customer.created",
    "customer.updated",
    "payment_intent.succeeded",
    "payment_intent.payment_failed",
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

def find_by_veklom_id(stripe: Any, resource: Any, veklom_id: str):
    """Look up an existing Stripe object by metadata.veklom_id."""
    kwargs: dict[str, Any] = {"limit": 100}
    if resource is stripe.Product:
        # Products don't support active filter the same way
        pass
    items = resource.list(**kwargs)
    for obj in items.auto_paging_iter():
        if (obj.metadata or {}).get("veklom_id") == veklom_id:
            return obj
    return None


def upsert_product(stripe: Any, plan: dict, dry_run: bool):
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
                "pricing_model": "activation_plus_reserve",
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
            "pricing_model": "activation_plus_reserve",
        },
    )
    ok(f"product created  {product.id}  {plan['name']}")
    return product


def upsert_activation_price(stripe: Any, product_id: str, plan: dict, dry_run: bool):
    """Create a one-time activation price for a plan tier."""
    if plan["activation_cents"] is None:
        info(f"  {plan['name']}: no self-serve price (sales-led)")
        return None

    veklom_id = f"{plan['veklom_id']}__activation"
    existing = find_by_veklom_id(stripe, stripe.Price, veklom_id)
    if existing:
        if existing.unit_amount == plan["activation_cents"] and existing.type == "one_time":
            ok(f"  price reused     {existing.id}  ${plan['activation_cents']/100:,.2f} one-time")
            return existing
        if dry_run:
            info(f"  [dry-run] would archive {existing.id} and recreate")
        else:
            stripe.Price.modify(existing.id, active=False)
            warn(f"  archived stale price {existing.id} (amount changed)")
    if dry_run:
        info(f"  [dry-run] would create price ${plan['activation_cents']/100:,.2f} one-time")
        return None
    price = stripe.Price.create(
        product=product_id,
        unit_amount=plan["activation_cents"],
        currency="usd",
        metadata={
            "veklom_id": veklom_id,
            "internal_tier": plan["internal_tier"],
            "price_type": "activation",
        },
    )
    ok(f"  price created    {price.id}  ${plan['activation_cents']/100:,.2f} one-time")
    return price


def upsert_webhook(stripe: Any, url: str, dry_run: bool):
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


def configure_customer_portal(stripe: Any, dry_run: bool):
    """
    Configure the Stripe customer portal so customers can manage billing.
    """
    if dry_run:
        info("[dry-run] would configure customer portal")
        return None

    config = stripe.billing_portal.Configuration.create(
        business_profile={
            "headline": "Manage your Veklom account",
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
        },
        metadata={"veklom_id": "veklom_primary_portal"},
    )
    ok(f"portal configured {config.id}")
    return config


# ─── Main ────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Veklom Stripe setup (activation + reserve model)")
    parser.add_argument("--webhook-url", default=DEFAULT_WEBHOOK_URL,
                        help=f"Webhook endpoint URL (default: {DEFAULT_WEBHOOK_URL})")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would happen without making changes")
    parser.add_argument("--skip-portal", action="store_true",
                        help="Skip customer-portal configuration")
    parser.add_argument("--skip-webhook", action="store_true",
                        help="Skip webhook endpoint creation")
    args = parser.parse_args()

    header("Veklom · Stripe setup (activation + operating reserve)")
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
        warn("LIVE mode key detected — real products will be created.")
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
            warn("charges_enabled = False  → account not fully activated.")
        if not payouts_enabled:
            warn("payouts_enabled = False  → bank account not yet verified.")
    except Exception as e:
        fail(f"could not authenticate ({type(e).__name__}): {e}")
        return 4

    # 4. Products + activation prices
    header("2. Products + activation prices")
    output: dict = {"products": [], "prices": []}
    for plan in PLANS:
        product = upsert_product(stripe, plan, args.dry_run)
        if product is None:
            continue
        price = upsert_activation_price(stripe, product.id, plan, args.dry_run)
        if not args.dry_run:
            product_entry: dict = {
                "id": product.id,
                "name": product.name,
                "veklom_id": plan["veklom_id"],
                "internal_tier": plan["internal_tier"],
            }
            output["products"].append(product_entry)
            if price:
                output["prices"].append({
                    "id": price.id,
                    "product": product.id,
                    "type": "one_time",
                    "amount_cents": price.unit_amount,
                    "veklom_id": price.metadata.get("veklom_id"),
                })

    # 5. Webhook
    if not args.skip_webhook:
        header("3. Webhook endpoint")
        ep, fresh_secret = upsert_webhook(stripe, args.webhook_url, args.dry_run)
        if ep and not args.dry_run:
            output["webhook"] = {"id": ep.id, "url": ep.url, "events": list(ep.enabled_events)}
            if fresh_secret:
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
                output["webhook"]["signing_secret_saved_to"] = ".env.stripe"
            else:
                info("Existing webhook reused. If you don't have its signing secret saved,")
                info("delete it in dashboard and re-run this script to regenerate.")

    # 6. Customer portal
    if not args.skip_portal:
        header("4. Customer portal")
        try:
            cfg = configure_customer_portal(stripe, args.dry_run)
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
    info("Veklom products created in Stripe dashboard.")
    info("Next: verify with  python scripts/verify_stripe.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
