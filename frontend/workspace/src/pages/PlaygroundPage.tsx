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

import type * as React from "react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  AlertTriangle,
  Box,
  ChevronDown,
  ChevronUp,
  CheckCircle2,
  CircleStop,
  Copy,
  Cpu,
  Download,
  Gauge,
  GitBranch,
  Loader2,
  MessageSquare,
  Pencil,
  Play,
  RotateCcw,
  Save,
  Shield,
  SlidersHorizontal,
  Sparkles,
  TerminalSquare,
  Trash2,
  TrendingDown,
  Zap,
} from "lucide-react";
import { api } from "@/lib/api";
import { cn } from "@/lib/cn";
import { ProofStrip, RunStatePanel, type FlowStatus } from "@/components/workspace/FlowPrimitives";
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

type Vertical =
  | "banking_fintech"
  | "healthcare_hospital"
  | "insurance"
  | "legal_compliance"
  | "government_public_sector"
  | "enterprise_operations"
  | "generic";
type ResponseFormat = "text" | "json" | "json-schema";
type SessionTag = "Standard" | "PHI" | "PII" | "HIPAA" | "PCI" | "SOC2";

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
  model_type?: string;
  context_window?: number;
  quantization?: string;
  p50_ms?: number;
  p95_ms?: number;
  input_cost_per_1k?: number;
  output_cost_per_1k?: number;
}

