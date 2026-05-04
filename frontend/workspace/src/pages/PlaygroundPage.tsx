// =============================================================================
// DEVELOPER NOTE — READ BEFORE TOUCHING CONVERSATION STATE
// =============================================================================
// Added by: Perplexity AI (on behalf of Veklom founder), 2026-05-04
//
// WHY THIS WAS ADDED:
//   The original playground was single-shot only — every "Run" wiped the
//   previous response and started fresh. There was zero conversation memory.
//   Competing products (OpenAI Playground, Bedrock Console, Anthropic Console)
//   all support multi-turn back-and-forth. Customers expect it and stay longer
//   when they can build on previous answers mid-session.
//
// WHAT WAS CHANGED:
//   1. New `ConversationTurn` interface — tracks role (user/assistant),
//      message content, model slug used, timestamp, and per-turn stats.
//   2. New `conversation` state array — the full thread for the session.
//   3. `run()` now APPENDS to the thread instead of replacing responseText.
//      It also passes the previous turns as context to /ai/complete via the
//      new `messages` field (array of {role, content} pairs). Backend must
//      support this field — if it doesn't yet, it gracefully falls back to
//      single-shot (the `prompt` field is still sent as before).
//   4. New conversation thread UI rendered above the prompt textarea.
//   5. "Clear conversation" button resets the thread.
//   6. Model can be switched between turns — each turn records which model
//      was used so the thread stays honest even mid-session model switches.
//
// WHAT WAS NOT CHANGED:
//   - No token system. No credits per turn beyond what already existed.
//   - No streaming (that's a separate backend concern).
//   - All existing features (preflight, save-as-pipeline, export audit,
//     event log, telemetry, vertical selector) are fully preserved.
//
// BACKEND CONTRACT:
//   POST /ai/complete now receives an optional `messages` array:
//     [{ role: "user" | "assistant", content: string }, ...]
//   If the backend ignores it, single-shot still works. When the backend
//   honours it, the model gets full conversation context. Wire this up on
//   the backend side when ready — the frontend is already sending it.
//
// DO NOT:
//   - Remove the `conversation` state without replacing it with something else.
//   - Reset `conversation` inside `run()` — only `clearConversation()` should do that.
//   - Change ConversationTurn shape without updating the thread render below.
// =============================================================================

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  CircleStop,
  Cpu,
  Download,
  Gauge,
  GitBranch,
  Loader2,
  MessageSquare,
  Play,
  Save,
  Shield,
  Sparkles,
  Trash2,
  TrendingDown,
  Zap,
} from "lucide-react";
import { api } from "@/lib/api";
import { cn } from "@/lib/cn";
import { responseDetail } from "@/lib/errors";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface PreflightState {
  predicted_cost?: number;
  cost_confidence_lower?: number;
  cost_confidence_upper?: number;
  alternatives?: { provider: string; cost: string; savings_percent: number }[];
  predicted_quality?: number;
  failure_risk?: number;
  loading?: boolean;
  error?: string;
}

type Vertical = "default" | "legal" | "medical" | "finance" | "agency" | "infrastructure";

interface PipelineEvent {
  id: string;
  event: string;
  data: Record<string, unknown>;
  ts: number;
}

interface WorkspaceModel {
  slug: string;
  name: string;
  provider: string;
  runtime_model_id: string;
  enabled: boolean;
  connected: boolean;
}

interface AICompleteResponse {
  response_text: string;
  model: string;
  bedrock_model_id: string;
  provider?: string;
  request_id?: string;
  audit_log_id?: string;
  audit_hash?: string;
  prompt_tokens?: number;
  tokens_deducted: number;
  output_tokens: number;
  total_tokens?: number;
  latency_ms?: number;
  cost_usd?: string;
  wallet_balance: number;
  timestamp: string;
}

/**
 * A single turn in the multi-turn conversation thread.
 * Added 2026-05-04 — see developer note at top of file.
 */
