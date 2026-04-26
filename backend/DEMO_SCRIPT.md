# BYOS Demo Script — 5 Minute Loom

**Goal:** turn a curious viewer into a serious buyer. Tight, factual, no fluff.

**Setup before recording:**
- Two terminals open side-by-side
- VS Code with `apps/api/main.py` open showing the middleware stack
- Browser tab on `http://127.0.0.1:8000/api/v1/docs` (Swagger UI)
- Have `HONEST_AUDIT_REPORT.md` open in another tab
- Mic check, screen at 1080p+

---

## SCRIPT (read aloud, ~5 min)

### [0:00–0:30] Hook

> "Hi. I'm [name]. This is BYOS — a complete AI operations backend.
> What you're about to see is a working production-grade platform with 126 routes covering everything from multi-LLM routing, to cost-intelligence kill switches, to GDPR compliance, to Stripe billing. The kind of thing companies pay Portkey or LangSmith ten thousand dollars a month to use as SaaS — except this is source code you own outright."

### [0:30–1:30] Show the feature surface

Switch to browser → `/api/v1/docs`.

> "This is the live OpenAPI spec. 126 endpoints organized into about 60 routers. Let me scroll. You'll see:
> - **Auth & RBAC** — workspaces, roles, permissions
> - **Audit log** — every action recorded
> - **Billing** — Stripe subscriptions and usage
> - **Budget & cost intel** — predictive cost tracking with ML models
> - **Privacy** — GDPR data export, right-to-erasure
> - **Kill switch** — manual + automatic AI operations halt when budgets blown
> - **Autonomous routing** — picks the cheapest provider that meets quality SLA
> - **Plugins, suggestions, insights, exec, transcribe, extract, search, jobs**…"

(Scroll fast through the docs page so they see the volume.)

### [1:30–2:30] Show the architecture

Switch to VS Code → `apps/api/main.py`.

> "This is the FastAPI entry. Notice the middleware stack — defense in depth. From the outside in:
> - Pure-ASGI fast-path for cached endpoints — sub-millisecond
> - Performance + gzip layer
> - Zero-trust auth
> - Rate limiting, IP-based and workspace-based
> - Intrusion detection — SQL injection, SSRF, XSS pattern matching
> - Budget kill-switch checks
> - Then your routes.
>
> Each layer is a small, focused module. Every layer that touches money or data has been tested under load."

Switch to a router file briefly (`apps/api/routers/audit.py` or similar).

> "The code is plain FastAPI plus SQLAlchemy. No exotic frameworks. Anyone with a year of Python experience can extend it."

### [2:30–3:30] Run the stress test live

Switch to terminal 1.

```bash
python -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000 --log-level warning
```

Wait for "Application startup complete."

Switch to terminal 2.

```bash
python tests/load/real_stress_test.py
```

> "This is `real_stress_test.py`. It hits five endpoints with 10, 50, 100, 200, and 500 concurrent users — 9,600 requests total. Every request gets a unique correlation ID. Every response is hashed. Full audit JSON saved at the end. No fake numbers possible."

(Wait ~90 seconds for it to run. Talk over it.)

> "Note this is on a single-worker Uvicorn on Windows with SQLite. In production, gunicorn with 4 workers on Linux + Postgres + Redis is roughly an order of magnitude faster. The numbers you're about to see are the floor, not the ceiling."

When it finishes:

> "100% success at every load level up to 500 concurrent users. No 5xx errors, no dropped connections. Latencies are honest — they degrade under load on a single worker, exactly as expected."

### [3:30–4:15] Show the audit report

Switch to `HONEST_AUDIT_REPORT.md`.

> "Here's something most sellers won't show you: the honest audit report.
> 
> The previous developer claimed 777-millisecond P95 at 5,000 concurrent users. That was false — the real Locust failure CSVs are still in the repo as evidence. I went through, identified the bugs, fixed them, and wrote up exactly what works, what doesn't, and what the deployment shape needs to be.
>
> If you're doing technical due diligence, this saves you a week. Everything's verifiable. Nothing's hidden."

### [4:15–5:00] The ask

> "What you get when you buy:
> - The complete source code, around 50K lines of focused Python
> - Deployment configs for Render, DigitalOcean, or self-host
> - The audit report and stress test artifacts
> - 30 days of transition support
>
> Pricing: $250K outright with full IP transfer, or $75K for a non-exclusive perpetual license.
>
> If you're a serious buyer or strategic acquirer, email me at [your email]. Repo access under NDA after first call.
>
> Thanks for watching."

(End recording.)

---

## Recording tips

- **Practice once before recording.** First take is always rough.
- **Cut anything over 6 minutes.** Buyers click away.
- **Don't apologize for the laptop demo.** It's a feature: "this runs on a laptop and still hits 100% — imagine prod."
- **Show your face in a webcam bubble.** Loom does this automatically. Trust signal.
- **Upload to Loom (free), get the share URL.** Put that URL in your sales emails.

---

## What to send with the Loom

Email template:

> Subject: AI ops platform — full source code, $250K
>
> Hi [name],
>
> 5-minute walkthrough of BYOS: [Loom URL]
>
> It's the AI operations backend that competitors like Portkey and LangSmith charge $5K–$10K/month for as SaaS — sold as source code so you own it outright. 126 routes, multi-LLM, cost intel, RBAC, GDPR, Stripe, audit. Everything verified, including an honest audit report.
>
> Asking $250K outright or $75K non-exclusive license. Open to strategic deal structures.
>
> Worth a 20-minute call?
>
> [your name]

That's it. Send to 30 targeted contacts. 2–5 will reply. 1 will close.
