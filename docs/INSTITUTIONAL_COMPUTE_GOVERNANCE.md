# Institutional Compute Governance Map

This is the canonical one-page doctrine and vocabulary map for Veklom, UACP, Sunnyvale, Silicon Valley, Archives, and Sovereign Builder Agents.

## Doctrine To Product Surfaces

| Doctrine | What it is | Product surfaces |
|---|---|---|
| Intent | Human or institutional goals, policies, and constraints expressed in a structured way. | Silicon Valley: policy sets, institutional stances, and what the institution is allowed to do. Deterministic Engine: the public narrative for what this system is for. |
| Reasoning | Multi-Model Consortium deliberation across multiple models and agents so no single model is trusted absolutely. | Sunnyvale: agent swarms, committees, workflows, and tools. Silicon Valley: levers for which models and agents sit on which committees, under what constraints. |
| Governance | UACP control plane that authorizes, constrains, and vetoes decisions at runtime based on policy and evidence. | Silicon Valley: global policy, convergence pressure, institutional telemetry, and escalation authority. Internals: registry of systems, agents, committees, risk tiers, and controls. |
| Specialized execution | Concrete tools, MCP servers, connectors, workflows, automations, and workers that touch real systems. | Sunnyvale: queues, tasks, jobs, pipelines, DevOps/infra tooling, and Builder Agents. Marketplace: Sovereign Builder Agents produce these as assets. |
| Auditable operation | Full decision traceability, observability, replayable logs, and evidence of control effectiveness. | Archives: Archives of Order, decision traces, provenance, and evidence ledger. Silicon Valley: institutional telemetry, posture, and audit views. |
| Autonomous continuity | The system keeps operating coherently over time through drift detection, historical learning, and policy/behavior alignment. | Archives: long-term institutional memory and replay. Silicon Valley: convergence dashboards, drift alerts, and institutional health. Sunnyvale: workflows that adapt using historical signals without breaking constraints. |

Sequence:

```text
Intent -> Consortium Reasoning -> UACP Governance -> Specialized Execution -> Auditable Operation -> Autonomous Continuity
```

## Product Layers

| Layer | Product name | Purpose | Exposes |
|---|---|---|---|
| 1 | Public Narrative: The Deterministic Engine | Mythology and visual identity. | Intent, governed autonomy, and the promise of replayable decisions without exposing doctrine internals. |
| 2 | Operational Product: Sunnyvale | Where the institution works. | Reasoning, committees, agents, workflows, tools, approvals, replays, safety rails, blocked jobs, and operator tools. |
| 3 | Sovereign Governance: Silicon Valley | Where the founder or institution governs. | Intent, UACP, institutional telemetry, convergence pressure, system health, escalation authority, and audit visibility. |
| 4 | Historical Continuity: Archives | Memory spine and replayable judgment. | Lineage, replay, historical state, recursive learning, auditable operation, and autonomous continuity. |

## Canonical Vocabulary

### Core Concepts

**Institutional Compute Governance**

UACP's job: govern how probabilistic intelligence from models and agents is converted into auditable institutional behavior. It is not just orchestration and not just observability.

**UACP: Unified Autonomous Control Plane**

The governance engine that registers systems, agents, committees, and tools; enforces policy and risk rules at decision time; vetoes or approves actions; records evidence and posture for audits.

**Multi-Model Consortium**

A governed set of models and agents that reason together before action. No single model has absolute authority; UACP defines the rules of deliberation and acceptance.

**Deterministic Engine**

The public mythology for the system. The promise is governed autonomy that behaves more like an institution than a stochastic toy. This is a narrative layer, not a product name.

### Product Surfaces

**Sunnyvale: Execution Floor**

Tenant-visible operational layer. Shows queues, workflows, agents, tasks, evidence, approvals, blocked jobs, and operator tools. It should feel useful, governed, and safe without exposing deep doctrine.

**Silicon Valley: Strategic Command Center**

Founder and institutional governance layer. Shows UACP, institutional telemetry, global policy, convergence pressure, escalation authority, and system health. This is the constitutional console.

**Archives: Institutional Memory**

The memory spine. Stores decision traces, overrides, failures, replays, policy changes, lineage, and institutional state transitions. Enables replayable judgment and autonomous continuity.

### Metrics And Primitives

**Certainty Index**

A governance-level signal summarizing confidence in a decision by combining model confidence, ensemble agreement, and evidence quality. Used by UACP and Silicon Valley, not surfaced raw to tenants.

**Determinism Ratio**

A measure of how repeatable decisions are under the same inputs and policies. High ratio means institution-like behavior; low ratio means stochastic toy behavior. Internal metric for governance and convergence.

**Archives of Order**

The curated subset of Archives representing stable institutional patterns: codified playbooks, resolved incidents, and "this is how we do things here now." Used by UACP and workflow designers.

**Convergence Pressure**

Signals and policies that push the system toward stable, consistent behavior over time, such as penalizing flakiness or raising requirements where replayability is poor. Exposed in Silicon Valley as institutional health.

### Builder And Marketplace Terms

**Sovereign Builder Agents**

UACP-governed Builder Agents that convert public pain into original infrastructure tools such as MCP servers, SDKs, CLIs, CI actions, connectors, and automation packs with clean-room discipline and full provenance.

**Veklom-Native Tool**

A tool built or vetted through UACP, designed to plug into Sunnyvale execution and Silicon Valley governance with telemetry, auth, billing hooks, and audit-friendly behavior.

### Governance And Observability

**Replayable Judgment**

The ability to reconstruct decisions step by step: inputs, reasoning traces, policies in force, escalations, and outcomes. Archives plus UACP provide this; it is the backbone of accountability.

**Governed Autonomy**

Default operating mode: agents can act autonomously within policy, while UACP can constrain, pause, or override based on risk, context, or drift.

**Decision Telemetry / Evidence Ledger**

Structured logs of decisions, signals, and control effectiveness. Used to prove governance maturity, not just to show that the system logged something.

## Hard Language Rules

- Use "Institutional Compute Governance" when describing UACP's category.
- Use "Sunnyvale" for tenant-visible operational execution.
- Use "Silicon Valley" for founder/institutional strategic governance.
- Use "Archives" for memory, lineage, replay, and continuity.
- Use "Deterministic Engine" only for public narrative and mythology.
- Do not describe UACP as just orchestration.
- Do not describe Archives as ordinary logs.
- Do not expose raw Certainty Index or Determinism Ratio to tenants unless a scoped product decision explicitly allows it.