interface ConversationTurn {
  id: string;
  role: "user" | "assistant";
  content: string;
  modelSlug?: string;       // which model answered (assistant turns only)
  provider?: string;        // provider for this turn
  cost_usd?: string;        // per-turn cost
  tokens?: number;          // completion tokens for this turn
  latency_ms?: number;
  ts: number;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const VERTICALS: { value: Vertical; label: string; hint: string }[] = [
  { value: "default", label: "General", hint: "Broad control-plane request" },
  { value: "legal", label: "Legal", hint: "Privacy-first legal ops" },
  { value: "medical", label: "Medical", hint: "HIPAA-aware clinical ops" },
  { value: "finance", label: "Finance", hint: "SOC2 / PCI-aware" },
  { value: "agency", label: "Agency", hint: "Multi-tenant copilot" },
  { value: "infrastructure", label: "Infrastructure", hint: "SNMP / Modbus bridge" },
];

const SAMPLE_PROMPTS: Record<Vertical, string> = {
  default: "Summarize why sovereignty matters for regulated AI workloads in three bullets.",
  legal: "Draft a privacy-first intake workflow for handling PII in client matters.",
  medical: "Explain the PHI controls you would enforce on an intake chatbot.",
  finance: "Outline the SOC2 audit artifacts you would generate for each AI decision.",
  agency: "Describe tenant isolation for a 50-client agency running shared models.",
  infrastructure: "Translate a stream of SNMP traps into a governed AI incident triage.",
};

const EVENT_META: Record<string, { label: string; color: string; icon: string }> = {
  workspace_request: { label: "Workspace request", color: "text-bone", icon: "*" },
  auth_check: { label: "Auth check", color: "text-electric", icon: ">" },
  wallet_check: { label: "Wallet check", color: "text-electric", icon: "$" },
  provider_selected: { label: "Provider chosen", color: "text-brass-2", icon: ">" },
  response_complete: { label: "Response complete", color: "text-moss", icon: "+" },
  audit_written: { label: "Audit written", color: "text-moss", icon: "+" },
  cost_recorded: { label: "Cost recorded", color: "text-moss", icon: "+" },
  done: { label: "Done", color: "text-moss", icon: "*" },
  error: { label: "Error", color: "text-crimson", icon: "!" },
};

const DEFAULT_MAX_TOKENS = 64;
const REQUEST_TIMEOUT_MS = 90_000;
const MAX_CONVERSATION_TURNS = 20; // safety cap — keeps context window sane

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function normalizeModel(raw: unknown): WorkspaceModel {
  const row = raw as Record<string, unknown>;
  const slug = String(row.slug ?? row.model_slug ?? "");
  const runtime = String(row.bedrock_model_id ?? row.runtime_model_id ?? row.model ?? slug);
  return {
    slug,
    name: String(row.name ?? row.display_name ?? row.model_slug ?? slug),
    provider: String(row.provider ?? "local"),
    runtime_model_id: runtime,
    enabled: row.enabled !== false,
    connected: row.connected !== false,
  };
}

async function fetchWorkspaceModels(): Promise<WorkspaceModel[]> {
  const resp = await api.get<{ models?: unknown[]; items?: unknown[] } | unknown[]>("/workspace/models");
  const body = resp.data;
  const raw = Array.isArray(body) ? body : body.models ?? body.items ?? [];
  return raw.map(normalizeModel).filter((model) => Boolean(model.slug));
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function PlaygroundPage() {
  const [vertical, setVertical] = useState<Vertical>("default");
  const [prompt, setPrompt] = useState(SAMPLE_PROMPTS.default);
  const [maxTokens, setMaxTokens] = useState(DEFAULT_MAX_TOKENS);
  const [selectedModelSlug, setSelectedModelSlug] = useState("");
  const [running, setRunning] = useState(false);
  const [events, setEvents] = useState<PipelineEvent[]>([]);
  const [responseText, setResponseText] = useState("");

  // -------------------------------------------------------------------------
  // Multi-turn conversation history (added 2026-05-04 — see note at top)
  // -------------------------------------------------------------------------
  const [conversation, setConversation] = useState<ConversationTurn[]>([]);
  const threadRef = useRef<HTMLDivElement>(null);

  const clearConversation = useCallback(() => {
    setConversation([]);
    setResponseText("");
    setEvents([]);
  }, []);

  const appendTurn = useCallback((turn: Omit<ConversationTurn, "id" | "ts">) => {
    setConversation((prev) => [
      ...prev.slice(-MAX_CONVERSATION_TURNS),
      { ...turn, id: `${turn.role}-${Date.now()}`, ts: Date.now() },
    ]);
  }, []);
  // -------------------------------------------------------------------------

  const [stats, setStats] = useState<{
    provider?: string;
    model?: string;
    runtime_model_id?: string;
    prompt_tokens?: number;
    completion_tokens?: number;
    total_tokens?: number;
    latency_ms?: number;
    request_id?: string;
    audit_hash?: string;
    tokens_deducted?: number;
    wallet_balance?: number;
    cost_usd?: string;
  }>({});
  const [error, setError] = useState<string | null>(null);
  const [preflight, setPreflight] = useState<PreflightState>({});
  const [savedPipelineSlug, setSavedPipelineSlug] = useState<string | null>(null);
  const [savingPipeline, setSavingPipeline] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const feedRef = useRef<HTMLDivElement>(null);

  const models = useQuery({
    queryKey: ["playground-models"],
    queryFn: fetchWorkspaceModels,
    refetchInterval: 30_000,
  });

  const runnableModels = useMemo(
    () => (models.data ?? []).filter((model) => model.enabled && model.connected),
    [models.data],
  );

  useEffect(() => {
    if (!selectedModelSlug && runnableModels.length > 0) {
      setSelectedModelSlug(runnableModels[0]!.slug);
    }
  }, [runnableModels, selectedModelSlug]);

  const selectedModel = useMemo(
    () => runnableModels.find((model) => model.slug === selectedModelSlug) ?? runnableModels[0],
    [runnableModels, selectedModelSlug],
  );

  const appendEvent = useCallback((event: string, data: Record<string, unknown> = {}) => {
    setEvents((prev) => [
      ...prev,
      { id: `${event}-${Date.now()}-${prev.length}`, event, data, ts: Date.now() },
    ]);
  }, []);

  // Scroll thread to bottom whenever a new turn lands
  useEffect(() => {
    if (threadRef.current) threadRef.current.scrollTop = threadRef.current.scrollHeight;
  }, [conversation.length]);

  const handleVerticalChange = (v: Vertical) => {
    setVertical(v);
    if (prompt === SAMPLE_PROMPTS[vertical]) setPrompt(SAMPLE_PROMPTS[v]);
  };

  const stop = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setRunning(false);
  }, []);