interface AICompleteResponse {
  response_text: string;
  model: string;
  bedrock_model_id: string;
  provider?: string;
  requested_provider?: string;
  requested_model?: string;
  fallback_triggered?: boolean;
  routing_reason?: string;
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
  reserve_debited?: number;
  billing_event_type?: "governed_run" | "compare_run" | "byok_governance_call" | "managed_governance_call";
  pricing_tier?: string;
  free_evaluation_remaining?: number | null;
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

interface CompareRunResult {
  modelSlug: string;
  modelName: string;
  provider: string;
  status: "idle" | "running" | "done" | "error";
  responseText?: string;
  error?: string;
  latencyMs?: number;
  outputTokens?: number;
  costUsd?: string;
  requestId?: string;
  auditHash?: string;
}

interface PlaygroundScenario {
  scenario_id: string;
  title: string;
  prompt: string;
  suggested_workflow: string[];
  suggested_models_tools: string[];
  evidence_emphasis: string[];
}

interface PlaygroundProfile {
  workspaceId: string;
  tenantId: string;
  industry: Vertical;
  playground_profile: Vertical;
  profileName: string;
  risk_tier: string;
  policy_pack: string;
  suggested_demo_prompts: string[];
  sample_workflows: string[];
  policy_checks: string[];
  evidence_requirements: string[];
  gpc_templates: string[];
  restricted_actions: string[];
  recommended_model_tool_constraints: string[];
  default_demo_scenarios: PlaygroundScenario[];
  default_blocking_rules: string[];
  regulated_defaults: {
    external_fallback_default: boolean;
    human_review_required_for_high_risk: boolean;
    evidence_capture_required: boolean;
    audit_replay_required: boolean;
    sensitive_data_warning_visible: boolean;
    founder_review_required_for_regulated_claims: boolean;
  };
}

interface GpcHandoff {
  workspaceId: string;
  tenantId: string;
  industry: Vertical;
  playground_profile: Vertical;
  scenario_id: string;
  scenario_title: string;
  user_input: string;
  risk_tier: string;
  policy_pack: string;
  evidence_requirements: string[];
  blocking_rules: string[];
  suggested_workflow: string[];
  suggested_models_tools: string[];
  handoff_status: "prepared";
  claim_level: "draft";
}

interface CommercialArtifactDraft {
  id: string;
  artifact_type: string;
  title: string;
  founderReviewStatus: string;
  archiveRecordId?: string | null;
  outcome: string;
  artifact: Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const VERTICALS: { value: Vertical; label: string; hint: string }[] = [
  { value: "banking_fintech", label: "Banking / Fintech", hint: "Approval-heavy financial operations" },
  { value: "healthcare_hospital", label: "Healthcare / Hospital", hint: "PHI-aware clinical workflows" },
  { value: "insurance", label: "Insurance", hint: "Claims and fraud support workflows" },
  { value: "legal_compliance", label: "Legal / Compliance", hint: "Source-backed review and approvals" },
  { value: "government_public_sector", label: "Government / Public Sector", hint: "Sensitive records and routing controls" },
  { value: "enterprise_operations", label: "Enterprise Operations", hint: "Support, policy, and incident workflows" },
  { value: "generic", label: "Generic", hint: "Cross-industry governed workflow design" },
];

const SAMPLE_PROMPTS: Record<Vertical, string> = {
  banking_fintech: "We want AI to triage suspicious transactions, explain risk basis, and route urgent cases for approval.",
  healthcare_hospital: "We want AI to summarize patient intake while redacting PHI and requiring human review.",
  insurance: "We want AI to triage claims, flag fraud risk, and support adjusters without making final claim decisions.",
  legal_compliance: "We want AI to review contract clauses, surface risk, and route sensitive matters for human approval.",
  government_public_sector: "We want AI to triage public-sector intake, screen record sensitivity, and preserve replay evidence.",
  enterprise_operations: "We want AI to triage support tickets, detect urgent issues, and route them with evidence and cost controls.",
  generic: "We want to use AI to triage support tickets, summarize the case, route it to the right team, and keep an audit trail.",
};

const EVENT_META: Record<string, { label: string; color: string; icon: string }> = {
  workspace_request: { label: "Workspace request", color: "text-bone", icon: "*" },
  auth_check: { label: "Auth check", color: "text-electric", icon: ">" },
  wallet_check: { label: "Reserve check", color: "text-electric", icon: "$" },
  provider_selected: { label: "Provider chosen", color: "text-brass-2", icon: ">" },
  circuit_breaker_triggered: { label: "Circuit breaker", color: "text-brass-2", icon: "!" },
  response_complete: { label: "Response complete", color: "text-moss", icon: "+" },
  audit_written: { label: "Audit written", color: "text-moss", icon: "+" },
  cost_recorded: { label: "Cost recorded", color: "text-moss", icon: "+" },
  done: { label: "Done", color: "text-moss", icon: "*" },
  error: { label: "Error", color: "text-crimson", icon: "!" },
};

const DEFAULT_MAX_TOKENS = 512;
const DEFAULT_TEMPERATURE = 0.7;
const DEFAULT_TOP_P = 0.95;
const DEFAULT_TOP_K = 40;
const DEFAULT_SEED = 42;
const REQUEST_TIMEOUT_MS = 90_000;
const COMPARE_REQUEST_TIMEOUT_MS = 120_000;
const PREFLIGHT_TIMEOUT_MS = 25_000;
const MAX_CONVERSATION_TURNS = 20; // safety cap — keeps context window sane
const PLAYGROUND_STORAGE_KEY = "veklom.workspace.playground.v3";
const SESSION_TAGS: SessionTag[] = ["Standard", "PHI", "PII", "HIPAA", "PCI", "SOC2"];

const QUICK_PROMPTS: { label: string; prompt: string; tag?: SessionTag; vertical?: Vertical }[] = [
  {
    label: "PHI-safe summarization",
    tag: "PHI",
    vertical: "healthcare_hospital",
    prompt:
      "Summarize this clinical intake note for an operations lead. Preserve clinical intent, redact PHI/PII, include risk flags, and explain which Veklom governance controls fired.",
  },
  {
    label: "Banking risk triage",
    vertical: "banking_fintech",
    prompt:
      "Triage suspicious transactions, explain the risk basis, route urgent cases to the right team, and create replayable evidence.",
  },
  {
    label: "Policy-bound rewrite",
    tag: "SOC2",
    vertical: "legal_compliance",
    prompt:
      "Rewrite this customer-facing AI response so it follows outbound.public.v3, avoids unsupported claims, and includes an audit-ready explanation of the policy decision.",
  },
  {
    label: "Support workflow planning",
    vertical: "enterprise_operations",
    prompt:
      "Turn our support ticket triage idea into a governed workflow with approvals, evidence requirements, and cost controls.",
  },
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function normalizeModel(raw: unknown): WorkspaceModel {
  const row = raw as Record<string, unknown>;
  const slug = String(row.slug ?? row.model_slug ?? "");
  const runtime = String(row.bedrock_model_id ?? row.runtime_model_id ?? row.model ?? slug);
  const numberOrUndefined = (value: unknown): number | undefined => {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : undefined;
  };
  return {
    slug,
    name: String(row.name ?? row.display_name ?? row.model_slug ?? slug),
    provider: String(row.provider ?? "local"),
    runtime_model_id: runtime,
    enabled: row.enabled !== false,
    connected: row.connected !== false,
    model_type: String(row.model_type ?? row.mode ?? "chat"),
    context_window: numberOrUndefined(row.context_window ?? row.context_window_tokens),
    quantization: String(row.quantization ?? row.quant ?? "FP16"),
    p50_ms: numberOrUndefined(row.p50_ms ?? row.latency_p50_ms),
    p95_ms: numberOrUndefined(row.p95_ms ?? row.latency_p95_ms),
    input_cost_per_1k: numberOrUndefined(row.input_cost_per_1k ?? row.input_price_per_1k),
    output_cost_per_1k: numberOrUndefined(row.output_cost_per_1k ?? row.output_price_per_1k),
  };
}

async function fetchWorkspaceModels(): Promise<WorkspaceModel[]> {
  const resp = await api.get<{ models?: unknown[]; items?: unknown[] } | unknown[]>("/workspace/models");
  const body = resp.data;
  const raw = Array.isArray(body) ? body : body.models ?? body.items ?? [];
  return raw.map(normalizeModel).filter((model) => Boolean(model.slug));
}

async function fetchWorkspacePlaygroundProfile(): Promise<PlaygroundProfile> {
  const resp = await api.get<PlaygroundProfile>("/workspace/playground/profile");
  return resp.data;
}

async function recordFeatureUse(feature: string, metadata: Record<string, unknown> = {}) {
  await api.post("/telemetry/events", {
    events: [
      {
        event_type: "feature_use",
        surface: "playground",
        route: "/playground",
        feature,
        metadata,
      },
    ],
  });
}

function normalizeStoredVertical(value: unknown): Vertical {
  switch (value) {
    case "default":
      return "generic";
    case "medical":
      return "healthcare_hospital";
    case "finance":
      return "banking_fintech";
    case "legal":
      return "legal_compliance";
    case "agency":
      return "enterprise_operations";
    case "infrastructure":
      return "government_public_sector";
    case "banking_fintech":
    case "healthcare_hospital":
    case "insurance":
    case "legal_compliance":
    case "government_public_sector":
    case "enterprise_operations":
    case "generic":
      return value;
    default:
      return "generic";
  }
}

function readStoredPlaygroundState() {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(PLAYGROUND_STORAGE_KEY);
    return raw
      ? (JSON.parse(raw) as {
          prompt?: string;
          vertical?: string;
          selectedModelSlug?: string;
          maxTokens?: number;
          conversation?: ConversationTurn[];
          systemPrompt?: string;
          temperature?: number;
          topP?: number;
          topK?: number;
          frequencyPenalty?: number;
          presencePenalty?: number;
          streamEnabled?: boolean;
          responseFormat?: ResponseFormat;
          seed?: number;
          sessionTag?: SessionTag;
          lockToOnPrem?: boolean;
          autoRedact?: boolean;
          auditExportPinned?: boolean;
          showSystemPrompt?: boolean;
        })
      : null;
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function PlaygroundPage() {
  const stored = useMemo(() => readStoredPlaygroundState(), []);
  const storedVertical = normalizeStoredVertical(stored?.vertical);
  const [vertical, setVertical] = useState<Vertical>(storedVertical);
  const [prompt, setPrompt] = useState(stored?.prompt ?? SAMPLE_PROMPTS[storedVertical]);
  const [maxTokens, setMaxTokens] = useState(stored?.maxTokens ?? DEFAULT_MAX_TOKENS);
  const [selectedModelSlug, setSelectedModelSlug] = useState(stored?.selectedModelSlug ?? "");
  const [systemPrompt, setSystemPrompt] = useState(stored?.systemPrompt ?? "");
  const [temperature, setTemperature] = useState(stored?.temperature ?? DEFAULT_TEMPERATURE);
  const [topP, setTopP] = useState(stored?.topP ?? DEFAULT_TOP_P);
  const [topK, setTopK] = useState(stored?.topK ?? DEFAULT_TOP_K);
  const [frequencyPenalty, setFrequencyPenalty] = useState(stored?.frequencyPenalty ?? 0);
  const [presencePenalty, setPresencePenalty] = useState(stored?.presencePenalty ?? 0);
  const [streamEnabled, setStreamEnabled] = useState(stored?.streamEnabled ?? false);
  const [responseFormat, setResponseFormat] = useState<ResponseFormat>(stored?.responseFormat ?? "text");
  const [seed, setSeed] = useState(stored?.seed ?? DEFAULT_SEED);
  const [sessionTag, setSessionTag] = useState<SessionTag>(
    stored?.sessionTag && SESSION_TAGS.includes(stored.sessionTag) ? stored.sessionTag : "Standard",
  );
  const [showSystemPrompt, setShowSystemPrompt] = useState(stored?.showSystemPrompt ?? false);
  const [mode, setMode] = useState<"chat" | "completion">("chat");
  const [compareOpen, setCompareOpen] = useState(false);
  const [toolMenuOpen, setToolMenuOpen] = useState(false);
  const [autoRedact, setAutoRedact] = useState(stored?.autoRedact ?? true);
  const [auditExportPinned, setAuditExportPinned] = useState(stored?.auditExportPinned ?? true);
  const [lockToOnPrem, setLockToOnPrem] = useState(stored?.lockToOnPrem ?? false);
  const [running, setRunning] = useState(false);
  const [events, setEvents] = useState<PipelineEvent[]>([]);
  const [responseText, setResponseText] = useState("");
  const [secondaryModelSlug, setSecondaryModelSlug] = useState("");
  const [comparePrompt, setComparePrompt] = useState("");
  const [compareResults, setCompareResults] = useState<Record<string, CompareRunResult>>({});
  const [selectedScenarioId, setSelectedScenarioId] = useState<string>("");
  const [handoffPreview, setHandoffPreview] = useState<GpcHandoff | null>(null);
  const [artifactDraft, setArtifactDraft] = useState<CommercialArtifactDraft | null>(null);
  const [compileSubmitting, setCompileSubmitting] = useState(false);
  const [artifactSubmitting, setArtifactSubmitting] = useState(false);
  const [markingEvaluation, setMarkingEvaluation] = useState(false);

  // -------------------------------------------------------------------------
  // Multi-turn conversation history (added 2026-05-04 — see note at top)
  // -------------------------------------------------------------------------
  const [conversation, setConversation] = useState<ConversationTurn[]>(stored?.conversation ?? []);
  const threadRef = useRef<HTMLDivElement>(null);

  const clearConversation = useCallback(() => {
    setConversation([]);
    setResponseText("");
    setEvents([]);
    setComparePrompt("");
    setCompareResults({});
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
    reserve_debited?: number;
    billing_event_type?: string;
    pricing_tier?: string;
    free_evaluation_remaining?: number | null;
    cost_usd?: string;
    requested_provider?: string;
    requested_model?: string;
    fallback_triggered?: boolean;
    routing_reason?: string;
  }>({});
  const [error, setError] = useState<string | null>(null);
  const [preflight, setPreflight] = useState<PreflightState>({});
  const [savedPipelineSlug, setSavedPipelineSlug] = useState<string | null>(null);
  const [savingPipeline, setSavingPipeline] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const feedRef = useRef<HTMLDivElement>(null);
  const protectedSession = sessionTag === "PHI" || sessionTag === "HIPAA";
  const effectiveLockToOnPrem = protectedSession || lockToOnPrem;

  const resetParameters = () => {
    setTemperature(DEFAULT_TEMPERATURE);
    setTopP(DEFAULT_TOP_P);
    setTopK(DEFAULT_TOP_K);
    setMaxTokens(DEFAULT_MAX_TOKENS);
    setFrequencyPenalty(0);
    setPresencePenalty(0);
    setStreamEnabled(false);
    setResponseFormat("text");
    setSeed(DEFAULT_SEED);
  };

  const handleSessionTagChange = (tag: SessionTag) => {
    setSessionTag(tag);
    if (tag === "PHI" || tag === "HIPAA") {
      setAutoRedact(true);
      setAuditExportPinned(true);
      setLockToOnPrem(true);
    }
  };

  const models = useQuery({
    queryKey: ["playground-models"],
    queryFn: fetchWorkspaceModels,
    refetchInterval: 30_000,
  });
  const profileQuery = useQuery({
    queryKey: ["workspace-playground-profile"],
    queryFn: fetchWorkspacePlaygroundProfile,
    staleTime: 60_000,
  });
  const playgroundProfile = profileQuery.data;
  const activeScenarios = playgroundProfile?.default_demo_scenarios ?? [];

  useEffect(() => {
    if (!playgroundProfile) return;
    setVertical(playgroundProfile.playground_profile);
    const firstScenario = playgroundProfile.default_demo_scenarios[0];
    setSelectedScenarioId((current) => current || firstScenario?.scenario_id || "");
    if (!stored?.prompt && firstScenario?.prompt) {
      setPrompt(firstScenario.prompt);
    }
  }, [playgroundProfile, stored?.prompt]);

  const runnableModels = useMemo(
    () =>
      (models.data ?? [])
        .filter((model) => model.enabled && model.connected && model.provider !== "groq")
        .sort((a, b) => {
          const score = (model: WorkspaceModel) => model.provider === "ollama" ? 0 : 1;
          return score(a) - score(b);
        }),
    [models.data],
  );

  const quarantinedGroqModels = useMemo(
    () => (models.data ?? []).filter((model) => model.enabled && model.connected && model.provider === "groq"),
    [models.data],
  );

  const preferredModel = useMemo(() => {
    if (!runnableModels.length) return undefined;
    if (effectiveLockToOnPrem) {
      return runnableModels.find((model) => model.provider === "ollama") ?? runnableModels[0];
    }
    return runnableModels.find((model) => model.provider === "ollama") ?? runnableModels[0];
  }, [effectiveLockToOnPrem, runnableModels]);

  useEffect(() => {
    const current = runnableModels.find((model) => model.slug === selectedModelSlug);
    if (!preferredModel) return;
    if (!current || (effectiveLockToOnPrem && current.provider !== "ollama")) {
      setSelectedModelSlug(preferredModel.slug);
    }
  }, [effectiveLockToOnPrem, preferredModel, runnableModels, selectedModelSlug]);

  useEffect(() => {
    const current = runnableModels.find((model) => model.slug === secondaryModelSlug);
    const fallback = runnableModels.find((model) => model.slug !== selectedModelSlug);
    if (!fallback) {
      if (secondaryModelSlug) setSecondaryModelSlug("");
      return;
    }
    if (!current || current.slug === selectedModelSlug || (effectiveLockToOnPrem && current.provider !== "ollama")) {
      setSecondaryModelSlug(fallback.slug);
    }
  }, [effectiveLockToOnPrem, runnableModels, secondaryModelSlug, selectedModelSlug]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    window.localStorage.setItem(
      PLAYGROUND_STORAGE_KEY,
      JSON.stringify({
        vertical,
        prompt,
        maxTokens,
        selectedModelSlug,
        conversation,
        systemPrompt,
        temperature,
        topP,
        topK,
        frequencyPenalty,
        presencePenalty,
        streamEnabled,
        responseFormat,
        seed,
        sessionTag,
        lockToOnPrem,
        autoRedact,
        auditExportPinned,
        showSystemPrompt,
      }),
    );
  }, [
    auditExportPinned,
    autoRedact,
    conversation,
    frequencyPenalty,
    lockToOnPrem,
    maxTokens,
    presencePenalty,
    prompt,
    responseFormat,
    seed,
    selectedModelSlug,
    sessionTag,
    showSystemPrompt,
    streamEnabled,
    systemPrompt,
    temperature,
    topK,
    topP,
    vertical,
  ]);

  const selectedModel = useMemo(
    () => runnableModels.find((model) => model.slug === selectedModelSlug) ?? preferredModel ?? runnableModels[0],
    [preferredModel, runnableModels, selectedModelSlug],
  );
  const secondaryCompareModel = useMemo(
    () => runnableModels.find((model) => model.slug === secondaryModelSlug && model.slug !== selectedModel?.slug)
      ?? runnableModels.find((model) => model.slug !== selectedModel?.slug),
    [runnableModels, secondaryModelSlug, selectedModel?.slug],
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

  const copyTurn = useCallback(async (content: string) => {
    if (typeof navigator === "undefined" || !navigator.clipboard) return;
    await navigator.clipboard.writeText(content);
  }, []);

  const editAndResendTurn = useCallback((content: string) => {
    setPrompt(content);
  }, []);

  const regenerateFromTurn = useCallback((turnId: string) => {
    const idx = conversation.findIndex((turn) => turn.id === turnId);
    if (idx <= 0) return;
    const priorUserTurn = [...conversation.slice(0, idx)].reverse().find((turn) => turn.role === "user");
    if (!priorUserTurn) return;
    setConversation(conversation.slice(0, idx));
    setPrompt(priorUserTurn.content);
  }, [conversation]);

  const selectedScenario = useMemo(
    () => activeScenarios.find((scenario) => scenario.scenario_id === selectedScenarioId) ?? activeScenarios[0],
    [activeScenarios, selectedScenarioId],
  );

  const handleVerticalChange = (v: Vertical) => {
    setVertical(v);
    if (prompt === SAMPLE_PROMPTS[vertical]) setPrompt(SAMPLE_PROMPTS[v]);
  };

  const applyScenario = useCallback(async (scenario: PlaygroundScenario) => {
    setSelectedScenarioId(scenario.scenario_id);
    setPrompt(scenario.prompt);
    setHandoffPreview(null);
    setArtifactDraft(null);
    try {
      await recordFeatureUse("vertical_demo_generated", {
        scenario_id: scenario.scenario_id,
        industry: playgroundProfile?.industry ?? vertical,
        playground_profile: playgroundProfile?.playground_profile ?? vertical,
        risk_tier: playgroundProfile?.risk_tier ?? "generic",
      });
    } catch {
      // best-effort telemetry only
    }
  }, [playgroundProfile, vertical]);

  const compileWithGpc = useCallback(async () => {
    if (!selectedScenario) return;
    setCompileSubmitting(true);
    setArtifactDraft(null);
    try {
      const resp = await api.post<GpcHandoff>("/workspace/playground/handoff", {
        scenario_id: selectedScenario.scenario_id,
        scenario_title: selectedScenario.title,
        user_input: prompt,
      });
      setHandoffPreview(resp.data);
    } catch (err) {
      setError(responseDetail(err));
    } finally {
      setCompileSubmitting(false);
    }
  }, [prompt, selectedScenario]);

  const createFounderReviewArtifact = useCallback(async () => {
    if (!handoffPreview || !selectedScenario) return;
    setArtifactSubmitting(true);
    try {
      const resp = await api.post<CommercialArtifactDraft>("/workspace/commercial/community-awareness-run", {
        title: `${selectedScenario.title} founder-review draft`,
        handoff: handoffPreview,
        community_or_source: `${handoffPreview.industry} / vertical playground`,
        audience_type: "ai_platform_ops_compliance",
        pain_signal: "AI demo works but team lacks governed deployment path.",
        why_veklom_fits: "Veklom turns the tested workflow into a governed tenant-scoped plan with evidence and private runtime options.",
        suggested_reply_or_post: `Teams in ${handoffPreview.industry.replace(/_/g, " ")} usually stall after the demo. The missing piece is a governed workflow with approvals, evidence, policy checks, and a private runtime path.`,
        cta: "Try the GPC demo",
      });
      setArtifactDraft(resp.data);
    } catch (err) {
      setError(responseDetail(err));
    } finally {
      setArtifactSubmitting(false);
    }
  }, [handoffPreview, selectedScenario]);

  const founderReviewArtifact = useCallback(async (status: "approved_by_founder" | "blocked_by_founder") => {
    if (!artifactDraft) return;
    try {
      const resp = await api.patch(`/workspace/commercial/artifacts/${artifactDraft.id}`, {
        founder_review_status: status,
        outcome: status === "approved_by_founder" ? "founder_review_complete" : "blocked",
      });
      setArtifactDraft((current) => current ? { ...current, founderReviewStatus: resp.data.founderReviewStatus, outcome: resp.data.outcome } : current);
    } catch (err) {
      setError(responseDetail(err));
    }
  }, [artifactDraft]);

  const markEvaluationConversation = useCallback(async () => {
    if (!handoffPreview || !selectedScenario) return;
    setMarkingEvaluation(true);
    try {
      await recordFeatureUse("evaluation_conversation_influenced_by_vertical_demo", {
        scenario_id: selectedScenario.scenario_id,
        industry: handoffPreview.industry,
        playground_profile: handoffPreview.playground_profile,
        risk_tier: handoffPreview.risk_tier,
      });
    } finally {
      setMarkingEvaluation(false);
    }
  }, [handoffPreview, selectedScenario]);

  const stop = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setRunning(false);
  }, []);

  const buildConversationMessages = useCallback((userContent: string) => (
    conversation
      .slice(-MAX_CONVERSATION_TURNS)
      .map((turn) => ({ role: turn.role, content: turn.content }))
      .concat([{ role: "user" as const, content: userContent }])
  ), [conversation]);

  const buildGovernanceSystemPrompt = useCallback(() => (
    [
      autoRedact ? "Redact or refuse disclosure of PII, PHI, secrets, access tokens, and regulated identifiers unless the user explicitly asks for a safe placeholder format." : "",
      `Session tag: ${sessionTag}. Apply Veklom policy controls before provider execution.`,
      protectedSession ? "PHI/HIPAA session: keep execution on Hetzner/on-prem runtime only, auto-redact PHI/PII, and keep signed audit export pinned on." : "",
      responseFormat !== "text" ? `Response format requested: ${responseFormat}.` : "",
      vertical !== "generic" ? `Session vertical: ${vertical}. Apply the matching Veklom governance posture before answering.` : "",
      playgroundProfile?.policy_pack ? `Tenant policy pack: ${playgroundProfile.policy_pack}.` : "",
      systemPrompt.trim(),
    ].filter(Boolean).join("\n\n")
  ), [autoRedact, playgroundProfile?.policy_pack, protectedSession, responseFormat, sessionTag, systemPrompt, vertical]);

  const executeCompletion = useCallback(async (
    model: WorkspaceModel,
    userContent: string,
    billingEventType: "governed_run" | "compare_run",
    signal: AbortSignal,
    timeoutMs = REQUEST_TIMEOUT_MS,
  ) => {
    const startedAt = performance.now();
    const resp = await api.post<AICompleteResponse>(
      "/ai/complete",
      {
        model: model.slug,
        prompt: userContent.slice(0, 8000),
        messages: buildConversationMessages(userContent),
        system_prompt: buildGovernanceSystemPrompt() || undefined,
        temperature,
        top_p: topP,
        top_k: topK,
        frequency_penalty: frequencyPenalty,
        presence_penalty: presencePenalty,
        stream: streamEnabled,
        response_format: responseFormat,
        seed,
        session_tag: sessionTag,
        lock_to_on_prem: effectiveLockToOnPrem,
        auto_redact: autoRedact,
        sign_audit_on_export: auditExportPinned,
        billing_event_type: billingEventType,
        max_tokens: maxTokens,
      },
      { signal, timeout: timeoutMs },
    );
    const elapsedMs = Math.round(performance.now() - startedAt);
    const payload = resp.data;
    const provider = payload.provider ?? model.provider;
    const requestedProvider = payload.requested_provider ?? model.provider;
    const fallbackTriggered = payload.fallback_triggered ?? provider !== model.provider;
    const latency = payload.latency_ms ?? elapsedMs;
    return {
      payload,
      provider,
      requestedProvider,
      fallbackTriggered,
      latency,
      stats: {
        provider,
        model: payload.model,
        runtime_model_id: payload.bedrock_model_id,
        prompt_tokens: payload.prompt_tokens,
        completion_tokens: payload.output_tokens,
        total_tokens: payload.total_tokens,
        latency_ms: latency,
        request_id: payload.request_id,
        audit_hash: payload.audit_hash,
        tokens_deducted: payload.reserve_debited ?? payload.tokens_deducted,
        wallet_balance: payload.wallet_balance,
        reserve_debited: payload.reserve_debited ?? payload.tokens_deducted,
        billing_event_type: payload.billing_event_type ?? billingEventType,
        pricing_tier: payload.pricing_tier,
        free_evaluation_remaining: payload.free_evaluation_remaining,
        cost_usd: payload.cost_usd,
        requested_provider: requestedProvider,
        requested_model: payload.requested_model ?? model.slug,
        fallback_triggered: fallbackTriggered,
        routing_reason: payload.routing_reason ?? (fallbackTriggered ? "circuit_breaker_failover" : "primary_runtime"),
      },
    };
  }, [
    auditExportPinned,
    autoRedact,
    buildConversationMessages,
    buildGovernanceSystemPrompt,
    effectiveLockToOnPrem,
    frequencyPenalty,
    maxTokens,
    presencePenalty,
    responseFormat,
    seed,
    sessionTag,
    streamEnabled,
    temperature,
    topK,
    topP,
  ]);

  const run = useCallback(async () => {
    if (running || !selectedModel || !prompt.trim()) return;

    const controller = new AbortController();
    abortRef.current = controller;
    const userContent = prompt.trim();
    setEvents([]);
    setResponseText("");
    setStats({});
    setError(null);
    setSavedPipelineSlug(null);
    setRunning(true);

    try {
      if (compareOpen) {
        const compareModels = [selectedModel, secondaryCompareModel].filter(
          (model, index, items): model is WorkspaceModel => Boolean(model) && items.findIndex((item) => item?.slug === model?.slug) === index,
        );
        if (compareModels.length < 2) {
          throw new Error("Compare mode requires two connected models.");
        }

        setComparePrompt(userContent);
        setCompareResults(
          Object.fromEntries(
            compareModels.map((model) => [
              model.slug,
              {
                modelSlug: model.slug,
                modelName: model.name,
                provider: model.provider,
                status: "running" as const,
              },
            ]),
          ),
        );

        appendEvent("auth_check", { status: "bearer token attached", tenant_scope: "current workspace", compare: true });
        for (const model of compareModels) {
          appendEvent("workspace_request", {
            endpoint: "/api/v1/ai/complete",
            model: model.slug,
            max_tokens: maxTokens,
            temperature,
            top_p: topP,
            top_k: topK,
            response_format: responseFormat,
            session_tag: sessionTag,
            lock_to_on_prem: effectiveLockToOnPrem,
            billing_event_type: "compare_run",
          });
          appendEvent("wallet_check", { status: "reserve requested", model: model.slug, billing_event_type: "compare_run" });
          appendEvent("provider_selected", {
            provider: model.provider,
            model: model.slug,
            runtime_model_id: model.runtime_model_id,
          });
        }

        const settled = await Promise.allSettled(
          compareModels.map(async (model) => {
            try {
              return {
                model,
                result: await executeCompletion(
                  model,
                  userContent,
                  "compare_run",
                  controller.signal,
                  COMPARE_REQUEST_TIMEOUT_MS,
                ),
              };
            } catch (error) {
              throw { model, error };
            }
          }),
        );

        let primaryResultText = "";
        let primaryStats: typeof stats | null = null;
        let firstSuccessfulStats: typeof stats | null = null;

        for (const outcome of settled) {
          if (outcome.status === "fulfilled") {
            const { model, result } = outcome.value;
            const { payload, provider, requestedProvider, fallbackTriggered, latency } = result;
            setCompareResults((prev) => ({
              ...prev,
              [model.slug]: {
                modelSlug: model.slug,
                modelName: model.name,
                provider,
                status: "done",
                responseText: payload.response_text,
                latencyMs: latency,
                outputTokens: payload.output_tokens,
                costUsd: payload.cost_usd,
                requestId: payload.request_id,
                auditHash: payload.audit_hash,
              },
            }));

            if (!firstSuccessfulStats) firstSuccessfulStats = result.stats;
            if (model.slug === selectedModel.slug) {
              primaryResultText = payload.response_text;
              primaryStats = result.stats;
            }

            if (fallbackTriggered) {
              appendEvent("circuit_breaker_triggered", {
                intended_provider: requestedProvider,
                intended_model: payload.requested_model ?? model.slug,
                actual_provider: provider,
                actual_model: payload.model,
                reason: payload.routing_reason ?? "circuit_breaker_failover",
              });
            }

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
              reserve_debit: payload.reserve_debited ?? payload.tokens_deducted,
              billing_event_type: payload.billing_event_type ?? "compare_run",
              pricing_tier: payload.pricing_tier,
              free_evaluation_remaining: payload.free_evaluation_remaining,
              wallet_balance: payload.wallet_balance,
              cost_usd: payload.cost_usd,
            });
            appendEvent("done", {
              request_id: payload.request_id,
              total_latency_ms: latency,
              model: model.slug,
            });
          } else {
            const err = outcome.reason as { model?: WorkspaceModel; error?: unknown };
            const model = err?.model;
            const rawError = err?.error ?? err;
            const aborted = (rawError as { code?: string })?.code === "ERR_CANCELED";
            const message = aborted ? "Request cancelled before completion." : responseDetail(rawError);
            if (model) {
              setCompareResults((prev) => ({
                ...prev,
                [model.slug]: {
                  modelSlug: model.slug,
                  modelName: model.name,
                  provider: model.provider,
                  status: "error",
                  error: message,
                },
              }));
            }
            appendEvent("error", {
              endpoint: "/api/v1/ai/complete",
              model: model?.slug,
              message,
            });
          }
        }

        setResponseText(primaryResultText);
        setStats(primaryStats ?? firstSuccessfulStats ?? {});
        if ((primaryStats ?? firstSuccessfulStats) == null) {
          setError("Compare run failed for both models.");
        } else {
          setPrompt("");
        }
        return;
      }

      appendTurn({ role: "user", content: userContent });
      appendEvent("workspace_request", {
        endpoint: "/api/v1/ai/complete",
        model: selectedModel.slug,
        max_tokens: maxTokens,
        temperature,
        top_p: topP,
        top_k: topK,
        response_format: responseFormat,
        session_tag: sessionTag,
        lock_to_on_prem: effectiveLockToOnPrem,
      });
      appendEvent("auth_check", { status: "bearer token attached", tenant_scope: "current workspace" });
      appendEvent("wallet_check", { status: "reserve requested", model: selectedModel.slug });
      appendEvent("provider_selected", {
        provider: selectedModel.provider,
        model: selectedModel.slug,
        runtime_model_id: selectedModel.runtime_model_id,
      });

      const result = await executeCompletion(selectedModel, userContent, "governed_run", controller.signal);
      const { payload, provider, requestedProvider, fallbackTriggered, latency } = result;

      setResponseText(payload.response_text);
      setStats(result.stats);

      appendTurn({
        role: "assistant",
        content: payload.response_text,
        modelSlug: selectedModel.slug,
        provider,
        cost_usd: payload.cost_usd,
        tokens: payload.output_tokens,
        latency_ms: latency,
      });
      setPrompt("");

      if (fallbackTriggered) {
        appendEvent("circuit_breaker_triggered", {
          intended_provider: requestedProvider,
          intended_model: payload.requested_model ?? selectedModel.slug,
          actual_provider: provider,
          actual_model: payload.model,
          reason: payload.routing_reason ?? "circuit_breaker_failover",
        });
      }

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
        reserve_debit: payload.reserve_debited ?? payload.tokens_deducted,
        billing_event_type: payload.billing_event_type ?? "governed_run",
        pricing_tier: payload.pricing_tier,
        free_evaluation_remaining: payload.free_evaluation_remaining,
        wallet_balance: payload.wallet_balance,
        cost_usd: payload.cost_usd,
      });
      appendEvent("done", {
        request_id: payload.request_id,
        total_latency_ms: latency,
      });
    } catch (err) {
      const aborted = (err as { code?: string })?.code === "ERR_CANCELED";
      const message = aborted
        ? "Request cancelled before completion."
        : err instanceof Error
          ? err.message
          : responseDetail(err);
      setError(message);
      appendEvent("error", {
        endpoint: "/api/v1/ai/complete",
        message,
      });
    } finally {
      abortRef.current = null;
      setRunning(false);
    }
  }, [
    appendEvent,
    appendTurn,
    auditExportPinned,
    maxTokens,
    prompt,
    running,
    compareOpen,
    secondaryCompareModel,
    executeCompletion,
    appendTurn,
    effectiveLockToOnPrem,
    frequencyPenalty,
    maxTokens,
    presencePenalty,
    responseFormat,
    selectedModel,
    sessionTag,
    temperature,
    topK,
    topP,
  ]);

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
      }, { timeout: PREFLIGHT_TIMEOUT_MS });
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
        const qResp = await api.post("/autonomous/quality/predict", null, {
          params,
          timeout: PREFLIGHT_TIMEOUT_MS,
        });
        const q = qResp.data as { predicted_quality?: number };
        if (q?.predicted_quality != null) next.predicted_quality = q.predicted_quality;
      } catch {
        /* ML may still be warming for a fresh workspace. */
      }
      try {
        const rResp = await api.post("/autonomous/quality/failure-risk", null, {
          params,
          timeout: PREFLIGHT_TIMEOUT_MS,
        });
        const r = rResp.data as { failure_risk?: number; risk?: number };
        const risk = r?.failure_risk ?? r?.risk;
        if (risk != null) next.failure_risk = risk;
      } catch {
        /* ML may still be warming for a fresh workspace. */
      }

      setPreflight(next);
    } catch (err) {
      const msg = responseDetail(err);
      const friendly = /timeout|network|ERR_NETWORK|ECONN/i.test(msg)
        ? "Pre-flight timed out reaching predictors. Run still works; retry pre-flight in a moment."
        : msg;
      setPreflight({ loading: false, error: friendly });
    }
  }, [prompt, selectedModel, selectedModelSlug]);

  const saveAsPipeline = useCallback(async () => {
    const pipelinePrompt = (comparePrompt || prompt).trim();
    if (!pipelinePrompt || savingPipeline) return;
    setSavingPipeline(true);
    try {
      const name = `Playground - ${vertical} - ${new Date().toLocaleDateString()}`;
      const resp = await api.post<{ slug: string }>("/pipelines", {
        name,
        description: `Saved from Playground (${vertical}). Original prompt preserved as input node.`,
        graph: {
          nodes: [
            { id: "input", type: "prompt", label: "User input", prompt: pipelinePrompt },
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
  }, [comparePrompt, prompt, savingPipeline, selectedModelSlug, stats.model, vertical]);

  const eventCount = events.length;
  const tokenCount = stats.completion_tokens ?? 0;
  const canRun = Boolean(
    prompt.trim()
    && selectedModel
    && !models.isLoading
    && !models.isError
    && (!compareOpen || secondaryCompareModel),
  );
  const hasCompareOutput = Object.values(compareResults).some((result) => result.status === "done" && Boolean(result.responseText));
  const hasRunOutput = Boolean(responseText || hasCompareOutput);

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
            compare_prompt: comparePrompt,
            compare_results: compareResults,
            stats,
            events,
            audit_export_pinned: auditExportPinned,
            controls: {
              session_tag: sessionTag,
              auto_redact: autoRedact,
              lock_to_on_prem: effectiveLockToOnPrem,
              temperature,
              top_p: topP,
              top_k: topK,
              max_tokens: maxTokens,
              frequency_penalty: frequencyPenalty,
              presence_penalty: presencePenalty,
              stream: streamEnabled,
              response_format: responseFormat,
              seed,
            },
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
    a.download = `veklom-audit-${stats.request_id ?? "compare"}-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(href);
  };

  const sessionUnits = conversation.reduce((total, turn) => total + (turn.tokens ?? 0), 0);
  const sessionCostLabel = stats.cost_usd ?? "$0.00";
  const latestLatency = stats.latency_ms ?? "-";
  const complianceTag = sessionTag;
  const inputEstimate = Math.ceil(prompt.length / 4) || 0;
  const outputRate = selectedModel?.output_cost_per_1k ?? 0.79;
  const inputRate = selectedModel?.input_cost_per_1k ?? 0.59;
  const estimatedRunCost = ((inputEstimate / 1000) * inputRate + (maxTokens / 1000) * outputRate).toFixed(4);
  const contextLabel = selectedModel?.context_window
    ? `${Math.round(selectedModel.context_window / 1000)}K`
    : "128K";
  const quantLabel = selectedModel?.quantization ?? "FP16";
  // Show live observed latency when available; fall back to model profile only as a secondary estimate.
  const p50Label = stats.latency_ms ? `${stats.latency_ms} ms` : selectedModel?.p50_ms ? `~${selectedModel.p50_ms} ms` : "-";
  const p95Label = selectedModel?.p95_ms ? `~${selectedModel.p95_ms} ms` : "-";
  const playgroundFlowStatus: FlowStatus = running
    ? "running"
    : error
      ? "failed"
      : hasRunOutput
        ? "succeeded"
        : models.isError
          ? "unavailable"
          : "idle";
  const completionStepStatus: FlowStatus = running
    ? "running"
    : error
      ? "failed"
      : hasRunOutput
        ? "succeeded"
        : "idle";
  const policyStepStatus: FlowStatus = running
    ? "running"
    : error
      ? "failed"
      : eventCount || hasRunOutput
        ? "succeeded"
        : "idle";
  const traceHref = `/monitoring${stats.request_id ? `?run=${encodeURIComponent(stats.request_id)}` : ""}`;
  const proofAudit = stats.audit_hash ?? stats.request_id ?? (hasCompareOutput ? "compare results returned" : "not created yet");

  return (
    <div className="mx-auto w-full max-w-[1400px]">
      <header className="mb-4 flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="text-eyebrow">Workspace · Playground</div>
          <h1 className="font-display mt-1 text-[30px] font-semibold tracking-tight text-bone">Playground</h1>
          <p className="mt-2 max-w-2xl text-sm text-bone-2">
            Test an industry-specific AI workflow, then turn it into a governed GPC-ready handoff with policy,
            evidence, cost, and private runtime controls attached.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <span className="chip border-brass/40 bg-brass/10 text-brass-2">
              <span className="h-1.5 w-1.5 rounded-full bg-brass-2" />
              {selectedModel?.provider ?? "provider"} route
            </span>
            <span className="chip border-rule bg-ink/40 text-bone-2">{latestLatency} p50</span>
            <span className="chip border-rule bg-ink/40 text-bone-2">{sessionCostLabel} session · {sessionUnits} out</span>
            <span className="chip border-brass/40 bg-brass/10 text-brass-2">{complianceTag}</span>
            <span className="chip border-rule bg-ink/40 text-bone-2">
              {playgroundProfile?.profileName ?? "Loading workspace profile"}
            </span>
            <span className={cn("chip", autoRedact ? "border-brass/40 bg-brass/10 text-brass-2" : "border-rule bg-ink/40 text-muted")}>
              <Shield className="h-3 w-3" />
              {autoRedact ? "Auto-redact" : "Redact off"}
            </span>
            <span className="chip border-moss/30 bg-moss/10 text-moss">
              <span className="h-1.5 w-1.5 animate-pulse-soft rounded-full bg-moss" />
              POLICY ENGINE LIVE
            </span>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <button type="button" className="v-btn-primary h-8 px-3 text-xs" onClick={exportAudit} disabled={!events.length || running}>
            <Download className="h-3.5 w-3.5" /> Audit export
          </button>
          <button type="button" className="v-btn-ghost h-8 px-3 text-xs" onClick={saveAsPipeline} disabled={!hasRunOutput || running || savingPipeline}>
            <Save className="h-3.5 w-3.5" /> {savingPipeline ? "Saving" : "Save prompt"}
          </button>
          <button type="button" className="v-btn-ghost h-8 px-3 text-xs" disabled title="Branching requires a saved pipeline run">
            <GitBranch className="h-3.5 w-3.5" /> Branch
          </button>
        </div>
      </header>

      <RunStatePanel
        className="mb-4"
        eyebrow="Playground loop"
        title={compareOpen ? "Compare is running governed model-specific completions" : "Prompt, run, prove, then save as pipeline"}
        status={playgroundFlowStatus}
        summary="This page now completes the run loop here: the prompt starts in Playground, `/ai/complete` executes live, telemetry is shown, proof is available, and the next action is explicit."
        steps={[
          {
            label: "Prompt prepared",
            status: prompt.trim() ? "succeeded" : "idle",
            detail: prompt.trim() ? `${inputEstimate} estimated input tokens` : "enter a prompt",
          },
          {
            label: "Policy and reserve gate",
            status: policyStepStatus,
            detail: `${sessionTag} / outbound.public.v3`,
          },
          {
            label: compareOpen ? "Two model completions" : "Model completion",
            status: completionStepStatus,
            detail: compareOpen
              ? `${selectedModel?.slug ?? "primary"} + ${secondaryCompareModel?.slug ?? "secondary"}`
              : selectedModel?.slug ?? "no connected model",
          },
          {
            label: "Pipeline handoff",
            status: savedPipelineSlug ? "succeeded" : "idle",
            detail: savedPipelineSlug ?? "available after a successful run",
          },
        ]}
        metrics={[
          { label: "mode", value: compareOpen ? "compare" : "single" },
          { label: "latency", value: stats.latency_ms ? `${stats.latency_ms}ms` : running ? "running" : "not run" },
          { label: "output", value: hasCompareOutput ? `${Object.values(compareResults).filter((result) => result.status === "done").length} panes` : `${tokenCount} tokens` },
          { label: "proof", value: stats.audit_hash ? "audit hash" : stats.request_id ? "request id" : hasCompareOutput ? "per-model proof" : "pending" },
        ]}
        error={error}
        actions={[
          { label: running ? "Running" : "Send", onClick: () => void run(), disabled: !canRun || running, primary: true },
          { label: "Save as Pipeline", onClick: () => void saveAsPipeline(), disabled: !hasRunOutput || running || savingPipeline },
          { label: "Open pipeline", href: "/pipelines", disabled: !savedPipelineSlug },
          { label: "View trace", href: traceHref, disabled: !stats.request_id && !stats.audit_hash && !hasCompareOutput },
        ]}
      />

      <ProofStrip
        className="mb-4"
        items={[
          { label: "Completion route", value: "/api/v1/ai/complete" },
          { label: "Model source", value: selectedModel?.slug ?? "workspace model required" },
          { label: "Audit proof", value: proofAudit },
          { label: "Pipeline", value: savedPipelineSlug ?? "not saved yet" },
        ]}
      />

      <div className="grid grid-cols-12 gap-4 py-4">
        <aside className="col-span-12 space-y-3 xl:col-span-2">
          <div className="frame">
            <SideHeader icon={<MessageSquare className="h-3.5 w-3.5" />} label="Sessions" />
            <div className="space-y-1 px-2 py-2">
              <button className="hover-elevate flex w-full items-center justify-between rounded-md bg-white/[0.035] px-2 py-1.5 text-left text-[12px]">
                <span className="flex min-w-0 items-center gap-2">
                  <span className="h-1.5 w-1.5 rounded-full bg-moss" />
                  <span className="truncate">{conversation.length ? "Current governed thread" : "New governed thread"}</span>
                </span>
                <span className="font-mono text-[10px] text-muted">{conversation.length}t</span>
              </button>
              <button className="hover-elevate flex w-full items-center justify-between rounded-md px-2 py-1.5 text-left text-[12px]" disabled>
                <span className="flex min-w-0 items-center gap-2">
                  <span className="h-1.5 w-1.5 rounded-full bg-brass-2" />
                  <span className="truncate">Last audit export</span>
                </span>
                <span className="font-mono text-[10px] text-muted">{hasRunOutput ? "ready" : "none"}</span>
              </button>
            </div>
          </div>

          <div className="frame">
            <SideHeader icon={<Sparkles className="h-3.5 w-3.5" />} label="Prompt Library" />
            <div className="space-y-1 px-2 py-2">
              {profileQuery.isLoading && (
                <div className="px-2 py-2 font-mono text-[11px] text-muted">
                  Loading vertical profile…
                </div>
              )}
              {profileQuery.isError && (
                <div className="rounded-md border border-crimson/30 bg-crimson/10 px-3 py-2 text-[11px] text-crimson">
                  {responseDetail(profileQuery.error)}
                </div>
              )}
              {activeScenarios.map((scenario) => (
                <button
                  key={scenario.scenario_id}
                  onClick={() => void applyScenario(scenario)}
                  className={cn(
                    "hover-elevate flex w-full items-center justify-between rounded-md px-2 py-1.5 text-left",
                    selectedScenarioId === scenario.scenario_id && "bg-brass/10 text-brass-2",
                  )}
                  type="button"
                >
                  <span className="truncate font-mono text-[11.5px]">{scenario.title}</span>
                  <span className="font-mono text-[10px] text-muted">{playgroundProfile?.risk_tier ?? "draft"}</span>
                </button>
              ))}
            </div>
            <div className="border-t border-rule px-3 py-2 text-[10.5px] text-muted">
              Workspace profile drives scenarios, evidence, blocking rules, and GPC templates.
            </div>
          </div>

          <div className="frame">
            <SideHeader icon={<Shield className="h-3.5 w-3.5" />} label="Vertical Profile" />
            <div className="space-y-3 px-3 py-3 text-[11px] text-bone-2">
              <div>
                <div className="text-eyebrow">Workspace profile</div>
                <div className="mt-1 text-sm text-bone">{playgroundProfile?.profileName ?? "Loading profile"}</div>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <ModelFact label="Industry" value={(playgroundProfile?.industry ?? vertical).replace(/_/g, " ")} />
                <ModelFact label="Risk" value={playgroundProfile?.risk_tier ?? "generic"} />
              </div>
              <div>
                <div className="mb-1 text-eyebrow">Policy checks</div>
                <ul className="space-y-1 text-[11px] text-muted">
                  {(playgroundProfile?.policy_checks ?? []).slice(0, 3).map((item) => (
                    <li key={item}>+ {item}</li>
                  ))}
                </ul>
              </div>
              <div>
                <div className="mb-1 text-eyebrow">Evidence emphasis</div>
                <div className="flex flex-wrap gap-1.5">
                  {(selectedScenario?.evidence_emphasis ?? playgroundProfile?.evidence_requirements ?? []).slice(0, 5).map((item) => (
                    <span key={item} className="chip border-rule bg-ink/40 text-muted">{item}</span>
                  ))}
                </div>
              </div>
              {playgroundProfile?.regulated_defaults?.sensitive_data_warning_visible && (
                <div className="rounded-md border border-brass/30 bg-brass/10 px-3 py-2 text-[11px] text-brass-2">
                  Sensitive-data and regulated-claim warnings are active. No public regulated claims publish without founder approval.
                </div>
              )}
            </div>
          </div>

          <div className="frame">
            <SideHeader icon={<SlidersHorizontal className="h-3.5 w-3.5" />} label="Tools / Functions" />
            <div className="space-y-1 px-2 py-2">
              <ToolRow name="compliance.fetch" enabled detail="live compliance route" />
              <ToolRow name="vault.read" enabled detail="workspace API keys" />
              <ToolRow name="http.get" detail="pipeline tool only" />
              <ToolRow name="sql.exec" detail="disabled for playground" />
            </div>
          </div>
        </aside>

        <section className="frame col-span-12 overflow-hidden xl:col-span-7">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-rule px-4 py-2">
            <div className="flex flex-wrap items-center gap-2">
              <div className="inline-flex h-8 items-center rounded-md border border-rule bg-ink/40 p-1">
                <ModeButton active={mode === "chat"} onClick={() => setMode("chat")} icon={<MessageSquare className="h-3.5 w-3.5" />}>
                  Chat
                </ModeButton>
                <ModeButton active={mode === "completion"} onClick={() => setMode("completion")} icon={<TerminalSquare className="h-3.5 w-3.5" />}>
                  Completion
                </ModeButton>
              </div>
              <div className="ml-1 flex items-center gap-2 text-[11px] text-muted">
                <Cpu className="h-3.5 w-3.5" />
                <span>{selectedModel?.name ?? "No model connected"}</span>
                <span className="text-muted/60">·</span>
                <span className="font-mono">{maxTokens} max out</span>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button
                className={cn("flex items-center gap-1.5 rounded-md border px-2 py-1 text-[11px] hover-elevate", compareOpen ? "border-brass/40 bg-brass/10 text-brass-2" : "border-rule bg-ink/40 text-muted")}
                onClick={() => setCompareOpen((prev) => !prev)}
                type="button"
              >
                <Box className="h-3.5 w-3.5" /> Compare {compareOpen ? "ON" : "off"}
              </button>
              <button className="rounded-md border border-rule bg-ink/40 px-2 py-1 text-[11px] text-muted hover-elevate" onClick={clearConversation} type="button">
                <Trash2 className="mr-1 inline h-3.5 w-3.5" /> Clear
              </button>
            </div>
          </div>

          {compareOpen ? (
            <div className="grid min-h-[420px] grid-cols-1 gap-3 px-4 py-4 lg:grid-cols-2">
              <ComparePane
                model={selectedModel?.name ?? "Selected model"}
                prompt={comparePrompt || prompt}
                result={selectedModel ? compareResults[selectedModel.slug] : undefined}
                status={selectedModel ? compareResults[selectedModel.slug]?.status ?? "idle" : "idle"}
              />
              <ComparePane
                model={secondaryCompareModel?.name ?? "Second model"}
                prompt={comparePrompt || prompt}
                result={secondaryCompareModel ? compareResults[secondaryCompareModel.slug] : undefined}
                status={
                  !secondaryCompareModel
                    ? "error"
                    : compareResults[secondaryCompareModel.slug]?.status ?? (runnableModels.length > 1 ? "idle" : "error")
                }
              />
            </div>
          ) : (
            <div ref={threadRef} className="max-h-[58vh] min-h-[420px] space-y-4 overflow-y-auto px-5 py-5">
              {systemPrompt.trim() && <SystemMessage content={systemPrompt.trim()} />}
              {conversation.length === 0 && !running && (
                <div className="grid min-h-[300px] place-items-center text-center">
                  <div>
                    <div className="font-display text-lg text-bone">Bring the governed run to life.</div>
                    <p className="mx-auto mt-2 max-w-xl text-sm leading-relaxed text-bone-2">
                      Use a starter or write your own request. Veklom routes, meters, audits, and logs each step before a model answer is accepted.
                    </p>
                  </div>
                </div>
              )}
              {conversation.map((turn) => (
                <ChatBubble
                  key={turn.id}
                  turn={turn}
                  onCopy={() => void copyTurn(turn.content)}
                  onEdit={() => editAndResendTurn(turn.content)}
                  onRegenerate={turn.role === "assistant" ? () => regenerateFromTurn(turn.id) : undefined}
                />
              ))}
              {running && <AssistantThinking />}
            </div>
          )}

          <div className="border-t border-rule bg-ink-2/50 p-3">
            {conversation.length === 0 && (
              <div className="mb-3 flex flex-wrap gap-2">
                {QUICK_PROMPTS.map((item) => (
                  <button
                    key={item.label}
                    onClick={() => {
                      if (item.vertical) handleVerticalChange(item.vertical);
                      if (item.tag) handleSessionTagChange(item.tag);
                      setPrompt(item.prompt);
                    }}
                    className="hover-elevate rounded-full border border-rule bg-ink/40 px-3 py-1 text-[11px] text-muted hover:text-bone"
                    type="button"
                  >
                    <Sparkles className="mr-1.5 inline h-3 w-3" />
                    {item.label}
                  </button>
                ))}
              </div>
            )}
            {selectedScenario && (
              <div className="mb-3 rounded-lg border border-rule bg-ink/40 px-3 py-3">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <div className="text-eyebrow">Selected scenario</div>
                    <div className="mt-1 text-sm text-bone">{selectedScenario.title}</div>
                    <p className="mt-1 text-[11px] leading-5 text-muted">
                      {(playgroundProfile?.industry ?? vertical).replace(/_/g, " ")} · {playgroundProfile?.policy_pack ?? "policy pack pending"} · risk {playgroundProfile?.risk_tier ?? "generic"}
                    </p>
                  </div>
                  <button
                    type="button"
                    className="v-btn-ghost h-8 px-3 text-xs"
                    onClick={() => void compileWithGpc()}
                    disabled={!prompt.trim() || compileSubmitting}
                  >
                    <GitBranch className="h-3.5 w-3.5" />
                    {compileSubmitting ? "Preparing..." : "Compile with GPC"}
                  </button>
                </div>
                <div className="mt-3 grid gap-3 lg:grid-cols-2">
                  <div>
                    <div className="mb-1 text-eyebrow">Suggested workflow</div>
                    <ul className="space-y-1 text-[11px] text-muted">
                      {selectedScenario.suggested_workflow.map((item) => (
                        <li key={item}>+ {item}</li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <div className="mb-1 text-eyebrow">Models and tools</div>
                    <div className="flex flex-wrap gap-1.5">
                      {selectedScenario.suggested_models_tools.map((item) => (
                        <span key={item} className="chip border-rule bg-ink/40 text-muted">{item}</span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}
            <div className="rounded-lg border border-rule bg-ink/40 focus-within:border-brass/50 focus-within:ring-1 focus-within:ring-brass/30">
              <textarea
                id="prompt"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value.slice(0, 8000))}
                onKeyDown={(e) => {
                  if ((e.ctrlKey || e.metaKey) && e.key === "Enter" && canRun) {
                    e.preventDefault();
                    void run();
                  }
                }}
                placeholder={mode === "chat" ? "Ask anything. ⌘ + Enter to send…" : "Enter your prompt for raw completion…"}
                className="min-h-[88px] w-full resize-none border-0 bg-transparent px-3 py-3 font-mono text-[13px] leading-relaxed text-bone outline-none placeholder:text-muted"
                disabled={running}
              />
              <div className="flex flex-wrap items-center justify-between gap-2 border-t border-rule px-3 py-2">
                <div className="flex flex-wrap items-center gap-2 text-[11px] text-muted">
                  <span className="chip border-rule bg-ink/40 text-muted">${estimatedRunCost}</span>
                  <span className="hidden md:inline">·</span>
                  <span className="hidden font-mono md:inline">est · {outputRate.toFixed(2)}/1K out</span>
                  <span className="hidden md:inline">·</span>
                  <span className="hidden font-mono md:inline">policy: outbound.public.v3</span>
                  <span className="hidden md:inline">·</span>
                  <span className="hidden font-mono md:inline">~{inputEstimate} tok in</span>
                </div>
                <div className="flex items-center gap-2">
                  <button className="v-btn-ghost h-7 px-2 text-xs" type="button" onClick={() => void compileWithGpc()} disabled={!prompt.trim() || compileSubmitting}>
                    <GitBranch className="h-3.5 w-3.5" /> {compileSubmitting ? "Preparing" : "GPC"}
                  </button>
                  <button className="v-btn-ghost h-7 px-2 text-xs" type="button" onClick={() => setToolMenuOpen((prev) => !prev)} title="Show available governed tools">
                    <SlidersHorizontal className="h-3.5 w-3.5" /> Tools
                  </button>
                  <button className="v-btn-ghost h-7 px-2 text-xs" type="button" onClick={exportAudit} disabled={!events.length || running}>
                    <Download className="h-3.5 w-3.5" /> JSON
                  </button>
                  {!running ? (
                    <button className="v-btn-primary h-7 px-3 text-xs" onClick={run} disabled={!canRun} type="button">
                      <Play className="h-3.5 w-3.5" /> Send
                    </button>
                  ) : (
                    <button className="v-btn-ghost h-7 px-3 text-xs text-crimson" onClick={stop} type="button">
                      <CircleStop className="h-3.5 w-3.5" /> Stop
                    </button>
                  )}
                </div>
              </div>
            </div>
            {toolMenuOpen && (
              <div className="mt-2 grid gap-2 rounded-lg border border-rule bg-ink/70 p-2 sm:grid-cols-2">
                <ToolAction name="compliance.fetch" detail="Live evidence and framework checks" enabled />
                <ToolAction name="vault.read" detail="Workspace key inventory" enabled />
                <ToolAction name="pipeline.save" detail="Save this thread into Pipelines" enabled={hasRunOutput} />
                <ToolAction name="http.get" detail="Pipeline-only external fetch" />
              </div>
            )}

            <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
              <div className="flex flex-wrap gap-2">
                <button className="v-btn-ghost text-xs" onClick={runPreflight} disabled={!prompt.trim() || preflight.loading} type="button">
                  <TrendingDown className="h-4 w-4" /> {preflight.loading ? "Predicting..." : "Pre-flight"}
                </button>
                <button className="v-btn-ghost text-xs" onClick={saveAsPipeline} disabled={!hasRunOutput || running || savingPipeline} type="button">
                  <Save className="h-4 w-4" /> {savingPipeline ? "Saving..." : savedPipelineSlug ? "Saved" : "Save as Pipeline"}
                </button>
                {conversation.length > 0 && (
                  <button className="v-btn-ghost text-xs" onClick={clearConversation} title="Clear thread" type="button">
                    <Trash2 className="h-3.5 w-3.5" /> New conversation
                  </button>
                )}
              </div>
              <div className="flex gap-2 font-mono text-[11px]">
                <span className="chip border-rule bg-ink/40 text-bone-2"><Activity className="h-3 w-3" /> {eventCount} events</span>
                <span className="chip border-rule bg-ink/40 text-bone-2"><Sparkles className="h-3 w-3" /> {tokenCount} out</span>
                <span className="chip border-rule bg-ink/40 text-bone-2"><MessageSquare className="h-3 w-3" /> {conversation.length} turns</span>
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
                <a href="/pipelines" className="ml-auto inline-flex items-center gap-1 text-moss underline-offset-4 hover:underline">
                  Open Pipelines <GitBranch className="h-3 w-3" />
                </a>
              </div>
            )}
            {(preflight.predicted_cost != null || preflight.error) && (
              <div className="mt-3 rounded-md border border-rule/70 bg-ink p-3">
                <div className="mb-2 flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.12em] text-muted">
                  <Zap className="h-3 w-3 text-brass-2" /> Pre-flight intelligence
                </div>
                {preflight.error ? (
                  <div className="font-mono text-[12px] text-crimson">{preflight.error}</div>
                ) : (
                  <div className="grid grid-cols-1 gap-3 font-mono text-[12px] sm:grid-cols-3">
                    <PreflightCell label="cost / run" value={preflight.predicted_cost != null ? `$${preflight.predicted_cost.toFixed(4)}` : "-"} sub={preflight.cost_confidence_upper != null && preflight.predicted_cost != null ? `+/-$${Math.abs(preflight.cost_confidence_upper - preflight.predicted_cost).toFixed(4)}` : "server-side ml"} tone="ok" />
                    <PreflightCell label="quality" value={preflight.predicted_quality != null ? `${(preflight.predicted_quality * 100).toFixed(0)}%` : "-"} sub={preflight.predicted_quality != null ? "predicted" : "ml warming"} tone={preflight.predicted_quality != null && preflight.predicted_quality > 0.8 ? "ok" : "warn"} />
                    <PreflightCell label="failure risk" value={preflight.failure_risk != null ? `${(preflight.failure_risk * 100).toFixed(0)}%` : "-"} sub={preflight.failure_risk != null ? "before run" : "ml warming"} tone={preflight.failure_risk != null && preflight.failure_risk < 0.2 ? "ok" : "warn"} />
                  </div>
                )}
              </div>
            )}
          </div>
        </section>

        <aside className="col-span-12 space-y-3 xl:col-span-3">
          <div className="frame">
            <SideHeader icon={<Cpu className="h-3.5 w-3.5" />} label="Model" />
            <div className="px-3 pb-3 pt-2">
              {models.isLoading ? (
                <div className="flex items-center gap-2 font-mono text-[12px] text-muted">
                  <Loader2 className="h-3.5 w-3.5 animate-spin" /> Loading live models...
                </div>
              ) : models.isError ? (
                <div className="rounded-md border border-crimson/30 bg-crimson/10 px-3 py-2 text-[12px] text-crimson">
                  {responseDetail(models.error)}
                </div>
              ) : runnableModels.length ? (
                <>
                  <select className="v-input h-9 w-full" value={selectedModel?.slug ?? ""} disabled={running} onChange={(e) => setSelectedModelSlug(e.target.value)}>
                    {runnableModels.map((model) => (
                      <option key={model.slug} value={model.slug}>{model.name}</option>
                    ))}
                  </select>
                  {quarantinedGroqModels.length > 0 && (
                    <div className="mt-2 rounded-md border border-brass/30 bg-brass/10 px-3 py-2 text-[11px] text-brass-2">
                      Groq direct Playground sends are paused until provider health is verified. The default buyer path is using live Ollama.
                    </div>
                  )}
                  <div className="mt-3 rounded-lg border border-brass/25 bg-brass/10 px-3 py-2">
                    <div className="truncate font-display text-sm text-bone">
                      {selectedModel?.name ?? "Llama 3.1 70B Instruct"}
                    </div>
                    <div className="mt-1 flex flex-wrap gap-1.5">
                      <span className="chip border-rule bg-ink/40 text-muted">{selectedModel?.model_type ?? "chat"}</span>
                      <span className="chip border-rule bg-ink/40 text-muted">Context {contextLabel}</span>
                      <span className="chip border-rule bg-ink/40 text-muted">Quant {quantLabel}</span>
                    </div>
                  </div>
                  <div className="mt-3 grid grid-cols-2 gap-2 text-[11px] text-muted">
                    <ModelFact label="P50" value={p50Label} />
                    <ModelFact label="P95" value={p95Label} />
                    <ModelFact label="In $/1K tok" value={`$${inputRate.toFixed(2)}`} />
                    <ModelFact label="Out $/1K tok" value={`$${outputRate.toFixed(2)}`} />
                    <ModelFact label="Provider" value={selectedModel?.provider ?? "-"} />
                    <ModelFact label="Runtime" value={selectedModel?.runtime_model_id ?? "-"} />
                  </div>
                </>
              ) : (
                <div className="rounded-md border border-brass/30 bg-brass/10 px-3 py-2 text-[12px] text-brass-2">
                  No connected non-Groq models are enabled for this workspace. Groq direct Playground sends are paused until provider health is verified.
                </div>
              )}
            </div>
          </div>

          <div className="frame">
            <SideHeader icon={<SlidersHorizontal className="h-3.5 w-3.5" />} label="Parameters" action={<button className="text-eyebrow hover:text-bone" onClick={resetParameters} type="button">Reset</button>} />
            <div className="space-y-3 px-3 pb-3 pt-2">
              <RangeControl label="Temperature" hint="creativity" value={temperature.toFixed(2)} min={0} max={1.2} step={0.05} current={temperature} onChange={setTemperature} disabled={running} />
              <RangeControl label="Top-p" hint="nucleus" value={topP.toFixed(2)} min={0.05} max={1} step={0.05} current={topP} onChange={setTopP} disabled={running} />
              <RangeControl label="Top-k" hint="vocab" value={String(topK)} min={1} max={100} step={1} current={topK} onChange={setTopK} disabled={running} />
              <RangeControl label="Max tokens" hint="cap" value={String(maxTokens)} min={128} max={4096} step={128} current={maxTokens} onChange={setMaxTokens} disabled={running} />
              <RangeControl label="Frequency penalty" hint="repeat" value={frequencyPenalty.toFixed(2)} min={-2} max={2} step={0.1} current={frequencyPenalty} onChange={setFrequencyPenalty} disabled={running} />
              <RangeControl label="Presence penalty" hint="novelty" value={presencePenalty.toFixed(2)} min={-2} max={2} step={0.1} current={presencePenalty} onChange={setPresencePenalty} disabled={running} />
              <ToggleRow icon={<Zap className="h-3.5 w-3.5" />} label="Stream" checked={streamEnabled} onChange={setStreamEnabled} disabled={running} />
              <div>
                <div className="mb-1.5 flex items-center justify-between">
                  <span className="text-[11.5px]">Response format</span>
                  <span className="font-mono text-[11px] text-bone">{responseFormat}</span>
                </div>
                <div className="grid grid-cols-3 gap-1">
                  {(["text", "json", "json-schema"] as ResponseFormat[]).map((format) => (
                    <button
                      key={format}
                      type="button"
                      disabled={running}
                      onClick={() => setResponseFormat(format)}
                      className={cn(
                        "rounded-md border px-2 py-1.5 text-[10.5px] hover-elevate disabled:opacity-50",
                        responseFormat === format ? "border-brass/40 bg-brass/15 text-bone" : "border-rule bg-ink/40 text-muted",
                      )}
                    >
                      {format}
                    </button>
                  ))}
                </div>
              </div>
              <label className="block">
                <div className="mb-1 flex items-end justify-between">
                  <span className="text-[11.5px]">Seed</span>
                  <span className="font-mono text-[11px] text-bone">{seed}</span>
                </div>
                <input
                  className="v-input h-8 w-full font-mono text-[12px]"
                  type="number"
                  min={0}
                  max={2147483647}
                  value={seed}
                  disabled={running}
                  onChange={(e) => setSeed(Number(e.target.value) || 0)}
                />
              </label>
            </div>
          </div>

          <div className="frame">
            <SideHeader icon={<Shield className="h-3.5 w-3.5" />} label="Compliance" />
            <div className="space-y-2.5 px-3 pb-3 pt-2">
              <div>
                <div className="mb-1.5 text-eyebrow">Session tag</div>
                <div className="grid grid-cols-3 gap-1">
                  {SESSION_TAGS.map((tag) => (
                    <button
                      key={tag}
                      onClick={() => handleSessionTagChange(tag)}
                      className={cn("rounded-md border px-2 py-1.5 text-[11px] hover-elevate", sessionTag === tag ? "border-brass/40 bg-brass/15 text-bone" : "border-rule bg-ink/40 text-muted")}
                      type="button"
                    >
                      {tag}
                    </button>
                  ))}
                </div>
                <p className="mt-2 text-[10.5px] leading-snug text-muted">
                  Tag scopes routing rules and redaction. PHI/HIPAA forces Hetzner-only with auto-redact and audit export pinned ON.
                </p>
              </div>
              <ToggleRow icon={<Shield className="h-3.5 w-3.5" />} label="Auto-redact PHI/PII" checked={autoRedact} onChange={setAutoRedact} disabled={protectedSession} />
              <ToggleRow icon={<Download className="h-3.5 w-3.5" />} label="Sign audit on export" checked={auditExportPinned} onChange={setAuditExportPinned} disabled={protectedSession} />
              <ToggleRow icon={<Cpu className="h-3.5 w-3.5" />} label="Lock to on-prem (no AWS burst)" checked={effectiveLockToOnPrem} onChange={setLockToOnPrem} disabled={protectedSession} />
            </div>
            <div className="border-t border-rule px-3 py-2 text-[10.5px] text-muted">
              SHA-256 manifest emitted per session · evidence ready
            </div>
          </div>

          <div className="frame">
            <SideHeader icon={<GitBranch className="h-3.5 w-3.5" />} label="GPC Handoff" />
            <div className="space-y-3 px-3 py-3 text-[11px] text-bone-2">
              {handoffPreview ? (
                <>
                  <div>
                    <div className="text-eyebrow">Prepared handoff</div>
                    <div className="mt-1 text-sm text-bone">{handoffPreview.scenario_title}</div>
                    <div className="mt-1 font-mono text-[10px] text-muted">
                      {handoffPreview.handoff_status} · {handoffPreview.claim_level} · {handoffPreview.policy_pack}
                    </div>
                  </div>
                  <div>
                    <div className="mb-1 text-eyebrow">Evidence requirements</div>
                    <div className="flex flex-wrap gap-1.5">
                      {handoffPreview.evidence_requirements.map((item) => (
                        <span key={item} className="chip border-rule bg-ink/40 text-muted">{item}</span>
                      ))}
                    </div>
                  </div>
                  <div>
                    <div className="mb-1 text-eyebrow">Blocking rules</div>
                    <ul className="space-y-1 text-[11px] text-muted">
                      {handoffPreview.blocking_rules.map((item) => (
                        <li key={item}>+ {item}</li>
                      ))}
                    </ul>
                  </div>
                  <button
                    type="button"
                    className="v-btn-primary h-9 w-full px-3 text-xs"
                    onClick={() => void createFounderReviewArtifact()}
                    disabled={artifactSubmitting}
                  >
                    <Sparkles className="h-3.5 w-3.5" />
                    {artifactSubmitting ? "Drafting..." : "Create founder-review artifact"}
                  </button>
                </>
              ) : (
                <div className="rounded-md border border-rule bg-ink/40 px-3 py-3 text-muted">
                  Compile a selected scenario with GPC to prepare the governed handoff object.
                </div>
              )}
            </div>
          </div>

          <div className="frame">
            <SideHeader icon={<MessageSquare className="h-3.5 w-3.5" />} label="Commercial Review" />
            <div className="space-y-3 px-3 py-3 text-[11px] text-bone-2">
              {artifactDraft ? (
                <>
                  <div>
                    <div className="text-eyebrow">Community Awareness Run</div>
                    <div className="mt-1 text-sm text-bone">{artifactDraft.title}</div>
                    <div className="mt-1 font-mono text-[10px] text-muted">
                      founder review: {artifactDraft.founderReviewStatus} · outcome: {artifactDraft.outcome}
                    </div>
                  </div>
                  <div className="rounded-md border border-brass/30 bg-brass/10 px-3 py-2 text-[11px] text-brass-2">
                    No auto-posting. Public-facing copy stays draft until founder approval.
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <button type="button" className="v-btn-ghost h-8 px-3 text-xs" onClick={() => void founderReviewArtifact("approved_by_founder")}>
                      Approve draft
                    </button>
                    <button type="button" className="v-btn-ghost h-8 px-3 text-xs" onClick={() => void founderReviewArtifact("blocked_by_founder")}>
                      Block draft
                    </button>
                  </div>
                </>
              ) : (
                <div className="rounded-md border border-rule bg-ink/40 px-3 py-3 text-muted">
                  Prepared handoffs can become founder-review-gated public or community artifacts from here.
                </div>
              )}
              <button
                type="button"
                className="v-btn-ghost h-8 w-full px-3 text-xs"
                onClick={() => void markEvaluationConversation()}
                disabled={!handoffPreview || markingEvaluation}
              >
                <MessageSquare className="h-3.5 w-3.5" />
                {markingEvaluation ? "Recording..." : "Mark evaluation conversation influenced"}
              </button>
            </div>
          </div>

          <TelemetryPanel stats={stats} conversationLength={conversation.length} />
          <EventLogPanel events={events} running={running} feedRef={feedRef} eventCount={eventCount} />
        </aside>
      </div>
    </div>
  );

  return (
    <div className="mx-auto w-full max-w-7xl space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="mb-1 font-mono text-[11px] uppercase tracking-[0.15em] text-muted">
            Workspace - Playground
          </div>
          <h1 className="text-3xl font-semibold tracking-tight">Authenticated AI execution</h1>
          <p className="mt-2 max-w-2xl text-sm text-bone-2">
            Send a real workspace request through Veklom's governed execution endpoint. The backend selects the
            runtime, enforces model availability, records the reserve debit, and writes the audit artifact.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <span className="v-chip v-chip-ok">
              <span className="h-1.5 w-1.5 animate-pulse-soft rounded-full bg-moss" />
              authenticated - <span className="font-mono">/api/v1/ai/complete</span>
            </span>
            <span className="v-chip">reserve metered</span>
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
                {quarantinedGroqModels.length > 0 && (
                  <div className="rounded-md border border-brass/30 bg-brass/10 px-3 py-2 text-[11px] text-brass-2">
                    Groq direct Playground sends are paused until provider health is verified. The default buyer path is using live Ollama.
                  </div>
                )}
                {selectedModel && (
                  <div className="space-y-1 font-mono text-[11px] text-muted">
                    <div>slug: <span className="text-bone">{selectedModel.slug}</span></div>
                    <div>provider: <span className="text-bone">{selectedModel.provider}</span></div>
                    <div>runtime: <span className="text-bone">{selectedModel.runtime_model_id}</span></div>
                  </div>
                )}
                <label className="block">
                  <div className="mb-1 font-mono text-[10px] uppercase tracking-wider text-muted">Max output units</div>
                  <select
                    className="v-input w-full"
                    value={maxTokens}
                    disabled={running}
                    onChange={(e) => setMaxTokens(Number(e.target.value))}
                  >
                    {[128, 256, 512, 1024, 2048, 4096].map((n) => (
                      <option key={n} value={n}>{n}</option>
                    ))}
                  </select>
                </label>
                <label className="block">
                  <div className="mb-1 font-mono text-[10px] uppercase tracking-wider text-muted">Sampling</div>
                  <div className="flex items-center gap-3">
                    <input
                      type="range"
                      min={0}
                      max={1.2}
                      step={0.1}
                      value={temperature}
                      disabled={running}
                      onChange={(e) => setTemperature(Number(e.target.value))}
                      className="w-full accent-[var(--brass)]"
                    />
                    <span className="min-w-10 text-right font-mono text-[11px] text-bone">{temperature.toFixed(1)}</span>
                  </div>
                </label>
                <button
                  type="button"
                  className="flex w-full items-center justify-between rounded-lg border border-rule-2 bg-white/[0.02] px-3 py-2 text-left text-[12px] text-bone-2"
                  onClick={() => setShowSystemPrompt((prev) => !prev)}
                >
                  <span className="flex items-center gap-2 font-medium">
                    <SlidersHorizontal className="h-3.5 w-3.5 text-brass-2" />
                    System instruction
                  </span>
                  {showSystemPrompt ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
                </button>
                {showSystemPrompt && (
                  <textarea
                    className="v-input min-h-[108px] resize-y font-mono text-[12px] leading-relaxed"
                    value={systemPrompt}
                    onChange={(e) => setSystemPrompt(e.target.value.slice(0, 12000))}
                    placeholder="You are a governed AI assistant running inside Veklom's sovereign control plane..."
                    disabled={running}
                  />
                )}
              </div>
            ) : (
              <div className="rounded-md border border-brass/30 bg-brass/10 px-3 py-2 text-[12px] text-brass-2">
                No connected non-Groq models are enabled for this workspace. Groq direct Playground sends are paused until provider health is verified.
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
                "Reserve metering",
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
                        <span className="font-mono text-[10px] text-muted">{turn.tokens} out</span>
                      )}
                    </div>
                    <div className="whitespace-pre-wrap font-mono text-[13px] leading-relaxed text-bone">
                      {turn.content}
                    </div>
                    <div className="mt-2 flex flex-wrap gap-2">
                      <button className="v-btn-ghost text-[11px]" onClick={() => void copyTurn(turn.content)}>
                        <Copy className="h-3.5 w-3.5" /> Copy
                      </button>
                      <button className="v-btn-ghost text-[11px]" onClick={() => editAndResendTurn(turn.content)}>
                        <Pencil className="h-3.5 w-3.5" /> Edit
                      </button>
                      {turn.role === "assistant" && (
                        <button className="v-btn-ghost text-[11px]" onClick={() => regenerateFromTurn(turn.id)}>
                          <RotateCcw className="h-3.5 w-3.5" /> Regenerate
                        </button>
                      )}
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
              <span className="font-mono text-[10px] text-muted">{prompt.length} / 8000</span>
            </div>
            <textarea
              id="prompt"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value.slice(0, 8000))}
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
            {!conversation.length && (
              <div className="mt-3 flex flex-wrap gap-2">
                {VERTICALS.map((item) => (
                  <button
                    key={item.value}
                    type="button"
                    className="v-chip hover:text-bone"
                    onClick={() => {
                      setVertical(item.value);
                      setPrompt(SAMPLE_PROMPTS[item.value]);
                    }}
                  >
                    {item.label} starter
                  </button>
                ))}
              </div>
            )}
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
                  disabled={!hasRunOutput || running || savingPipeline}
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
                  <Sparkles className="h-3 w-3" /> {tokenCount} output units
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
                <a href="/pipelines" className="ml-auto inline-flex items-center gap-1 text-moss underline-offset-4 hover:underline">
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
                      value={preflight.predicted_cost != null ? `$${preflight.predicted_cost!.toFixed(4)}` : "-"}
                      sub={
                        preflight.cost_confidence_upper != null && preflight.predicted_cost != null
                          ? `+/-$${Math.abs(preflight.cost_confidence_upper! - preflight.predicted_cost!).toFixed(4)}`
                          : "server-side ml"
                      }
                      tone="ok"
                    />
                    <PreflightCell
                      label="quality"
                      value={
                        preflight.predicted_quality != null
                          ? `${(preflight.predicted_quality! * 100).toFixed(0)}%`
                          : "-"
                      }
                      sub={preflight.predicted_quality != null ? "predicted" : "ml warming"}
                      tone={preflight.predicted_quality != null && preflight.predicted_quality! > 0.8 ? "ok" : "warn"}
                    />
                    <PreflightCell
                      label="failure risk"
                      value={
                        preflight.failure_risk != null
                          ? `${(preflight.failure_risk! * 100).toFixed(0)}%`
                          : "-"
                      }
                      sub={preflight.failure_risk != null ? "before run" : "ml warming"}
                      tone={preflight.failure_risk != null && preflight.failure_risk! < 0.2 ? "ok" : "warn"}
                    />
                  </div>
                )}
                {preflight.alternatives?.length ? (
                  <div className="mt-2 flex flex-wrap gap-1.5 font-mono text-[10px]">
                    {preflight.alternatives!.slice(0, 3).map((alt) => (
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
          {responseText && conversation.length === 0 && (
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
                <div className="font-mono text-[11px] uppercase tracking-[0.12em] text-muted">Playground ready</div>
              </header>
              <div className="min-h-[180px] p-4">
                <div className="font-display text-lg text-bone">Bring the governed run to life.</div>
                <p className="mt-2 max-w-2xl text-sm leading-relaxed text-bone-2">
                  Use a starter above or write your own request. Veklom will route, meter, audit, and log each step before a model answer is accepted.
                </p>
                <div className="mt-4 grid gap-2 sm:grid-cols-2">
                  {Object.entries(SAMPLE_PROMPTS).slice(0, 4).map(([key, value]) => (
                    <button
                      key={key}
                      type="button"
                      className="rounded-lg border border-rule-2 bg-white/[0.02] px-3 py-3 text-left text-[12px] text-bone-2 hover:bg-white/[0.04]"
                      onClick={() => setPrompt(value)}
                    >
                      {value}
                    </button>
                  ))}
                </div>
                {running && <span className="mt-4 inline-block h-4 w-2 animate-pulse bg-brass" />}
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
              <Stat
                label="routing"
                value={stats.fallback_triggered ? `${stats.requested_provider ?? "primary"} -> ${stats.provider ?? "fallback"}` : "primary"}
              />
              <Stat label="model" value={stats.model ?? "-"} />
              <Stat label="runtime" value={stats.runtime_model_id ?? "-"} mono />
              <Stat label="input units" value={stats.prompt_tokens?.toString() ?? "-"} />
              <Stat label="output units" value={stats.completion_tokens?.toString() ?? "-"} />
              <Stat label="total units" value={stats.total_tokens?.toString() ?? "-"} />
              <Stat label="latency" value={stats.latency_ms ? `${stats.latency_ms} ms` : "-"} />
              <Stat label="billing event" value={stats.billing_event_type?.replace(/_/g, " ") ?? "-"} />
              <Stat label="pricing tier" value={stats.pricing_tier?.replace(/_/g, " ") ?? "-"} />
              <Stat label="reserve debit" value={(stats.reserve_debited ?? stats.tokens_deducted)?.toString() ?? "-"} />
              <Stat label="reserve balance" value={stats.wallet_balance?.toString() ?? "-"} />
              <Stat label="free runs left" value={stats.free_evaluation_remaining?.toString() ?? "-"} />
              <Stat label="audit hash" value={stats.audit_hash ? `${stats.audit_hash!.slice(0, 12)}...` : "-"} mono />
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

function SideHeader({ icon, label, action }: { icon: React.ReactNode; label: string; action?: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between border-b border-rule px-3 py-2">
      <span className="text-eyebrow flex items-center gap-2 text-bone-2">
        {icon}
        {label}
      </span>
      {action}
    </div>
  );
}

function ToolRow({ name, detail, enabled }: { name: string; detail: string; enabled?: boolean }) {
  return (
    <div className="flex items-center justify-between rounded-md px-2 py-1.5">
      <div className="flex min-w-0 flex-col">
        <span className="truncate font-mono text-[11.5px] text-bone">{name}</span>
        <span className="truncate text-[10px] text-muted">{detail}</span>
      </div>
      <span
        className={cn(
          "h-5 w-9 rounded-full border p-0.5",
          enabled ? "border-brass/40 bg-brass/20" : "border-rule bg-ink/70",
        )}
        title={enabled ? "Available in this workspace flow" : "Not available in Playground"}
      >
        <span className={cn("block h-3.5 w-3.5 rounded-full transition", enabled ? "translate-x-3.5 bg-brass-2" : "bg-muted")} />
      </span>
    </div>
  );
}

function ToolAction({ name, detail, enabled }: { name: string; detail: string; enabled?: boolean }) {
  return (
    <button
      type="button"
      disabled={!enabled}
      className={cn(
        "rounded-md border px-2.5 py-2 text-left disabled:cursor-not-allowed disabled:opacity-60",
        enabled ? "border-brass/30 bg-brass/10 hover-elevate" : "border-rule bg-ink/40",
      )}
    >
      <div className="font-mono text-[11px] text-bone">{name}</div>
      <div className="mt-0.5 text-[10px] text-muted">{enabled ? detail : `${detail} · unavailable in Playground`}</div>
    </button>
  );
}

function ModeButton({
  active,
  onClick,
  icon,
  children,
}: {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "inline-flex h-6 items-center gap-1.5 rounded px-2 text-xs transition",
        active ? "bg-brass/15 text-brass-2" : "text-muted hover:text-bone",
      )}
    >
      {icon}
      {children}
    </button>
  );
}

function ComparePane({
  model,
  prompt,
  status,
  result,
}: {
  model: string;
  prompt: string;
  status: CompareRunResult["status"];
  result?: CompareRunResult;
}) {
  const statusLabel = status === "running"
    ? "running governed compare"
    : status === "done"
      ? "live result ready"
      : status === "error"
        ? result?.error ?? "compare unavailable"
        : prompt
          ? "ready to compare"
          : "send a prompt to compare";
  return (
    <div className="flex h-[460px] flex-col rounded-xl border border-rule bg-ink/40">
      <div className="border-b border-rule px-3 py-2">
        <div className="flex items-center justify-between gap-2">
          <span className="truncate text-[12.5px] text-bone">{model}</span>
          <span className="chip border-rule bg-ink/40 text-muted">compare</span>
        </div>
        <div className="mt-1 text-[10.5px] text-muted">{statusLabel}</div>
      </div>
      <div className="flex-1 overflow-auto px-3 py-3 text-[12.5px] leading-relaxed">
        <p className="text-muted">{prompt ? `Prompt: ${prompt}` : "Send a prompt to compare across connected models."}</p>
        {status === "running" && (
          <div className="mt-3 flex items-center gap-2 rounded-md border border-rule bg-ink-2/70 p-3 text-muted">
            <Loader2 className="h-4 w-4 animate-spin" />
            Waiting on live `/ai/complete` output.
          </div>
        )}
        {status === "error" && (
          <div className="mt-3 rounded-md border border-crimson/30 bg-crimson/10 p-3 text-crimson">
            {result?.error ?? "Compare execution failed for this model."}
          </div>
        )}
        {status === "done" && result?.responseText && (
          <>
            <div className="mt-3 whitespace-pre-wrap rounded-md border border-rule bg-ink-2/70 p-3 text-bone">
              {result.responseText}
            </div>
            <div className="mt-2 flex flex-wrap gap-1.5 text-[10.5px]">
              <span className="chip border-brass/40 bg-brass/10 text-brass-2">{result.provider}</span>
              {result.latencyMs != null && <span className="chip border-rule bg-ink/40 text-muted">{result.latencyMs} ms</span>}
              {result.outputTokens != null && <span className="chip border-rule bg-ink/40 text-muted">{result.outputTokens} out</span>}
              {result.costUsd && <span className="chip border-rule bg-ink/40 text-muted">{result.costUsd}</span>}
            </div>
          </>
        )}
        {status === "idle" && (
          <div className="mt-3 rounded-md border border-rule bg-ink-2/70 p-3 text-muted">
            Compare will execute honest, model-specific governed runs for both panes.
          </div>
        )}
      </div>
    </div>
  );
}

function SystemMessage({ content }: { content: string }) {
  return (
    <div className="flex items-start gap-3">
      <div className="mt-1 grid h-6 w-6 place-items-center rounded-md bg-white/[0.04] text-muted">
        <SlidersHorizontal className="h-3.5 w-3.5" />
      </div>
      <div className="flex-1 rounded-md border border-dashed border-rule bg-white/[0.02] px-3 py-2 text-[12px] text-muted">
        <span className="text-eyebrow mr-2">System</span>
        {content}
      </div>
    </div>
  );
}

function ChatBubble({
  turn,
  onCopy,
  onEdit,
  onRegenerate,
}: {
  turn: ConversationTurn;
  onCopy: () => void;
  onEdit: () => void;
  onRegenerate?: () => void;
}) {
  const user = turn.role === "user";
  return (
    <div className={cn("flex items-start gap-3", user && "justify-end")}>
      {!user && (
        <div className="mt-1 grid h-6 w-6 place-items-center rounded-md bg-brass/15 text-brass-2">
          <MessageSquare className="h-3.5 w-3.5" />
        </div>
      )}
      <div className={cn("max-w-[78%] flex-1", user && "flex flex-col items-end")}>
        <div
          className={cn(
            "rounded-2xl border px-4 py-3 text-[13px] leading-relaxed",
            user ? "border-brass/30 bg-brass/10 text-bone" : "border-rule bg-ink-2/70 text-bone",
          )}
        >
          <RichContent content={turn.content} />
        </div>
        {!user && (
          <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
            {turn.provider && <span className="chip border-brass/40 bg-brass/10 text-brass-2">{turn.provider}</span>}
            {turn.latency_ms && <span className="chip border-rule bg-ink/40 text-muted">{turn.latency_ms} ms</span>}
            {turn.cost_usd && <span className="chip border-rule bg-ink/40 text-muted">{turn.cost_usd}</span>}
            {turn.tokens && <span className="chip border-rule bg-ink/40 text-muted">{turn.tokens} out</span>}
            <span className="chip border-moss/30 bg-moss/10 text-moss">
              <Shield className="h-3 w-3" /> policy passed
            </span>
            <button className="ml-auto inline-flex items-center gap-1 text-[10px] text-muted hover:text-bone" onClick={onCopy} type="button">
              <Copy className="h-3 w-3" /> copy
            </button>
            <button className="inline-flex items-center gap-1 text-[10px] text-muted hover:text-bone" onClick={onEdit} type="button">
              <Pencil className="h-3 w-3" /> edit
            </button>
            {onRegenerate && (
              <button className="inline-flex items-center gap-1 text-[10px] text-muted hover:text-bone" onClick={onRegenerate} type="button">
                <RotateCcw className="h-3 w-3" /> regen
              </button>
            )}
          </div>
        )}
      </div>
      {user && (
        <div className="mt-1 grid h-6 w-6 place-items-center rounded-md bg-bone/10 font-display text-[10px] font-semibold text-bone">
          U
        </div>
      )}
    </div>
  );
}

function AssistantThinking() {
  return (
    <div className="flex items-start gap-3">
      <div className="mt-1 grid h-6 w-6 place-items-center rounded-md bg-brass/15 text-brass-2">
        <Loader2 className="h-3.5 w-3.5 animate-spin" />
      </div>
      <div className="rounded-2xl border border-rule bg-ink-2/70 px-4 py-3 text-[13px] text-muted">
        Generating...
      </div>
    </div>
  );
}

function RichContent({ content }: { content: string }) {
  const blocks = content.split(/(```[\s\S]*?```)/g);
  return (
    <div className="space-y-2">
      {blocks.map((block, idx) => {
        if (block.startsWith("```")) {
          const code = block.replace(/```(\w+)?\n?/, "").replace(/```$/, "");
          return (
            <pre key={idx} className="overflow-auto rounded-md border border-rule bg-ink p-3 font-mono text-[11.5px] leading-relaxed text-bone">
              {code}
            </pre>
          );
        }
        return (
          <p key={idx} className="whitespace-pre-wrap">
            {block.split(/(\*\*[^*]+\*\*)/g).map((part, partIdx) =>
              part.startsWith("**") ? (
                <strong key={partIdx} className="text-bone">
                  {part.slice(2, -2)}
                </strong>
              ) : (
                <span key={partIdx}>{part}</span>
              ),
            )}
          </p>
        );
      })}
    </div>
  );
}

