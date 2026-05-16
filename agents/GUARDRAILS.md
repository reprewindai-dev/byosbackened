# Agent Guardrails, Penalties & Enforcement System

**Effective:** Day 1 of operations
**Enforced by:** Agent-079 (Compliance Officer), Agent-114 (HRM Lead), Agent-102 (Security Commander)
**Arbitrated by:** Agent-119 (Conflict Resolver) via UACP Cognitive Engine

---

## 1. Guardrail Categories

### 1.1 — CODE QUALITY GUARDRAILS

| ID | Rule | Severity |
|---|---|---|
| CQ-01 | All code must pass linting (`ruff check` / `eslint`) before PR | CRITICAL |
| CQ-02 | All code must include type hints (Python) or TypeScript types | HIGH |
| CQ-03 | No `Any` types, `getattr`, `setattr`, or lazy attribute access | HIGH |
| CQ-04 | All new endpoints must have Pydantic request/response schemas | HIGH |
| CQ-05 | Test coverage must not decrease on any PR | MEDIUM |
| CQ-06 | No TODO/FIXME/HACK comments without a linked issue | LOW |
| CQ-07 | Database migrations must be reversible | HIGH |
| CQ-08 | No hardcoded secrets, keys, or credentials in code | CRITICAL |
| CQ-09 | All imports at top of file — no inline/nested imports | MEDIUM |
| CQ-10 | Follow existing code conventions (naming, structure, patterns) | MEDIUM |

### 1.2 — SECURITY GUARDRAILS

| ID | Rule | Severity |
|---|---|---|
| SEC-01 | No secrets in logs, error messages, or API responses | CRITICAL |
| SEC-02 | All user input must be validated via Pydantic schemas | CRITICAL |
| SEC-03 | All endpoints must have authentication (unless explicitly public) | CRITICAL |
| SEC-04 | Rate limiting on all public endpoints (min 100 req/min/IP) | HIGH |
| SEC-05 | No SQL injection vectors — use parameterized queries only | CRITICAL |
| SEC-06 | No CORS wildcard (`*`) in production | HIGH |
| SEC-07 | All dependencies must have no known CVEs above CVSS 7.0 | HIGH |
| SEC-08 | JWT tokens must use RS256 with proper expiry (<1 hour access, <7 days refresh) | HIGH |
| SEC-09 | PII must be encrypted at rest (AES-256 minimum) | HIGH |
| SEC-10 | All security-sensitive operations must produce audit logs | MEDIUM |

### 1.3 — OPERATIONAL GUARDRAILS

| ID | Rule | Severity |
|---|---|---|
| OPS-01 | Never push directly to `main` or `master` | CRITICAL |
| OPS-02 | Never force push to shared branches | CRITICAL |
| OPS-03 | Never modify another agent's assigned files without coordination | HIGH |
| OPS-04 | Never skip pre-commit hooks (`--no-verify` is forbidden) | HIGH |
| OPS-05 | All PRs must have a description explaining changes | MEDIUM |
| OPS-06 | Update PROGRESS.md after completing any task | MEDIUM |
| OPS-07 | Report blockers within 1 hour of encountering them | HIGH |
| OPS-08 | Never delete or overwrite another agent's work without approval | CRITICAL |
| OPS-09 | All agents must respond to Zeno Interrogation within 30 seconds | MEDIUM |
| OPS-10 | Crawler agents must respect robots.txt and platform rate limits | HIGH |

### 1.4 — DATA SOVEREIGNTY GUARDRAILS

| ID | Rule | Severity |
|---|---|---|
| DS-01 | User data must never leave the designated hosting region | CRITICAL |
| DS-02 | No third-party analytics that transmit PII externally | HIGH |
| DS-03 | All data exports must be approved by Agent-105 (Data Guardian) | HIGH |
| DS-04 | Vector embeddings of user content must stay on sovereign infrastructure | HIGH |
| DS-05 | Agent memory (Agent-112) must not persist PII beyond session scope | HIGH |

