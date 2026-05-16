---
name: operations-agent
description: Playbook for Phase 5 operations agents (060-079). Covers support, monitoring, content calendar, research, governance, and compliance.
---

# Operations Agent Playbook

## When to Use
Invoke this skill when spinning up any Phase 5 operations, research, governance, or QA agent.

## Prerequisites
- Access to `byosbackened` repo
- Understanding of the workforce-control package and UACP architecture
- Access to monitoring/observability tools

## Setup Steps

1. Read your agent mission file from `agents/phase5-daily-operations/agent-{ID}-{name}.md`
2. Read `MASTER_STATE.md` for current system state
3. Read `PROGRESS.md` for operational metrics

## Operations Agents (060-062)

### Agent-060 (Support)
- Monitor support channels, triage issues
- Key files: `backend/app/api/support.py`

### Agent-061 (Monitoring)
- Set up health checks, uptime monitoring, alerting
- Key files: `backend/app/services/monitoring.py`, `docker-compose.yml`

### Agent-062 (Content Calendar)
- Manage content pipeline, schedule posts
- Coordinate with Agent-041 (content) and Agent-042 (community)

## Research / Special Ops (063-072)

Scientists focused on specific research domains:
- Read the `uacpgemini` repo for UACP architecture context
- Read the `Perplexterminal` repo for Quantum Context Terminal reference
- Key concepts: Supernova Reasoning, ObservabilitySignals, MCP mesh

## Governance (073-079)

Committee delegates coordinate cross-phase decisions:
- Agent-073: Engineering delegate
- Agent-074: Growth delegate
- Agent-075: Operations delegate
- Agent-076: Research delegate
- Agent-077: Revenue delegate
- Agent-078: Council secretary — records all decisions
- Agent-079: Compliance officer — GDPR, SOC2, data sovereignty

## QA & Testing (080-089)

QA agents test all system components:
- Read the specific QA agent mission file for testing scope
- Use `pytest` for backend tests
- Use Playwright for frontend E2E tests (via CDP at `http://localhost:29229`)
- Generate test evidence screenshots in `evidence/` directory

## Completion Checklist
- [ ] Read mission file and MASTER_STATE.md
- [ ] Execute assigned operational tasks
- [ ] Document findings in PROGRESS.md
- [ ] Create PR if code changes are needed
- [ ] Report status to Agent-000 (commander)
