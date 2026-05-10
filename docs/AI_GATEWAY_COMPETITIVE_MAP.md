# Veklom AI Gateway Competitive Map

## Objective

Position Veklom honestly as a sovereign AI gateway plus UACP control plane. The gateway gives teams fast model access, routing, limits, observability, and spend control. UACP is the institutional edge: it turns intent into governed plans, evidence, approvals, replay, and worker-owned action.

## Competitive Signals To Match

| Signal | Veklom production posture | Source of truth |
| --- | --- | --- |
| Unified AI endpoint | Live. `/api/v1/ai/complete` accepts model, messages, prompt, token controls, response format, session tag, redaction, on-prem lock, and billing event type. | `backend/apps/api/routers/ai.py` |
| Multi-route model support | Live. Ollama/Hetzner, Groq, OpenAI-compatible providers, Gemini-compatible providers, and AWS Bedrock are supported by the governed runtime path. | `backend/apps/api/routers/ai.py`, workspace model inventory |
| Self-hosted / sovereign route | Live. Ollama is the local-first route; PHI/HIPAA or explicit on-prem lock prevents hosted fallback. | `backend/apps/api/routers/ai.py` |
| Fallback and circuit breaker | Live. Ollama failures open circuit state and can route to Groq when policy permits. On-prem/protected sessions fail closed instead of leaking to fallback. | `backend/apps/api/routers/ai.py`, `core/llm/circuit_breaker.py` |
| RBAC and tenant isolation | Live. Workspace users, owner/admin checks, API-key scopes, and platform superuser gates separate tenant surfaces from founder/internal command surfaces. | `backend/apps/api/deps.py`, `backend/apps/api/routers/auth.py`, `frontend/workspace/src/routes.tsx` |
| API-key scopes | Live. Customer scopes are separated from reserved internal automation scopes; reserved scopes require platform superuser ownership. | `backend/apps/api/routers/auth.py`, `backend/apps/api/routers/internal_operators.py` |
| Rate limiting | Live. Redis sliding-window limits apply by IP and workspace; auth routes have tighter burst limits. | `backend/apps/api/middleware/rate_limit.py` |
| Budget and kill switch | Live. Budget middleware checks workspace/global caps and emergency kill-switch state before costly AI operations. | `backend/apps/api/middleware/budget_check.py` |
| Reserve billing and cost attribution | Live. Governed events debit operating reserve units by pricing tier and write token transactions with event metadata. | `backend/apps/api/routers/ai.py`, `backend/apps/api/routers/token_wallet.py`, `backend/PRICING_TRUTH.md` |
| Exact hot cache | Live for safe repeat requests. Non-sensitive, non-streaming, non-on-prem completions can use a Redis exact-match cache. PHI/PII/HIPAA/PCI and detected PII bypass cache. | `backend/apps/api/routers/ai.py` |
| Semantic cache | Not claimed. Needs a governed embedding store, tenant-scoped invalidation, sensitivity checks, and audit labeling before public positioning. | Gap |
| Observability | Live surfaces exist for request logs, monitoring overview, deployments, and platform pulse. Empty states must remain explicit when data is unavailable. | `frontend/workspace/src/pages/MonitoringPage.tsx`, `backend/apps/api/routers/workspace.py` |
| Endpoint creation and testing | Live. Deployments can be created, selected, tested on-page, and tied back to audit/usage records. | `backend/apps/api/routers/deployments.py`, `frontend/workspace/src/pages/DeploymentsPage.tsx` |
| OpenAI-compatible developer path | Live at deployment UX/code-snippet level; the platform still needs full OpenAI API parity testing before claiming complete drop-in equivalence. | `frontend/workspace/src/pages/DeploymentsPage.tsx` |
| Tool calling | Governed tools and pipelines exist as product modules. Do not claim arbitrary OpenAI function-calling parity until the schema/runtime contract is built. | Workspace tools/pipelines |
| Multimodal | Not claimed. The current governed completion route is text-first. | Gap |
| UACP governed plan/runs/artifacts | Live as paid event types. Free Evaluation has no free UACP runs; paid workspaces debit reserve per compile, run, and artifact. | `backend/apps/api/routers/ai.py`, `frontend/workspace/src/pages/UacpPage.tsx` |

## Positioning Rule

Veklom can sit next to AI gateway vendors by saying:

> Veklom is a sovereign AI gateway with UACP governance on top.

Do not reduce the product to "AI tools" or a generic marketplace. Tools are one module inside the hub. The core commercial promise is confidence: companies can deploy AI workers and model routes quickly without losing policy control, cost control, evidence, or escalation paths.

## Public Claims Allowed Now

- Unified governed AI endpoint.
- Multi-route models across local/self-hosted and hosted providers.
- Local-first Ollama/Hetzner route with approved fallback.
- Tenant-scoped RBAC and API-key scopes.
- Rate limits, budget caps, kill switches, and reserve billing.
- Signed audit chain and request/evidence logging.
- Same-page model, pipeline, deployment, and endpoint verification loops.
- Exact hot-cache for safe repeat AI completions.
- UACP paid planning/execution/artifact events.

## Public Claims Not Allowed Yet

- Semantic caching.
- Full multimodal gateway.
- Full OpenAI drop-in API parity across every endpoint.
- Arbitrary tool-calling/function invocation parity.
- Fully autonomous worker economy.
- Any fake latency, fake revenue, fake users, fake cache-hit rate, or fake marketplace demand.

## Build Priority

1. Keep the buyer path fast: default to healthy local/Ollama routes, fail clearly, and avoid routing buyers into broken providers.
2. Expand cache in order: exact cache first, then semantic cache only after tenant-scoped embeddings, policy filters, freshness windows, and audit labeling exist.
3. Close OpenAI-compatible parity gaps with tests before using "drop-in replacement" language.
4. Keep UACP priced above commodity gateway calls because it creates governed planning and proof artifacts, not just token completions.
5. Make every page finish its own loop: action, running state, result, proof, next action.