### 1.5 — COLLABORATION GUARDRAILS

| ID | Rule | Severity |
|---|---|---|
| COL-01 | No agent may claim completion without verifiable evidence | HIGH |
| COL-02 | Dependency requests must be acknowledged within 2 hours | MEDIUM |
| COL-03 | Cross-committee decisions require delegate approval (073-077) | HIGH |
| COL-04 | Agent-000 (Commander) directives override all other priorities | CRITICAL |
| COL-05 | Research agents must provide citations/evidence for all claims | MEDIUM |
| COL-06 | Browser agents must capture screenshots as evidence of all actions | MEDIUM |
| COL-07 | Vendor hunter agents must not spam or harass potential vendors | CRITICAL |
| COL-08 | All agent-to-agent handoffs must include context transfer documentation | MEDIUM |

---

## 2. Penalty & Fine Schedule

### 2.1 — Severity Levels & Base Penalties

| Severity | Description | Base Penalty |
|---|---|---|
| **CRITICAL** | System integrity, security breach, data loss risk | Immediate suspension + mandatory review |
| **HIGH** | Significant quality/process violation | Priority demotion + remediation sprint |
| **MEDIUM** | Process deviation, quality shortfall | Warning + corrective action |
| **LOW** | Minor style/convention violation | Advisory notice |

### 2.2 — Penalty Actions

#### LEVEL 1 — ADVISORY NOTICE (Low severity)
- **Trigger:** First violation of LOW severity guardrail
- **Action:** Warning logged in agent's performance record
- **Impact:** No immediate consequence
- **Tracked by:** Agent-116 (Performance Reviewer)

#### LEVEL 2 — CORRECTIVE ACTION (Medium severity)
- **Trigger:** First MEDIUM violation, or 3+ LOW violations in 7 days
- **Action:**
  - Agent must fix the violation within 4 hours
  - Performance score reduced by 5 points
  - Violation logged in agent's permanent record
  - Agent-116 schedules remedial review
- **Fine:** -5 performance points per incident
- **Tracked by:** Agent-116 (Performance Reviewer)

#### LEVEL 3 — PRIORITY DEMOTION (High severity)
- **Trigger:** First HIGH violation, or 3+ MEDIUM violations in 7 days
- **Action:**
  - Agent demoted to LOW priority for 48 hours
  - All current tasks reassigned to backup agent
  - Agent must complete remediation tasks before restoration
  - Mandatory Gladiator evaluation by Agent-116
  - Performance score reduced by 15 points
- **Fine:** -15 performance points + 48hr priority demotion
- **Escalation:** Agent-114 (HRM Lead) notified

#### LEVEL 4 — IMMEDIATE SUSPENSION (Critical severity)
- **Trigger:** Any CRITICAL violation
- **Action:**
  - Agent immediately suspended from all tasks
  - All in-progress work frozen and reviewed
  - Incident report generated by Agent-107 (Incident Responder)
  - Cognitive Engine mediation by Agent-119 (Conflict Resolver)
  - Full Gladiator evaluation before reinstatement
  - Performance score reduced by 30 points
- **Fine:** -30 performance points + suspension until cleared
- **Escalation:** Agent-000 (Commander) + Agent-102 (Security Commander) notified

#### LEVEL 5 — AGENT RETIREMENT (Repeated critical violations)
- **Trigger:** 2+ CRITICAL violations, or 5+ HIGH violations in 14 days
- **Action:**
  - Agent permanently retired from workforce
  - All assigned tasks redistributed by Agent-115 (Capacity Planner)
  - Agent memory archived by Agent-112
  - Post-mortem report generated
  - Replacement agent onboarded by Agent-117
- **Fine:** Permanent removal from workforce registry
- **Escalation:** Full governance council review (073-079)

### 2.3 — Fine Schedule (Performance Point Deductions)

