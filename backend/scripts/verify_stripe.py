"""
Veklom — Stripe verification script.

Runs after `setup_stripe.py`. Confirms every Veklom-tagged Stripe object
is correctly configured AND that prices match the public landing page.

Exits 0 on full pass, non-zero on any failure.

Run:
    python scripts/verify_stripe.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Reuse helpers from setup_stripe.py
sys.path.insert(0, str(Path(__file__).resolve().parent))
from setup_stripe import (  # type: ignore
    PLANS, WEBHOOK_EVENTS, load_env,
    GREEN, RED, YELLOW, CYAN, DIM, BOLD, END,
    ok, fail, info, warn, header,
)


def main() -> int:
    header("Veklom · Stripe verification")

    env = load_env()
    secret_key = env.get("STRIPE_SECRET_KEY", "")
    if not secret_key:
        fail("STRIPE_SECRET_KEY missing — see .env.stripe")
        return 2

    try:
        import stripe
    except ImportError:
        fail("stripe library missing → pip install stripe")
        return 3
    stripe.api_key = secret_key
    stripe.api_version = env.get("STRIPE_API_VERSION", "2026-04-22.dahlia")

    failures = 0

    # 1. Account health
    header("1. Account")
    try:
        acct = stripe.Account.retrieve()
        ok(f"account {acct.id}  country={acct.country}")
        if acct.charges_enabled:
            ok("charges_enabled  = True")
        else:
            warn("charges_enabled  = False  (complete account activation in dashboard)")
            failures += 1
        if acct.payouts_enabled:
            ok("payouts_enabled  = True")
        else:
            warn("payouts_enabled  = False  (verify bank account in dashboard)")
            failures += 1
    except Exception as e:
        fail(f"account check failed: {e}")
        return 4

    # 2. Products + prices match the landing page
    header("2. Products + prices vs PRICING_TRUTH")
    products_by_veklom = {}
    for product in stripe.Product.list(limit=100, active=True).auto_paging_iter():
        vid = (product.metadata or {}).get("veklom_id")
        if vid:
            products_by_veklom[vid] = product

    for plan in PLANS:
        p = products_by_veklom.get(plan["veklom_id"])
        if not p:
            fail(f"product MISSING: {plan['name']}  ({plan['veklom_id']})")
            failures += 1
            continue
        ok(f"product OK       {p.id}  {plan['name']}")

        # Each plan must have one active monthly + one active yearly price.
        prices = stripe.Price.list(product=p.id, active=True, limit=100).data
        for interval, expected in (("month", plan["monthly_cents"]), ("year", plan["yearly_cents"])):
            match = next(
                (pr for pr in prices
                 if pr.recurring and pr.recurring.interval == interval and pr.unit_amount == expected),
                None,
            )
            if match:
                ok(f"  price OK       {match.id}  /{interval}  ${expected/100:,.2f}")
            else:
                fail(f"  price MISSING  {plan['name']}/{interval} expected ${expected/100:,.2f}")
                failures += 1

    # 3. Webhook
    header("3. Webhook endpoint")
    veklom_hooks = [
        ep for ep in stripe.WebhookEndpoint.list(limit=100).auto_paging_iter()
        if (ep.metadata or {}).get("veklom_id") == "veklom_primary_webhook"
    ]
    if not veklom_hooks:
        fail("no Veklom-tagged webhook endpoint found — run setup_stripe.py")
        failures += 1
    elif len(veklom_hooks) > 1:
        warn(f"{len(veklom_hooks)} Veklom webhook endpoints exist — keep one, delete the rest in dashboard")
        failures += 1
    else:
        ep = veklom_hooks[0]
        ok(f"webhook OK       {ep.id}  → {ep.url}")
        missing = [e for e in WEBHOOK_EVENTS if e not in ep.enabled_events]
        if missing:
            fail(f"  missing events: {missing}")
            failures += 1
        else:
            ok(f"  all {len(WEBHOOK_EVENTS)} events subscribed")
        if ep.status != "enabled":
            fail(f"  webhook status = {ep.status}  (should be enabled)")
            failures += 1
        if not env.get("STRIPE_WEBHOOK_SECRET"):
            warn("STRIPE_WEBHOOK_SECRET missing in .env.stripe — webhook signature verification will fail.")
            failures += 1
        else:
            ok("  STRIPE_WEBHOOK_SECRET present in env")

    # 4. Smoke checkout session (test mode only — never run on live)
    header("4. Checkout session smoke test")
    if secret_key.startswith("sk_live_") or secret_key.startswith("rk_live_"):
        info("LIVE key — skipping smoke checkout to avoid creating a real session")
    else:
        try:
            # Pick the Standard monthly price
            std_product = products_by_veklom.get("veklom_sovereign_standard")
            if not std_product:
                warn("Standard product missing — skipping smoke test")
            else:
                std_prices = stripe.Price.list(product=std_product.id, active=True, limit=10).data
                std_monthly = next(
                    (pr for pr in std_prices
                     if pr.recurring and pr.recurring.interval == "month"),
                    None,
                )
                if std_monthly:
                    sess = stripe.checkout.Session.create(
                        mode="subscription",
                        line_items=[{"price": std_monthly.id, "quantity": 1}],
                        success_url="https://veklom.com/success?sid={CHECKOUT_SESSION_ID}",
                        cancel_url="https://veklom.com/pricing",
                    )
                    ok(f"checkout session created: {sess.id}")
                    ok(f"  url: {sess.url[:60]}…")
                    # Expire it so it doesn't dangle
                    stripe.checkout.Session.expire(sess.id)
                    ok("  session expired cleanly")
        except Exception as e:
            fail(f"checkout smoke test failed: {e}")
            failures += 1

    # 5. Code-side sanity check: PLANS in subscriptions.py vs. landing page values
    header("5. Code vs. PRICING_TRUTH consistency")
    repo = Path(__file__).resolve().parent.parent
    sub_file = repo / "apps" / "api" / "routers" / "subscriptions.py"
    if sub_file.exists():
        text = sub_file.read_text(encoding="utf-8")
        expected_lines = [
            "750_000",     # standard monthly
            "1_800_000",   # pro monthly
            "4_500_000",   # enterprise monthly
        ]
        for needle in expected_lines:
            if needle in text:
                ok(f"PLANS constant contains {needle} cents")
            else:
                fail(f"PLANS constant MISSING {needle} cents — drift from landing page")
                failures += 1
    else:
        warn("subscriptions.py not found — skipping code sanity check")

    # ─── Summary ─────────────────────────────────────────────────────────────
    header("Summary")
    if failures == 0:
        print(f"{GREEN}{BOLD}ALL CHECKS PASSED.{END} Stripe is wired correctly.")
        print(f"{DIM}Next: deploy backend to Render, attach api.veklom.com, smoke-test a real checkout.{END}")
        return 0
    print(f"{RED}{BOLD}{failures} check(s) failed.{END} See messages above; re-run setup_stripe.py if needed.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