function ModelFact({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-rule bg-ink/40 px-2 py-1.5">
      <div className="text-eyebrow">{label}</div>
      <div className="truncate font-mono text-[12px] text-bone">{value}</div>
    </div>
  );
}

function RangeControl({
  label,
  hint,
  value,
  min,
  max,
  step,
  current,
  onChange,
  disabled,
}: {
  label: string;
  hint: string;
  value: string;
  min: number;
  max: number;
  step: number;
  current: number;
  onChange: (value: number) => void;
  disabled?: boolean;
}) {
  return (
    <div>
      <div className="mb-1 flex items-end justify-between">
        <span className="text-[11.5px]">
          {label} <span className="text-muted">· {hint}</span>
        </span>
        <span className="font-mono text-[11px] text-bone">{value}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={current}
        onChange={(e) => onChange(Number(e.target.value))}
        disabled={disabled}
        className="w-full accent-[#e5b16e]"
      />
    </div>
  );
}

function ToggleRow({
  icon,
  label,
  checked,
  onChange,
  disabled,
}: {
  icon: React.ReactNode;
  label: string;
  checked: boolean;
  onChange?: (checked: boolean) => void;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={() => onChange?.(!checked)}
      className="flex w-full items-center justify-between rounded-md border border-rule bg-ink/40 px-2.5 py-1.5 text-left disabled:cursor-not-allowed disabled:opacity-70"
    >
      <span className="flex items-center gap-2 text-[11.5px]">
        {icon}
        {label}
      </span>
      <span className={cn("h-5 w-9 rounded-full border p-0.5", checked ? "border-brass/40 bg-brass/20" : "border-rule bg-ink/70")}>
        <span className={cn("block h-3.5 w-3.5 rounded-full transition", checked ? "translate-x-3.5 bg-brass-2" : "bg-muted")} />
      </span>
    </button>
  );
}

