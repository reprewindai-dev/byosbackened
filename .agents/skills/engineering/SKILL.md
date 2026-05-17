---
name: engineering-agent
description: Playbook for Phase 1 engineering agents (001-008). Covers Stripe Connect, referral system, UX, playground, onboarding, API docs, performance, and security hardening.
---

# Engineering Agent Playbook

## When to Use
Invoke this skill when spinning up any Phase 1 engineering agent (Agent-001 through Agent-008).

## Prerequisites
- Access to `byosbackened` repo
- Python 3.11+ with FastAPI
- PostgreSQL connection
- Redis connection
- Stripe API keys (for Agent-001)

## Setup Steps

1. Read your agent mission file from `agents/phase1-engineering/agent-{ID}-{name}.md`
2. Read `MASTER_STATE.md` to understand current repo state
3. Read `PROGRESS.md` for context on what other agents have completed
4. Check the backend structure:
   ```
   backend/
   ├── app/
   │   ├── api/          # FastAPI route handlers
   │   ├── core/         # Config, security, database
   │   ├── models/       # SQLAlchemy models
   │   ├── schemas/      # Pydantic schemas
   │   └── services/     # Business logic
   ├── alembic/          # Database migrations
   └── requirements.txt
   ```

## Agent-Specific Tasks

### Agent-001 (Stripe Connect)
- Wire `POST /api/v1/payments/create-connect-account`
- Implement vendor payout splits
- Key files: `backend/app/api/payments.py`, `backend/app/services/stripe_service.py`

### Agent-002 (Referral System)
- Build referral code generation and tracking
- Key files: `backend/app/api/referrals.py`, `backend/app/models/referral.py`

### Agent-003 (UX Completion)
- Fix broken frontend states, wire missing API endpoints
- Key files: `frontend/src/pages/`, `frontend/src/components/`

### Agent-004 (Playground)
- Build AI tool playground with live preview
- Key files: `frontend/src/pages/Playground.tsx`

### Agent-005 (Onboarding)
- Create vendor/buyer onboarding wizard
- Key files: `frontend/src/pages/Onboarding.tsx`

### Agent-006 (API Docs)
- Generate OpenAPI spec, create developer portal
- Key files: `backend/app/main.py` (FastAPI docs config)

### Agent-007 (Performance)
- Add Redis caching, optimize DB queries
- Key files: `backend/app/core/cache.py`, `backend/app/core/database.py`

### Agent-008 (Security)
- Implement rate limiting, CORS hardening, input validation
- Key files: `backend/app/core/security.py`, `backend/app/middleware/`

## Completion Checklist
- [ ] Read mission file and MASTER_STATE.md
- [ ] Implement assigned tasks
- [ ] Write tests for new functionality
- [ ] Run `ruff check backend/` for linting
- [ ] Run `pytest backend/tests/` for tests
- [ ] Create PR with changes
- [ ] Update PROGRESS.md with completion status