  const run = useCallback(async () => {
    if (running || !selectedModel || !prompt.trim()) return;

    const controller = new AbortController();
    abortRef.current = controller;
    const startedAt = performance.now();

    // Add user turn to conversation thread BEFORE the request fires
    const userContent = prompt.trim();
    appendTurn({ role: "user", content: userContent });

    setEvents([]);
    setResponseText("");
    setStats({});
    setError(null);
    setSavedPipelineSlug(null);
    setRunning(true);

    appendEvent("workspace_request", {
      endpoint: "/api/v1/ai/complete",
      model: selectedModel.slug,
      max_tokens: maxTokens,
    });
    appendEvent("auth_check", { status: "bearer token attached", tenant_scope: "current workspace" });
    appendEvent("wallet_check", { status: "reservation requested", model: selectedModel.slug });
    appendEvent("provider_selected", {
      provider: selectedModel.provider,
      model: selectedModel.slug,
      runtime_model_id: selectedModel.runtime_model_id,
    });

    // Build messages array for multi-turn context. Backend honours this if
    // it supports conversational /ai/complete; otherwise falls back to prompt.
    const messages = conversation
      .slice(-MAX_CONVERSATION_TURNS)
      .map((t) => ({ role: t.role, content: t.content }))
      .concat([{ role: "user" as const, content: userContent }]);

    try {
      const resp = await api.post<AICompleteResponse>(
        "/ai/complete",
        {
          model: selectedModel.slug,
          prompt: userContent.slice(0, 800),
          messages,                           // multi-turn context — see note at top
          max_tokens: maxTokens,
        },
        { signal: controller.signal, timeout: REQUEST_TIMEOUT_MS },
      );
      const elapsedMs = Math.round(performance.now() - startedAt);
      const payload = resp.data;
      const provider = payload.provider ?? selectedModel.provider;
      const latency = payload.latency_ms ?? elapsedMs;

      setResponseText(payload.response_text);
      setStats({
        provider,
        model: payload.model,
        runtime_model_id: payload.bedrock_model_id,
        prompt_tokens: payload.prompt_tokens,
        completion_tokens: payload.output_tokens,
        total_tokens: payload.total_tokens,
        latency_ms: latency,
        request_id: payload.request_id,
        audit_hash: payload.audit_hash,
        tokens_deducted: payload.tokens_deducted,
        wallet_balance: payload.wallet_balance,
        cost_usd: payload.cost_usd,
      });

      // Append assistant turn to conversation thread
      appendTurn({
        role: "assistant",
        content: payload.response_text,
        modelSlug: selectedModel.slug,
        provider,
        cost_usd: payload.cost_usd,
        tokens: payload.output_tokens,
        latency_ms: latency,
      });

      // Clear the prompt input so the user can type the next message naturally
      setPrompt("");

      appendEvent("response_complete", {
        provider,
        model: payload.model,
        output_tokens: payload.output_tokens,
        latency_ms: latency,
      });
      appendEvent("audit_written", {
        audit_log_id: payload.audit_log_id,
        audit_hash: payload.audit_hash,
      });
      appendEvent("cost_recorded", {
        credits_charged: payload.tokens_deducted,
        wallet_balance: payload.wallet_balance,
        cost_usd: payload.cost_usd,
      });
      appendEvent("done", {
        request_id: payload.request_id,
        total_latency_ms: latency,
      });
    } catch (err) {
      const aborted = (err as { code?: string })?.code === "ERR_CANCELED";
      const message = aborted ? "Request cancelled before completion." : responseDetail(err);
      setError(message);
      appendEvent("error", {
        endpoint: "/api/v1/ai/complete",
        message,
      });
    } finally {
      abortRef.current = null;
      setRunning(false);
    }
  }, [appendEvent, appendTurn, conversation, maxTokens, prompt, running, selectedModel]);

