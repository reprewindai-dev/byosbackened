---
name: growth-agent
description: Playbook for Phase 3-4 growth and revenue agents (040-053). Covers SEO, content, community, paid growth, pricing, referrals, email automation, and analytics.
---

# Growth & Revenue Agent Playbook

## When to Use
Invoke this skill when spinning up Phase 3 (user acquisition) or Phase 4 (retention/revenue) agents.

## Prerequisites
- Access to `byosbackened` repo
- Frontend (React/Vite/TypeScript) and backend (FastAPI) understanding
- Analytics/SEO tools access where applicable

## Setup Steps

1. Read your agent mission file from `agents/phase3-user-acquisition/` or `agents/phase4-retention-revenue/`
2. Read `MASTER_STATE.md` for current growth metrics
3. Read `PROGRESS.md` for daily user/vendor counts

## Phase 3 — User Acquisition Agents

### Agent-040 (SEO)
- Implement meta tags, structured data, sitemap.xml
- Key files: `frontend/index.html`, `frontend/public/sitemap.xml`
- Target: Page 1 Google for "AI marketplace", "sovereign AI tools"

### Agent-041 (Content)
- Create blog infrastructure, landing pages
- Key files: `frontend/src/pages/Blog.tsx`, `frontend/src/pages/Landing.tsx`

### Agent-042 (Community)
- Build community features: comments, reviews, forums
- Key files: `backend/app/api/community.py`

### Agent-043 (Paid Growth)
- Set up conversion tracking, optimize landing pages
- Integration: Google Ads, LinkedIn Ads pixels

### Agent-044 (Product Hunt)
- Prepare Product Hunt launch assets
- Create launch page, tagline, screenshots

## Phase 4 — Retention & Revenue Agents

### Agent-050 (Pricing)
- Implement tiered pricing, usage metering
- Key files: `backend/app/services/billing.py`, `frontend/src/pages/Pricing.tsx`

### Agent-051 (Referral Activation)
- Wire referral rewards, track conversions
- Key files: `backend/app/api/referrals.py`

### Agent-052 (Email Automation)
- Build email sequences: welcome, onboarding, re-engagement
- Key files: `backend/app/services/email.py`

### Agent-053 (Analytics)
- Implement event tracking, funnel analysis, cohort reports
- Key files: `backend/app/services/analytics.py`

## Target Metrics (Day 14)

| Metric | Target |
|---|---|
| Registered users | 2,000 |
| Paying customers | 150 |
| Vendors listed | 100 |
| MRR | $7,500 |

## Completion Checklist
- [ ] Read mission file and MASTER_STATE.md
- [ ] Implement assigned growth/revenue feature
- [ ] Verify frontend changes render correctly
- [ ] Run lint checks
- [ ] Create PR with changes
- [ ] Update PROGRESS.md with metrics
