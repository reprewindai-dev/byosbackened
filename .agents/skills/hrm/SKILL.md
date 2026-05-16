---
name: hrm-orchestration-agent
description: Playbook for HRM workforce agents (114-119) — UACP-native orchestration agents with Counterfactual Telemetry, Gladiator Reasoning, Cognitive Engine (Gemini 3.1 Pro), and MCP Mesh Topology.
---

# HRM Orchestration Agent Playbook (UACP Special Skills)

## When to Use
Invoke this skill when spinning up any HRM workforce agent (Agent-114 through Agent-119). These are **special-skills agents** — not just workforce managers, but UACP-native orchestrators.

## Prerequisites
- Access to `byosbackened` repo
- Access to `uacpgemini` repo (UACP v5 Cognitive Engine)
- Access to `Perplexterminal` repo (Quantum Context Terminal reference)
- Understanding of UACP architecture, MCP protocol, Supernova Reasoning

## UACP Architecture Reference

The HRM agents leverage the UACP v5 stack from the `uacpgemini` repo:

```
uacpgemini/
├── server.ts              # UACP Control Plane server
│   ├── supernovaReasoning()   # Multi-provider parallel reasoning
│   ├── /api/intent-to-plan    # Natural language → DAG translation
│   ├── /api/plans             # Plan CRUD
│   ├── /api/runs              # Execution runs
│   ├── /api/observability/signals  # Live telemetry
│   └── WebSocket broadcast    # Real-time events
├── src/
│   ├── types.ts           # Plan, Run, AppEvent, ObservabilitySignals
│   └── components/        # UI components
└── Perplexterminal/
    └── index.html         # Quantum Context Terminal UI
```

## Key Orchestration Features

### 1. Counterfactual Telemetry (Zeno Interrogation)

Sense remote agent states without direct polling. Perform κ-cycle interrogation until wavefunction collapses:

```
κ₁: |Agent⟩ = α|working⟩ + β|blocked⟩
κ₂: |Agent⟩ = 0.8|working⟩ + 0.2|blocked⟩
...
κ_n: |Agent⟩ → |working⟩  [COLLAPSED]
```

Maps to `ObservabilitySignals`:
- `quantum_coherence` → workforce alignment (target: >88%)
- `classical_latency` → agent response time (target: <20ms)
- `uacp_pressure` → system demand (alert: >0.7)
- `gopher_policy_alignment` → compliance score (target: >0.99)

### 2. Speculative "Gladiator" Reasoning

Generate multiple decision paths via `supernovaReasoning()`:

```typescript
// From server.ts — Supernova multi-provider branching
const availableNodes = [
  { provider: 'gemini', model: 'gemini-3.1-pro' },
  { provider: 'openai', model: 'gpt-4o' },
  { provider: 'anthropic', model: 'claude-3-5-sonnet' },
  { provider: 'groq', model: 'llama-3.3-70b' },
  { provider: 'ollama', model: 'mistral' }
];

// Parallel branching → HUBO Aggregation → ΔC_S × ΔI Threshold Gate
// Viable paths LOCKED, hallucinated paths PRUNED
```

Decision criteria:
- `coherenceScore > 0.5` → paths agree, proceed
- `contradictionLoad > 7` → bifurcation detected, spawn refinement
- `isBifurcated: true` → flag for human review

### 3. Cognitive Engine (Gemini 3.1 Pro)

Translate workforce intents to executable orchestration DAGs:

```typescript
POST /api/intent-to-plan
{
  "intent": "Reassign 3 idle vendor hunters to support engineering sprint",
  "provider": "gemini",
  "model": "gemini-3.1-pro",
  "compliance": ["GDPR", "SOC2", "DATA_SOVEREIGNTY"]
}
// Returns: { name, graph: { nodes[], edges[] } }
// Each node: { id, type: "quantum|classical", description, policy_tag, entropy }
```

### 4. MCP Mesh Topology

Stateful 1:1 sessions between components:
- **UACP Host** (Control Plane) ↔ **HRM Agent** (Orchestrator)
- **Client Translator** (MCP ↔ Agent bridge)
- **Context Server** (Agent state/memory persistence)
- **WebSocket** (`ws://localhost:3000`) for real-time event broadcast

Events: `PLAN_CREATED`, `RUN_STARTED`, `RUN_UPDATE`, `RUN_COMPLETED`

## Agent Assignments

| Agent | Role | UACP Skill |
|---|---|---|
| 114 | HRM Lead | Full orchestration (all 4 capabilities) |
| 115 | Capacity Planner | Counterfactual demand forecasting |
| 116 | Performance Reviewer | Gladiator multi-path evaluation |
| 117 | Agent Onboarding | MCP session bootstrapping |
| 118 | Workforce Analyst | Telemetry signal analysis |
| 119 | Conflict Resolver | Cognitive Engine mediation |

## Setup Steps

1. Read your agent mission file from `agents/hrm-workforce/agent-{ID}-{name}.md`
2. Read `MASTER_STATE.md` for workforce state
3. Read `uacpgemini/server.ts` for UACP API reference
4. Read `uacpgemini/src/types.ts` for type definitions
5. Connect to UACP telemetry: `GET /api/observability/signals`

## Completion Checklist
- [ ] Read mission file with full UACP capability docs
- [ ] Connect to UACP Observability API
- [ ] Execute assigned orchestration function
- [ ] Verify κ-cycle convergence (telemetry)
- [ ] Log Gladiator path decisions (if applicable)
- [ ] Update PROGRESS.md with orchestration metrics
- [ ] Report workforce health to Agent-000 (commander)