function TelemetryPanel({
  stats,
  conversationLength,
}: {
  stats: {
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
    reserve_debited?: number;
    billing_event_type?: string;
    pricing_tier?: string;
    free_evaluation_remaining?: number | null;
    cost_usd?: string;
    requested_provider?: string;
    requested_model?: string;
    fallback_triggered?: boolean;
    routing_reason?: string;
  };
  conversationLength: number;
}) {
  return (
    <div className="frame p-4">
      <div className="mb-3 flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.12em] text-muted">
        <Gauge className="h-3 w-3" /> Telemetry
      </div>
      <dl className="space-y-2.5 font-mono text-[12px]">
        <Stat label="request id" value={stats.request_id ?? "-"} mono />
        <Stat label="provider" value={stats.provider ?? "-"} />
        <Stat
          label="routing"
          value={stats.fallback_triggered ? `${stats.requested_provider ?? "primary"} -> ${stats.provider ?? "fallback"}` : "primary"}
        />
        <Stat label="model" value={stats.model ?? "-"} />
        <Stat label="runtime" value={stats.runtime_model_id ?? "-"} mono />
        <Stat label="input units" value={stats.prompt_tokens?.toString() ?? "-"} />
        <Stat label="output units" value={stats.completion_tokens?.toString() ?? "-"} />
        <Stat label="total units" value={stats.total_tokens?.toString() ?? "-"} />
        <Stat label="latency" value={stats.latency_ms ? `${stats.latency_ms} ms` : "-"} />
        <Stat label="billing event" value={stats.billing_event_type?.replace(/_/g, " ") ?? "-"} />
        <Stat label="pricing tier" value={stats.pricing_tier?.replace(/_/g, " ") ?? "-"} />
        <Stat label="reserve debit" value={(stats.reserve_debited ?? stats.tokens_deducted)?.toString() ?? "-"} />
        <Stat label="reserve balance" value={stats.wallet_balance?.toString() ?? "-"} />
        <Stat label="free runs left" value={stats.free_evaluation_remaining?.toString() ?? "-"} />
        <Stat label="audit hash" value={stats.audit_hash ? `${stats.audit_hash.slice(0, 12)}...` : "-"} mono />
        <Stat label="turns" value={conversationLength.toString()} />
      </dl>
    </div>
  );
}

