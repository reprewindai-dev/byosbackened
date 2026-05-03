import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Activity,
  AlertTriangle,
  CircleStop,
  Download,
  Gauge,
  Play,
  Shield,
  Sparkles,
  Zap,
} from "lucide-react";
import { resolveApiBase } from "@/lib/api";
import { cn } from "@/lib/cn";

type Vertical = "default" | "legal" | "medical" | "finance" | "agency" | "infrastructure";

interface PipelineEvent {
  id: string;
  event: string;
  data: Record<string, unknown>;
  ts: number;
}

const VERTICALS: { value: Vertical; label: string; hint: string }[] = [
  { value: "default", label: "General", hint: "Broad control-plane demo" },
  { value: "legal", label: "Legal", hint: "Privacy-first legal ops" },
  { value: "medical", label: "Medical", hint: "HIPAA-aware clinical ops" },
  { value: "finance", label: "Finance", hint: "SOC2 / PCI-aware" },
  { value: "agency", label: "Agency", hint: "Multi-tenant copilot" },
  { value: "infrastructure", label: "Infrastructure", hint: "SNMP / Modbus bridge" },
];

const SAMPLE_PROMPTS: Record<Vertical, string> = {
  default: "Summarize why sovereignty matters for regulated AI workloads in three bullets.",
  legal: "Draft a privacy-first intake workflow for handling PII in client matters.",
  medical: "Explain the PHI controls you'd enforce on an intake chatbot.",
  finance: "Outline the SOC2 audit artifacts you'd generate for each AI decision.",
  agency: "Describe tenant isolation for a 50-client agency running shared models.",
  infrastructure: "Translate a stream of SNMP traps into a governed AI incident triage.",
};

const EVENT_META: Record<string, { label: string; color: string; icon: string }> = {
  request_received: { label: "Request received", color: "text-bone", icon: "◆" },
  zero_trust_check: { label: "Zero-trust check", color: "text-electric", icon: "🛡" },
  rate_limit_check: { label: "Rate limit", color: "text-electric", icon: "⏱" },
  token_budget_check: { label: "Token budget", color: "text-electric", icon: "◉" },
  circuit_breaker_check: { label: "Circuit breaker", color: "text-amber", icon: "↯" },
  provider_selected: { label: "Provider chosen", color: "text-brass-2", icon: "⇨" },
  ollama_attempt: { label: "Ollama attempt", color: "text-brass-2", icon: "▶" },
  ollama_unavailable: { label: "Ollama unavailable", color: "text-crimson", icon: "✕" },
  circuit_breaker_opened: { label: "Breaker opened", color: "text-crimson", icon: "⚠" },
  groq_fallback: { label: "Groq fallback", color: "text-violet", icon: "↪" },
  redis_memory_check: { label: "Memory check", color: "text-electric", icon: "◎" },
  token_delta: { label: "Token", color: "text-moss", icon: "·" },
  response_complete: { label: "Response complete", color: "text-moss", icon: "✓" },
  audit_written: { label: "Audit written", color: "text-moss", icon: "✓" },
  cost_recorded: { label: "Cost recorded", color: "text-moss", icon: "✓" },
  done: { label: "Done", color: "text-moss", icon: "●" },
  error: { label: "Error", color: "text-crimson", icon: "✕" },
};

