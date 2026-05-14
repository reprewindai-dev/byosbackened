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

## Infocodex V1 Surface Matrix

This table is Notion-ready. It maps doctrine to the four named surfaces and should be used when aligning product copy, UI hierarchy, investor narrative, and internal implementation.

| Doctrine element | Deterministic Engine (narrative) | Sunnyvale (execution floor) | Silicon Valley (governance) | Archives (memory spine) |
|---|---|---|---|---|
| Intent | Story of what the institution exists to do and why it must be governed, such as moving from stochastic toys to governed institutions. | Implicit in templates and workflows users choose, including onboarding wizards and domain presets. | Explicit policies, objectives, risk stances, and allowed domains of action. | Historical record of how intent evolved: older policies, retired charters, and previous institutional goals. |
| Reasoning (Multi-Model Consortium) | Simple framing: we never trust just one model; decisions are deliberated, not guessed. | Agent committees, toolchains, and workflows that call multiple models or agents, with approvals and reviews visible. | Controls for which models and agents sit on which committees, under which constraints and escalation rules. | Stored traces of consortium reasoning: which models participated, what they proposed, and what was accepted or rejected. |
| Governance (UACP) | Narrative that there is a control plane governing decisions, without deep technical detail. | Soft UX surfaces: governed workflow, requires approval, or UACP blocked this action. | Full UACP console: policy editor, risk tiers, controls library, live posture, and escalation authority. | Audit records of every UACP decision: veto, allow, override, and policy version in force at the time. |
| Specialized execution | High-level examples of what the system can do across telecom, finance, logistics, and other domains, not implementation detail. | Actual jobs: MCP calls, connectors, CI actions, automations, Builder Agent pipelines, tickets, and tasks. | Inventory view of controlled systems and tools; mapping between policies and specific execution surfaces. | Catalog of tools and runs with lineage: which version ran, against what systems, under what context. |
| Auditable operation | Plain-language promise that every important action is explainable and replayable. | In-app actions: view decision trace, show evidence, who approved this, and why was this blocked. | Dashboards for control effectiveness, violations, incident timelines, and audit readiness. | Full decision traces, evidence ledger, logs, and replay tools: the Archives of Order. |
| Autonomous continuity | Framed as the institution keeps learning and staying coherent over time, not just automating tasks. | Workflows that adapt based on historical outcomes, such as recommended playbooks and suggested automations, without breaking constraints. | Convergence and drift views: where behavior is stabilizing versus diverging, plus levers to tighten or relax policy. | Long-horizon records of policy changes, behavioral shifts, and institutional learning loops. |
| Certainty Index | High-level language: the engine knows when it is confident versus when to slow down and ask. | Occasionally shown as badges or hints, such as low confidence routed for review, not raw numbers. | Detailed metric: distributions by domain, thresholds for auto-approve versus escalate, and trends over time. | Historical curves of certainty versus outcomes, used to refine policies and model/agent ensembles. |
| Determinism Ratio | Idea that similar inputs lead to similar decisions, not numeric detail. | Hinted through stable workflow versus experimental labels; most users never see the raw ratio. | Internal metric: target bands and alerts when behavior becomes too stochastic in critical domains. | Time-series and snapshots of deterministic behavior per domain and policy era. |
| Archives of Order | Mythic phrase in narrative: we do not just log; we maintain an Archive of Order. | Summaries surfaced from the archive, such as playbooks and recommended actions, without showing the full machinery. | Tooling to promote archived patterns into policy or templates; institutionalization of good behavior. | The curated subset of the archive that encodes stable patterns and their provenance. |
| Convergence Pressure | Not mentioned explicitly; implied through smarter and more consistent over time language. | Visible indirectly through fewer manual interventions and more green runs, rather than as a named concept. | First-class in Silicon Valley: graphs of drift versus convergence, controls to adjust pressure by domain. | Historical record of convergence tuning and its effects; supports why the institution tightened or relaxed behavior. |
| Sovereign Builder Agents | Short story: Builder Agents turn public pain into original, governed tools. | UI panels for Builder pipelines: opportunities, in-progress builds, tests, and outcomes. | UACP rulesets for what Builders may target, legal constraints, duplication checks, and veto history. | Provenance and lineage of every built tool: sources, decisions, license checks, and marketplace versions. |

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