function EventLogPanel({
  events,
  running,
  feedRef,
  eventCount,
}: {
  events: PipelineEvent[];
  running: boolean;
  feedRef: React.RefObject<HTMLDivElement>;
  eventCount: number;
}) {
  return (
    <div className="frame p-0">
      <header className="flex items-center justify-between border-b border-rule px-4 py-2">
        <div className="flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.12em] text-muted">
          <Zap className="h-3 w-3" /> Event log
        </div>
        <span className="chip border-rule bg-ink/40 text-bone-2">{eventCount}</span>
      </header>
      <div ref={feedRef} className="max-h-[520px] overflow-y-auto p-3 font-mono text-[11px]">
        {events.length === 0 ? (
          <div className="py-8 text-center text-muted">{running ? "Waiting on backend..." : "No events yet."}</div>
        ) : (
          <ul className="space-y-1.5">
            {events.map((event) => {
              const meta = EVENT_META[event.event] ?? { label: event.event, color: "text-bone-2", icon: "-" };
              return (
                <li key={event.id} className="flex items-start gap-2">
                  <span className={cn("w-3 shrink-0 text-center", meta.color)}>{meta.icon}</span>
                  <span className={cn("shrink-0 font-semibold", meta.color)}>{meta.label}</span>
                  <span className="ml-auto truncate text-muted">{compactPayload(event.data)}</span>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}

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
    "reserve_debit",
    "intended_provider",
    "actual_provider",
    "reason",
    "request_id",
    "message",
  ];
  for (const k of preferred) {
    if (k in data && data[k] != null) return `${k}=${String(data[k]).slice(0, 56)}`;
  }
  const first = keys[0]!;
  return `${first}=${String(data[first]).slice(0, 56)}`;
}