  useEffect(() => {
    return () => stop();
  }, [stop]);

  useEffect(() => {
    if (feedRef.current) feedRef.current.scrollTop = feedRef.current.scrollHeight;
  }, [events.length]);

  const runPreflight = useCallback(async () => {
    if (!prompt.trim()) return;
    setPreflight({ loading: true });
    try {
      const costResp = await api.post("/cost/predict", {
        operation_type: "generation",
        provider: selectedModel?.provider ?? "local",
        input_text: prompt.slice(0, 4000),
        model: selectedModel?.runtime_model_id ?? selectedModelSlug,
      });
      const cost = costResp.data as {
        predicted_cost: string;
        confidence_lower: string;
        confidence_upper: string;
        alternative_providers: { provider: string; cost: string; savings_percent: number }[];
      };

      const next: PreflightState = {
        predicted_cost: parseFloat(cost.predicted_cost),
        cost_confidence_lower: parseFloat(cost.confidence_lower),
        cost_confidence_upper: parseFloat(cost.confidence_upper),
        alternatives: cost.alternative_providers,
        loading: false,
      };

      const params = {
        operation_type: "generation",
        provider: selectedModel?.provider ?? "local",
        input_text: prompt.slice(0, 2000),
      };
      try {
        const qResp = await api.post("/autonomous/quality/predict", null, { params });
        const q = qResp.data as { predicted_quality?: number };
        if (q?.predicted_quality != null) next.predicted_quality = q.predicted_quality;
      } catch {
        /* ML may still be warming for a fresh workspace. */
      }
      try {
        const rResp = await api.post("/autonomous/quality/failure-risk", null, { params });
        const r = rResp.data as { failure_risk?: number; risk?: number };
        const risk = r?.failure_risk ?? r?.risk;
        if (risk != null) next.failure_risk = risk;
      } catch {
        /* ML may still be warming for a fresh workspace. */
      }

      setPreflight(next);
    } catch (err) {
      setPreflight({ loading: false, error: responseDetail(err) });
    }
  }, [prompt, selectedModel, selectedModelSlug]);

  const saveAsPipeline = useCallback(async () => {
    if (!prompt.trim() || savingPipeline) return;
    setSavingPipeline(true);
    try {
      const name = `Playground - ${vertical} - ${new Date().toLocaleDateString()}`;
      const resp = await api.post<{ slug: string }>("/pipelines", {
        name,
        description: `Saved from Playground (${vertical}). Original prompt preserved as input node.`,
        graph: {
          nodes: [
            { id: "input", type: "prompt", label: "User input", prompt },
            { id: "policy", type: "gate", label: "Policy gate", policy: "default" },
            { id: "llm", type: "model", label: "LLM step", model: stats.model || selectedModelSlug },
          ],
          edges: [
            { from: "input", to: "policy" },
            { from: "policy", to: "llm" },
          ],
        },
      });
      setSavedPipelineSlug(resp.data.slug);
    } catch (err) {
      setError(responseDetail(err));
    } finally {
      setSavingPipeline(false);
    }
  }, [prompt, savingPipeline, selectedModelSlug, stats.model, vertical]);

  const eventCount = events.length;
  const tokenCount = stats.completion_tokens ?? 0;
  const canRun = Boolean(prompt.trim() && selectedModel && !models.isLoading && !models.isError);