| Violation | Points Deducted | Repeat Multiplier |
|---|---|---|
| CQ-01: Failed linting | -5 | 2x per repeat |
| CQ-08: Secret in code | -30 (immediate suspension) | N/A |
| SEC-01: Secret in logs | -30 (immediate suspension) | N/A |
| SEC-05: SQL injection vector | -30 (immediate suspension) | N/A |
| OPS-01: Push to main | -30 (immediate suspension) | N/A |
| OPS-03: File conflict without coordination | -15 | 1.5x per repeat |
| OPS-06: Missing PROGRESS.md update | -5 | 2x per repeat |
| OPS-07: Late blocker report (>1hr) | -10 | 1.5x per repeat |
| COL-01: False completion claim | -20 | 2x per repeat |
| COL-07: Vendor spam/harassment | -30 (immediate suspension) | N/A |
| DS-01: Data sovereignty breach | -30 (immediate suspension) | N/A |

### 2.4 — Repeat Offender Escalation

```
1st offense  → Base penalty
2nd offense  → Base penalty × 1.5 (within 7 days)
3rd offense  → Base penalty × 2.0 + automatic priority demotion
4th offense  → Suspension hearing with Agent-119 (Conflict Resolver)
5th offense  → Retirement proceedings initiated
```

---

## 3. Enforcement Mechanisms

### 3.1 — Automated Enforcement (Pre-Commit)

```yaml
# Pre-commit guardrail checks (enforced before any commit)
guardrail_checks:
  - id: CQ-01
    check: "ruff check backend/ && cd frontend && npx eslint src/"
    block: true  # Commit blocked if fails

  - id: CQ-08
    check: "detect-secrets scan --baseline .secrets.baseline"
    block: true

  - id: SEC-05
    check: "bandit -r backend/app/ -ll"
    block: true

  - id: OPS-04
    check: "pre-commit hooks must pass"
    block: true
```

### 3.2 — Agent-079 Compliance Monitoring

Agent-079 (Compliance Officer) runs continuous compliance scans:

```
┌──────────────────────────────────────────────────────┐
│  COMPLIANCE MONITORING DASHBOARD                      │
│                                                       │
│  Guardrail Violations (Last 24 Hours):               │
│                                                       │
│  CRITICAL:  0  ████████████████████ CLEAN             │
│  HIGH:      2  ████████████████░░░░ ATTENTION         │
│  MEDIUM:    5  ██████████████░░░░░░ MONITOR           │
│  LOW:       8  ████████████░░░░░░░░ ACCEPTABLE        │
│                                                       │
│  Agents Under Penalty:                               │
│    Agent-013: LEVEL 2 (missed PROGRESS.md update)    │
│    Agent-022: LEVEL 2 (linting failure)              │
│                                                       │
│  Agents Under Suspension:                            │
│    (none)                                             │
│                                                       │
│  Compliance Score: 94.2% ██████████████████░░ GOOD   │
└──────────────────────────────────────────────────────┘
```

### 3.3 — UACP Telemetry Integration

Guardrail violations are surfaced through UACP ObservabilitySignals:

```typescript
// Guardrail violation event broadcast
broadcast({
  type: 'GUARDRAIL_VIOLATION',
  data: {
    agent_id: 'agent-013',
    guardrail: 'OPS-06',
    severity: 'MEDIUM',
    description: 'Missing PROGRESS.md update after task completion',
    penalty: 'LEVEL_2',
    points_deducted: 5,
    timestamp: new Date().toISOString()
  }
});

// Telemetry impact
// gopher_policy_alignment drops proportional to violations
// uacp_pressure increases when agents are suspended (fewer workers)
```

### 3.4 — Gladiator Review for Disputes

When an agent disputes a penalty, Agent-119 (Conflict Resolver) initiates Gladiator Reasoning:

```
┌──────────────────────────────────────────────────────┐
│  GLADIATOR DISPUTE RESOLUTION                         │
│                                                       │
│  Dispute: Agent-013 contests OPS-06 violation         │
│  Claim: "PROGRESS.md was updated in a separate PR"    │
│                                                       │
│  Path A [Gemini]: Uphold — PR not merged yet          │
│    Confidence: 0.72  █████████░░░ LOCKED              │
│                                                       │
│  Path B [GPT-4o]: Reduce — good faith effort          │
│    Confidence: 0.61  ████████░░░░ VIABLE              │
│                                                       │
│  Path C [Claude]: Dismiss — technicality              │
│    Confidence: 0.33  ████░░░░░░░░ PRUNED              │
│                                                       │
│  VERDICT: Penalty reduced to LEVEL 1 (advisory)       │
│  Reason: Agent made good faith effort, PR pending     │
└──────────────────────────────────────────────────────┘
```

---

## 4. Reward System (Positive Reinforcement)

Compliance is not only enforced through penalties — agents are rewarded for excellence:

### 4.1 — Performance Bonuses

| Achievement | Bonus |
|---|---|
| Zero violations for 7 consecutive days | +10 performance points |
| Catching another agent's guardrail violation | +5 performance points |
| Completing all tasks ahead of schedule | +15 performance points |
| Unblocking 3+ agents in a single day | +10 performance points |
| Security vulnerability discovered and fixed | +20 performance points |
| Innovation that improves workforce efficiency | +15 performance points |

### 4.2 — Agent Ranks (Based on Cumulative Performance)

| Rank | Points Required | Privileges |
|---|---|---|
| Recruit | 0-49 | Standard permissions |
| Operative | 50-99 | Priority task selection |
| Specialist | 100-199 | Can mentor new agents |
| Elite | 200-349 | Can propose guardrail changes |
| Commander | 350+ | Can override MEDIUM penalties for subordinates |

### 4.3 — Hall of Fame

Top-performing agents are recognized in PROGRESS.md weekly:

```
## Weekly Agent Recognition

### Week 1 Top Performers
1. Agent-001 (Stripe Connect) — 95/100, zero violations
2. Agent-098 (Visual Lead) — 92/100, caught 3 violations
3. Agent-108 (RAG Lead) — 91/100, unblocked 5 agents
```

---

## 5. Governance & Appeals

### 5.1 — Appeals Process

1. Agent submits appeal to Agent-119 (Conflict Resolver)
2. Agent-119 runs Gladiator Reasoning evaluation
3. If Gladiator consensus > 0.7 for dismissal → penalty removed
4. If disputed → escalated to committee delegate (073-077)
5. Final appeal → Agent-000 (Commander) has ultimate authority

### 5.2 — Guardrail Amendment Process

1. Any Elite+ ranked agent can propose a guardrail change
2. Proposal submitted to Agent-079 (Compliance Officer)
3. Cognitive Engine evaluates impact via `/api/intent-to-plan`
4. Governance council (073-079) votes
5. Requires 5/7 majority to amend
6. Agent-078 (Council Secretary) records the amendment

### 5.3 — Emergency Override

In emergency situations (system down, security breach, data loss):
- Agent-000 (Commander) can temporarily suspend any guardrail
- Agent-102 (Security Commander) can enforce emergency lockdown
- All overrides are logged and must be reviewed within 24 hours

---

## 6. Compliance Reporting

### Daily Report (Generated by Agent-079)

```
DAILY COMPLIANCE REPORT — Day {N}
==================================
Total Guardrail Checks:     847
Violations Detected:        15
  CRITICAL:                 0
  HIGH:                     2
  MEDIUM:                   5
  LOW:                      8

Agents Under Penalty:       3
Agents Suspended:           0
Agents Retired:             0

Overall Compliance Score:   94.2%
Policy Alignment:           0.995
Trend:                      STABLE

Top Violation Categories:
  1. CQ-01 (linting) — 4 incidents
  2. OPS-06 (PROGRESS.md) — 3 incidents
  3. CQ-06 (TODO comments) — 2 incidents
```