export function PlaygroundPage() {
  const [vertical, setVertical] = useState<Vertical>("default");
  const [prompt, setPrompt] = useState(SAMPLE_PROMPTS.default);
  const [forceFallback, setForceFallback] = useState(false);
  const [running, setRunning] = useState(false);
  const [events, setEvents] = useState<PipelineEvent[]>([]);
  const [responseText, setResponseText] = useState("");
  const [stats, setStats] = useState<{
    provider?: string;
    model?: string;
    prompt_tokens?: number;
    completion_tokens?: number;
    latency_ms?: number;
    trace_id?: string;
    audit_hash?: string;
  }>({});
  const [error, setError] = useState<string | null>(null);
  const eventSrcRef = useRef<EventSource | null>(null);
  const feedRef = useRef<HTMLDivElement>(null);

  const apiBase = resolveApiBase();

  const handleVerticalChange = (v: Vertical) => {
    setVertical(v);
    if (prompt === SAMPLE_PROMPTS[vertical]) setPrompt(SAMPLE_PROMPTS[v]);
  };

  const stop = useCallback(() => {
    eventSrcRef.current?.close();
    eventSrcRef.current = null;
    setRunning(false);
  }, []);

  const run = useCallback(() => {
    if (running) return;
    setEvents([]);
    setResponseText("");
    setStats({});
    setError(null);
    setRunning(true);

    const url = new URL(`${apiBase}/api/v1/demo/pipeline/stream`, window.location.origin);
    url.searchParams.set("prompt", prompt.slice(0, 800));
    url.searchParams.set("vertical", vertical);
    if (forceFallback) url.searchParams.set("force_fallback", "true");

    const es = new EventSource(url.toString());
    eventSrcRef.current = es;

    const handle = (evt: MessageEvent, name: string) => {
      try {
        const data = JSON.parse(evt.data);
        setEvents((prev) => [
          ...prev,
          { id: `${name}-${prev.length}`, event: name, data, ts: Date.now() },
        ]);
        if (name === "token_delta" && typeof data.text === "string") {
          setResponseText((t) => t + data.text);
        }
        if (name === "provider_selected" || name === "groq_fallback") {
          setStats((s) => ({
            ...s,
            provider: String(data.provider ?? s.provider ?? ""),
            model: String(data.model ?? s.model ?? ""),
            trace_id: String(data.trace_id ?? s.trace_id ?? ""),
          }));
        }
        if (name === "response_complete") {
          setStats((s) => ({
            ...s,
            prompt_tokens: Number(data.prompt_tokens ?? s.prompt_tokens ?? 0),
            completion_tokens: Number(data.completion_tokens ?? s.completion_tokens ?? 0),
            latency_ms: Number(data.latency_ms ?? s.latency_ms ?? 0),
          }));
        }
        if (name === "audit_written" && typeof data.audit_hash === "string") {
          setStats((s) => ({ ...s, audit_hash: data.audit_hash as string }));
        }
        if (name === "done" || name === "error") {
          stop();
          if (name === "error") setError(String(data.detail ?? data.message ?? "Stream failed"));
        }
      } catch (e) {
        console.warn("malformed SSE frame", name, evt.data, e);
      }
    };

    const names = Object.keys(EVENT_META);
    for (const n of names) es.addEventListener(n, (e) => handle(e as MessageEvent, n));

    es.onerror = () => {
      if (es.readyState === EventSource.CLOSED) {
        setError((prev) => prev ?? "Stream closed unexpectedly. The backend may be offline or rate-limiting.");
      }
      stop();
    };
  }, [apiBase, forceFallback, prompt, running, stop, vertical]);

  useEffect(() => {
    return () => stop();
  }, [stop]);

  useEffect(() => {
    if (feedRef.current) feedRef.current.scrollTop = feedRef.current.scrollHeight;
  }, [events.length]);

  const eventCount = events.length;
  const tokenCount = useMemo(() => events.filter((e) => e.event === "token_delta").length, [events]);

  const exportAudit = () => {
    const blob = new Blob(
      [
        JSON.stringify(
          {
            exported_at: new Date().toISOString(),
            trace_id: stats.trace_id,
            vertical,
            prompt,
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
    a.download = `veklom-audit-${stats.trace_id ?? Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(href);
  };

  return (
    <div className="mx-auto w-full max-w-7xl space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="mb-1 font-mono text-[11px] uppercase tracking-[0.15em] text-muted">
            Workspace · Playground
          </div>
          <h1 className="text-3xl font-semibold tracking-tight">Governed execution theater</h1>
          <p className="mt-2 max-w-2xl text-sm text-bone-2">
            Every prompt passes through zero-trust, rate limits, token budget, circuit breaker, provider selection,
            memory, audit, and cost recording — before a single token leaves your perimeter. Watch it happen.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <span className="v-chip v-chip-ok">
              <span className="h-1.5 w-1.5 animate-pulse-soft rounded-full bg-moss" />
              live SSE · <span className="font-mono">/api/v1/demo/pipeline/stream</span>
            </span>
            <span className="v-chip">no auth required</span>
            <span className="v-chip">rate-limited 5/min</span>
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
            <div className="mb-2 font-mono text-[11px] uppercase tracking-[0.12em] text-muted">
              Circuit breaker
            </div>
            <label className="flex items-start gap-3 rounded-lg border border-rule-2 bg-white/[0.02] p-3">
              <input
                type="checkbox"
                checked={forceFallback}
                onChange={(e) => setForceFallback(e.target.checked)}
                className="mt-0.5 accent-brass"
              />
              <div className="flex-1">
                <div className="text-[13px] font-medium text-bone">Force fallback</div>
                <div className="mt-1 text-[11px] leading-relaxed text-muted">
                  Simulate Ollama outage — exercises the circuit breaker and routes through Groq fallback.
                </div>
              </div>
            </label>
          </div>

          <div className="v-card p-4">
            <div className="mb-2 flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.12em] text-muted">
              <Shield className="h-3 w-3" /> Governance active
            </div>
            <ul className="space-y-1.5 font-mono text-[11px]">
              {[
                "Zero-trust verification",
                "IP rate-limit (5 / 60s)",
                "Token budget guard",
                "Circuit breaker w/ Groq fallback",
                "Ephemeral Redis memory (60s TTL)",
                "Tamper-evident audit write",
                "Cost ledger entry",
              ].map((s) => (
                <li key={s} className="flex items-start gap-2 text-bone-2">
                  <span className="mt-0.5 text-moss">✓</span>
                  {s}
                </li>
              ))}
            </ul>
          </div>
        </aside>

        <section className="space-y-4">
          <div className="v-card p-4">
            <div className="mb-2 flex items-center justify-between">
              <label htmlFor="prompt" className="v-label mb-0">
                Prompt
              </label>
              <span className="font-mono text-[10px] text-muted">{prompt.length} / 800</span>
            </div>
            <textarea
              id="prompt"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value.slice(0, 800))}
              rows={4}
              className="v-input min-h-[96px] resize-y font-mono text-[13px] leading-relaxed"
              placeholder="What would you like the governed control plane to answer…"
              disabled={running}
            />
            <div className="mt-3 flex items-center justify-between">
              <div className="flex gap-2">
                {!running ? (
                  <button className="v-btn-primary" onClick={run} disabled={!prompt.trim()}>
                    <Play className="h-4 w-4" /> Run through pipeline
                  </button>
                ) : (
                  <button className="v-btn-ghost text-crimson" onClick={stop}>
                    <CircleStop className="h-4 w-4" /> Stop stream
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
              </div>
              <div className="flex gap-2 font-mono text-[11px]">
                <span className="v-chip">
                  <Activity className="h-3 w-3" /> {eventCount} events
                </span>
                <span className="v-chip">
                  <Sparkles className="h-3 w-3" /> {tokenCount} tokens
                </span>
              </div>
            </div>
            {error && (
              <div className="mt-3 flex items-start gap-2 rounded-md border border-crimson/30 bg-crimson/10 px-3 py-2 text-[12px] text-crimson">
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}
          </div>

          <div className="v-card p-0">
            <header className="flex items-center justify-between border-b border-rule px-4 py-2">
              <div className="font-mono text-[11px] uppercase tracking-[0.12em] text-muted">Response</div>
              {stats.provider && (
                <span className="v-chip v-chip-brass font-mono">
                  {stats.provider} · {stats.model ?? "—"}
                </span>
              )}
            </header>
            <div className="min-h-[180px] whitespace-pre-wrap p-4 font-mono text-[13px] leading-relaxed text-bone">
              {responseText || (
                <span className="text-muted">
                  {running ? "Streaming…" : "Click “Run through pipeline” to stream a response."}
                </span>
              )}
              {running && <span className="ml-0.5 inline-block h-4 w-2 animate-pulse bg-brass" />}
            </div>
          </div>
        </section>

        <aside className="space-y-4">
          <div className="v-card p-4">
            <div className="mb-3 flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.12em] text-muted">
              <Gauge className="h-3 w-3" /> Telemetry
            </div>
            <dl className="space-y-2.5 font-mono text-[12px]">
              <Stat label="trace_id" value={stats.trace_id ?? "—"} mono />
              <Stat label="provider" value={stats.provider ?? "—"} />
              <Stat label="model" value={stats.model ?? "—"} />
              <Stat label="prompt tokens" value={stats.prompt_tokens?.toString() ?? "—"} />
              <Stat label="completion tokens" value={stats.completion_tokens?.toString() ?? "—"} />
              <Stat label="latency" value={stats.latency_ms ? `${stats.latency_ms} ms` : "—"} />
              <Stat label="audit hash" value={stats.audit_hash ? stats.audit_hash.slice(0, 12) + "…" : "—"} mono />
            </dl>
          </div>

          <div className="v-card p-0">
            <header className="flex items-center justify-between border-b border-rule px-4 py-2">
              <div className="flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.12em] text-muted">
                <Zap className="h-3 w-3" /> Event log
              </div>
              <span className="v-chip font-mono">{eventCount}</span>
            </header>
            <div
              ref={feedRef}
              className="max-h-[520px] overflow-y-auto p-3 font-mono text-[11px]"
            >
              {events.length === 0 ? (
                <div className="py-8 text-center text-muted">
                  {running ? "Waiting on first event…" : "No events yet."}
                </div>
              ) : (
                <ul className="space-y-1.5">
                  {events.map((e) => {
                    const meta = EVENT_META[e.event] ?? { label: e.event, color: "text-bone-2", icon: "·" };
                    const isToken = e.event === "token_delta";
                    return (
                      <li key={e.id} className={cn("flex items-start gap-2", isToken && "opacity-60")}>
                        <span className={cn("w-3 shrink-0 text-center", meta.color)}>{meta.icon}</span>
                        <span className={cn("shrink-0 font-semibold", meta.color)}>{meta.label}</span>
                        {!isToken && (
                          <span className="ml-auto truncate text-muted">
                            {compactPayload(e.data)}
                          </span>
                        )}
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

function Stat({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <dt className="text-muted">{label}</dt>
      <dd className={cn("truncate text-right text-bone", mono && "font-mono")}>{value}</dd>
    </div>
  );
}

function compactPayload(data: Record<string, unknown>): string {
  const keys = Object.keys(data);
  if (!keys.length) return "";
  const preferred = ["provider", "model", "state", "hits", "tokens", "latency_ms", "detail", "message"];
  for (const k of preferred) {
    if (k in data) return `${k}=${String(data[k]).slice(0, 40)}`;
  }
  const first = keys[0]!;
  return `${first}=${String(data[first]).slice(0, 40)}`;
}