  const exportAudit = () => {
    const blob = new Blob(
      [
        JSON.stringify(
          {
            exported_at: new Date().toISOString(),
            request_id: stats.request_id,
            vertical,
            prompt,
            conversation,       // now includes full multi-turn thread
            response: responseText,
            stats,
            events,
          },
          null,
          2,
        ),
      ],
      { type: "application/json" },
    );
    const href = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = href;
    a.download = `veklom-audit-${stats.request_id ?? Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(href);
  };

  return (
    <div className="mx-auto w-full max-w-7xl space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="mb-1 font-mono text-[11px] uppercase tracking-[0.15em] text-muted">
            Workspace - Playground
          </div>
          <h1 className="text-3xl font-semibold tracking-tight">Authenticated AI execution</h1>
          <p className="mt-2 max-w-2xl text-sm text-bone-2">
            Send a real workspace request through Veklom's wallet-backed completion endpoint. The backend selects the
            runtime, enforces model availability, records the cost entry, and writes the audit artifact.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <span className="v-chip v-chip-ok">
              <span className="h-1.5 w-1.5 animate-pulse-soft rounded-full bg-moss" />
              authenticated - <span className="font-mono">/api/v1/ai/complete</span>
            </span>
            <span className="v-chip">wallet metered</span>
            <span className="v-chip">audit logged</span>
            <span className="v-chip v-chip-ok">
              <MessageSquare className="h-3 w-3" />
              multi-turn
            </span>
          </div>
        </div>
      </header>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[320px_1fr_320px]">
        <aside className="space-y-4">
          <div className="v-card p-4">
            <div className="mb-3 font-mono text-[11px] uppercase tracking-[0.12em] text-muted">Vertical</div>
            <div className="grid grid-cols-2 gap-2">
              {VERTICALS.map((v) => (
                <button
                  key={v.value}
                  onClick={() => handleVerticalChange(v.value)}
                  className={cn(
                    "rounded-lg border px-3 py-2 text-left text-[12px] transition",
                    vertical === v.value
                      ? "border-brass/60 bg-brass/10 text-brass-2"
                      : "border-rule-2 bg-white/[0.02] text-bone-2 hover:bg-white/[0.04]",
                  )}
                  title={v.hint}
                >
                  <div className="font-semibold">{v.label}</div>
                  <div className="mt-0.5 text-[10px] text-muted">{v.hint}</div>
                </button>
              ))}
            </div>
          </div>

          <div className="v-card p-4">
            <div className="mb-3 flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.12em] text-muted">
              <Cpu className="h-3 w-3" /> Runtime model
            </div>
            {models.isLoading ? (
              <div className="flex items-center gap-2 font-mono text-[12px] text-muted">
                <Loader2 className="h-3.5 w-3.5 animate-spin" /> Loading live models...
              </div>
            ) : models.isError ? (
              <div className="rounded-md border border-crimson/30 bg-crimson/10 px-3 py-2 text-[12px] text-crimson">
                {responseDetail(models.error)}
              </div>
            ) : runnableModels.length ? (
              <div className="space-y-3">
                <select
                  className="v-input w-full"
                  value={selectedModel?.slug ?? ""}
                  disabled={running}
                  onChange={(e) => setSelectedModelSlug(e.target.value)}
                >
                  {runnableModels.map((model) => (
                    <option key={model.slug} value={model.slug}>
                      {model.name}
                    </option>
                  ))}
                </select>
                {selectedModel && (
                  <div className="space-y-1 font-mono text-[11px] text-muted">
                    <div>slug: <span className="text-bone">{selectedModel.slug}</span></div>
                    <div>provider: <span className="text-bone">{selectedModel.provider}</span></div>
                    <div>runtime: <span className="text-bone">{selectedModel.runtime_model_id}</span></div>
                  </div>
                )}
                <label className="block">
                  <div className="mb-1 font-mono text-[10px] uppercase tracking-wider text-muted">Max tokens</div>
                  <select
                    className="v-input w-full"
                    value={maxTokens}
                    disabled={running}
                    onChange={(e) => setMaxTokens(Number(e.target.value))}
                  >
                    {[16, 32, 64, 128].map((n) => (
                      <option key={n} value={n}>{n}</option>
                    ))}
                  </select>
                </label>
              </div>
            ) : (
              <div className="rounded-md border border-brass/30 bg-brass/10 px-3 py-2 text-[12px] text-brass-2">
                No connected models are enabled for this workspace.
              </div>
            )}
          </div>

          <div className="v-card p-4">
            <div className="mb-2 font-mono text-[11px] uppercase tracking-[0.12em] text-muted">
              Circuit breaker
            </div>
            <div className="rounded-lg border border-rule-2 bg-white/[0.02] p-3">
              <div className="text-[13px] font-medium text-bone">Automatic failover</div>
              <div className="mt-1 text-[11px] leading-relaxed text-muted">
                The backend tries the selected model path and applies the configured circuit breaker/fallback route
                if the runtime is unavailable.
              </div>
            </div>
          </div>

          <div className="v-card p-4">
            <div className="mb-2 flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.12em] text-muted">
              <Shield className="h-3 w-3" /> Governance active
            </div>
            <ul className="space-y-1.5 font-mono text-[11px]">
              {[
                "Bearer auth verification",
                "Tenant-scoped workspace model",
                "Wallet/reserve metering",
                "Circuit breaker fallback",
                "Tamper-evident audit write",
                "Request ledger entry",
              ].map((s) => (
                <li key={s} className="flex items-start gap-2 text-bone-2">
                  <span className="mt-0.5 text-moss">+</span>
                  {s}
                </li>
              ))}
            </ul>
          </div>
        </aside>

        <section className="space-y-4">
          {/* ----------------------------------------------------------------
              CONVERSATION THREAD — added 2026-05-04
              Renders the full multi-turn history above the prompt input.
              Each turn shows role badge, content, model used, and per-turn cost.
          ----------------------------------------------------------------- */}
          {conversation.length > 0 && (
            <div className="v-card p-0">
              <header className="flex items-center justify-between border-b border-rule px-4 py-2">
                <div className="flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.12em] text-muted">
                  <MessageSquare className="h-3 w-3" /> Conversation
                  <span className="v-chip">{conversation.length} turns</span>
                </div>
                <button
                  className="v-btn-ghost text-[11px] text-crimson"
                  onClick={clearConversation}
                  title="Clear conversation and start fresh"
                >
                  <Trash2 className="h-3.5 w-3.5" /> Clear
                </button>
              </header>
              <div
                ref={threadRef}
                className="max-h-[480px] overflow-y-auto space-y-0 divide-y divide-rule"
              >
                {conversation.map((turn) => (
                  <div
                    key={turn.id}
                    className={cn(
                      "px-4 py-3",
                      turn.role === "user"
                        ? "bg-white/[0.02]"
                        : "bg-moss/[0.04]",
                    )}
                  >
                    <div className="mb-1.5 flex items-center gap-2">
                      <span
                        className={cn(
                          "rounded-full px-2 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-wider",
                          turn.role === "user"
                            ? "bg-brass/10 text-brass-2"
                            : "bg-moss/10 text-moss",
                        )}
                      >
                        {turn.role}
                      </span>
                      {turn.role === "assistant" && turn.modelSlug && (
                        <span className="font-mono text-[10px] text-muted">{turn.modelSlug}</span>
                      )}
                      {turn.role === "assistant" && turn.cost_usd && (
                        <span className="ml-auto font-mono text-[10px] text-muted">{turn.cost_usd}</span>
                      )}
                      {turn.role === "assistant" && turn.tokens != null && (
                        <span className="font-mono text-[10px] text-muted">{turn.tokens} tok</span>
                      )}
                    </div>
                    <div className="whitespace-pre-wrap font-mono text-[13px] leading-relaxed text-bone">
                      {turn.content}
                    </div>
                  </div>
                ))}
                {running && (
                  <div className="flex items-center gap-2 px-4 py-3 font-mono text-[12px] text-muted">
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    Waiting for response...
                  </div>
                )}
              </div>
            </div>
          )}

          <div className="v-card p-4">
            <div className="mb-2 flex items-center justify-between">
              <label htmlFor="prompt" className="v-label mb-0">
                {conversation.length > 0 ? "Next message" : "Prompt"}
              </label>
              <span className="font-mono text-[10px] text-muted">{prompt.length} / 800</span>
            </div>
            <textarea
              id="prompt"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value.slice(0, 800))}
              rows={4}
              className="v-input min-h-[96px] resize-y font-mono text-[13px] leading-relaxed"
              placeholder={
                conversation.length > 0
                  ? "Continue the conversation..."
                  : "What would you like the governed control plane to answer?"
              }
              disabled={running}
              onKeyDown={(e) => {
                // Ctrl+Enter / Cmd+Enter sends the message
                if ((e.ctrlKey || e.metaKey) && e.key === "Enter" && canRun) {
                  e.preventDefault();
                  void run();
                }
              }}
            />
            <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
              <div className="flex flex-wrap gap-2">
                {!running ? (
                  <button className="v-btn-primary" onClick={run} disabled={!canRun}>
                    <Play className="h-4 w-4" />
                    {conversation.length > 0 ? "Send" : "Run workspace request"}
                  </button>
                ) : (
                  <button className="v-btn-ghost text-crimson" onClick={stop}>
                    <CircleStop className="h-4 w-4" /> Stop request
                  </button>
                )}
                {conversation.length > 0 && (
                  <button className="v-btn-ghost text-[12px]" onClick={clearConversation} title="Clear thread">
                    <Trash2 className="h-3.5 w-3.5" /> New conversation
                  </button>
                )}
                <button
                  className="v-btn-ghost"
                  onClick={exportAudit}
                  disabled={!events.length || running}
                  title="Download audit bundle"
                >
                  <Download className="h-4 w-4" /> Export audit
                </button>
                <button
                  className="v-btn-ghost"
                  onClick={saveAsPipeline}
                  disabled={!responseText || running || savingPipeline}
                  title="Save this run as a governed pipeline"
                >
                  <Save className="h-4 w-4" />
                  {savingPipeline ? "Saving..." : savedPipelineSlug ? "Saved" : "Save as Pipeline"}
                </button>
                <button
                  className="v-btn-ghost"
                  onClick={runPreflight}
                  disabled={!prompt.trim() || preflight.loading}
                  title="Predict cost, quality, and failure risk before running"
                >
                  <TrendingDown className="h-4 w-4" />
                  {preflight.loading ? "Predicting..." : "Pre-flight"}
                </button>
              </div>
              <div className="flex gap-2 font-mono text-[11px]">
                <span className="v-chip">
                  <Activity className="h-3 w-3" /> {eventCount} events
                </span>
                <span className="v-chip">
                  <Sparkles className="h-3 w-3" /> {tokenCount} tokens
                </span>
                {conversation.length > 0 && (
                  <span className="v-chip">
                    <MessageSquare className="h-3 w-3" /> {conversation.length} turns
                  </span>
                )}
              </div>
            </div>
            {error && (
              <div className="mt-3 flex items-start gap-2 rounded-md border border-crimson/30 bg-crimson/10 px-3 py-2 text-[12px] text-crimson">
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}
            {savedPipelineSlug && (
              <div className="mt-3 flex items-center gap-2 rounded-md border border-moss/30 bg-moss/5 px-3 py-2 text-[12px] text-moss">
                <CheckCircle2 className="h-3.5 w-3.5" />
                Saved as pipeline <span className="font-mono">{savedPipelineSlug}</span>.
                <a href="#/pipelines" className="ml-auto inline-flex items-center gap-1 text-moss underline-offset-4 hover:underline">
                  Open Pipelines <GitBranch className="h-3 w-3" />
                </a>
              </div>
            )}
            {(preflight.predicted_cost != null || preflight.error) && (
              <div className="mt-3 rounded-md border border-rule/70 bg-ink-2 p-3">
                <div className="mb-2 flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.12em] text-muted">
                  <Zap className="h-3 w-3 text-brass-2" /> Pre-flight intelligence
                </div>
                {preflight.error ? (
                  <div className="font-mono text-[12px] text-crimson">{preflight.error}</div>
                ) : (
                  <div className="grid grid-cols-3 gap-3 font-mono text-[12px]">
                    <PreflightCell
                      label="cost / run"
                      value={preflight.predicted_cost != null ? `$${preflight.predicted_cost.toFixed(4)}` : "-"}
                      sub={
                        preflight.cost_confidence_upper != null && preflight.predicted_cost != null
                          ? `+/-$${Math.abs(preflight.cost_confidence_upper - preflight.predicted_cost).toFixed(4)}`
                          : "server-side ml"
                      }
                      tone="ok"
                    />
                    <PreflightCell
                      label="quality"
                      value={
                        preflight.predicted_quality != null
                          ? `${(preflight.predicted_quality * 100).toFixed(0)}%`
                          : "-"
                      }
                      sub={preflight.predicted_quality != null ? "predicted" : "ml warming"}
                      tone={preflight.predicted_quality != null && preflight.predicted_quality > 0.8 ? "ok" : "warn"}
                    />
                    <PreflightCell
                      label="failure risk"
                      value={
                        preflight.failure_risk != null
                          ? `${(preflight.failure_risk * 100).toFixed(0)}%`
                          : "-"
                      }
                      sub={preflight.failure_risk != null ? "before run" : "ml warming"}
                      tone={preflight.failure_risk != null && preflight.failure_risk < 0.2 ? "ok" : "warn"}
                    />
                  </div>
                )}
                {preflight.alternatives?.length ? (
                  <div className="mt-2 flex flex-wrap gap-1.5 font-mono text-[10px]">
                    {preflight.alternatives.slice(0, 3).map((alt) => (
                      <span key={alt.provider} className="v-chip">
                        via {alt.provider} - ${parseFloat(alt.cost).toFixed(4)}
                        {alt.savings_percent > 0 && (
                          <span className="text-moss"> - save {alt.savings_percent.toFixed(0)}%</span>
                        )}
                      </span>
                    ))}
                  </div>
                ) : null}
              </div>
            )}
          </div>

          {/* Single-shot response panel — still shown for the latest turn only */}
          {responseText && (
            <div className="v-card p-0">
              <header className="flex items-center justify-between border-b border-rule px-4 py-2">
                <div className="font-mono text-[11px] uppercase tracking-[0.12em] text-muted">Latest response</div>
                {stats.provider && (
                  <span className="v-chip v-chip-brass font-mono">
                    {stats.provider} - {stats.model ?? "-"}
                  </span>
                )}
              </header>
              <div className="min-h-[180px] whitespace-pre-wrap p-4 font-mono text-[13px] leading-relaxed text-bone">
                {responseText}
              </div>
            </div>
          )}
          {!responseText && conversation.length === 0 && (
            <div className="v-card p-0">
              <header className="flex items-center justify-between border-b border-rule px-4 py-2">
                <div className="font-mono text-[11px] uppercase tracking-[0.12em] text-muted">Response</div>
              </header>
              <div className="min-h-[180px] whitespace-pre-wrap p-4 font-mono text-[13px] leading-relaxed text-bone">
                <span className="text-muted">
                  {running ? "Waiting for /api/v1/ai/complete..." : "Click Run workspace request to call the backend."}
                </span>
                {running && <span className="ml-0.5 inline-block h-4 w-2 animate-pulse bg-brass" />}
              </div>
            </div>
          )}
        </section>

        <aside className="space-y-4">
          <div className="v-card p-4">
            <div className="mb-3 flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.12em] text-muted">
              <Gauge className="h-3 w-3" /> Telemetry
            </div>
            <dl className="space-y-2.5 font-mono text-[12px]">
              <Stat label="request id" value={stats.request_id ?? "-"} mono />
              <Stat label="provider" value={stats.provider ?? "-"} />
              <Stat label="model" value={stats.model ?? "-"} />
              <Stat label="runtime" value={stats.runtime_model_id ?? "-"} mono />
              <Stat label="prompt tokens" value={stats.prompt_tokens?.toString() ?? "-"} />
              <Stat label="completion tokens" value={stats.completion_tokens?.toString() ?? "-"} />
              <Stat label="total tokens" value={stats.total_tokens?.toString() ?? "-"} />
              <Stat label="latency" value={stats.latency_ms ? `${stats.latency_ms} ms` : "-"} />
              <Stat label="credits" value={stats.tokens_deducted?.toString() ?? "-"} />
              <Stat label="wallet" value={stats.wallet_balance?.toString() ?? "-"} />
              <Stat label="audit hash" value={stats.audit_hash ? `${stats.audit_hash.slice(0, 12)}...` : "-"} mono />
              <Stat label="turns" value={conversation.length.toString()} />
            </dl>
          </div>

          <div className="v-card p-0">
            <header className="flex items-center justify-between border-b border-rule px-4 py-2">
              <div className="flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.12em] text-muted">
                <Zap className="h-3 w-3" /> Event log
              </div>
              <span className="v-chip font-mono">{eventCount}</span>
            </header>
            <div ref={feedRef} className="max-h-[520px] overflow-y-auto p-3 font-mono text-[11px]">
              {events.length === 0 ? (
                <div className="py-8 text-center text-muted">
                  {running ? "Waiting on backend..." : "No events yet."}
                </div>
              ) : (
                <ul className="space-y-1.5">
                  {events.map((e) => {
                    const meta = EVENT_META[e.event] ?? { label: e.event, color: "text-bone-2", icon: "-" };
                    return (
                      <li key={e.id} className="flex items-start gap-2">
                        <span className={cn("w-3 shrink-0 text-center", meta.color)}>{meta.icon}</span>
                        <span className={cn("shrink-0 font-semibold", meta.color)}>{meta.label}</span>
                        <span className="ml-auto truncate text-muted">{compactPayload(e.data)}</span>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function Stat({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <dt className="text-muted">{label}</dt>
      <dd className={cn("truncate text-right text-bone", mono && "font-mono")}>{value}</dd>
    </div>
  );
}

function PreflightCell({
  label,
  value,
  sub,
  tone,
}: {
  label: string;
  value: string;
  sub: string;
  tone: "ok" | "warn";
}) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-wider text-muted">{label}</div>
      <div className={cn("mt-0.5 text-base font-semibold", tone === "ok" ? "text-moss" : "text-brass-2")}>
        {value}
      </div>
      <div className="text-[10px] text-muted">{sub}</div>
    </div>
  );
}

function compactPayload(data: Record<string, unknown>): string {
  const keys = Object.keys(data);
  if (!keys.length) return "";
  const preferred = [
    "endpoint",
    "status",
    "provider",
    "model",
    "runtime_model_id",
    "output_tokens",
    "latency_ms",
    "credits_charged",
    "request_id",
    "message",
  ];
  for (const k of preferred) {
    if (k in data && data[k] != null) return `${k}=${String(data[k]).slice(0, 56)}`;
  }
  const first = keys[0]!;
  return `${first}=${String(data[first]).slice(0, 56)}`;
}
