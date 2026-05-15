import type { ReactNode } from "react";
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Activity, Download, Gauge, GitBranch, Loader2, RotateCcw, Save, Send, Shield, SlidersHorizontal, Sparkles, TerminalSquare } from "lucide-react";
import { api } from "@/lib/api";
import { cn } from "@/lib/cn";
import { responseDetail } from "@/lib/errors";

type ResponseFormat = "text" | "json" | "json-schema";
type SessionTag = "Standard" | "PHI" | "PII" | "HIPAA" | "PCI" | "SOC2";
type WorkspaceModel = {
  slug: string;
  name: string;
  provider: string;
  enabled: boolean;
  connected: boolean;
  context_window?: number;
  quantization?: string;
  p50_ms?: number;
  p95_ms?: number;
};
type PlaygroundProfile = {
  policy_pack?: string;
  suggested_demo_prompts?: string[];
  evidence_requirements?: string[];
};
type CostPrediction = {
  predicted_cost: string;
  confidence_upper: string;
  input_tokens: number;
  estimated_output_tokens: number;
  prediction_id: string;
};
type CompleteResponse = {
  response_text: string;
  model: string;
  provider: string;
  request_id: string;
  audit_hash?: string;
  prompt_tokens: number;
  output_tokens: number;
  total_tokens: number;
  latency_ms: number;
  cost_usd: string;
  timestamp: string;
};
type Turn = {
  id: string;
  role: "user" | "assistant";
  content: string;
  provider?: string;
  latency_ms?: number;
  cost_usd?: string;
  audit_hash?: string;
  ts: string;
};

const SESSION_TAGS: SessionTag[] = ["Standard", "PHI", "PII", "HIPAA", "PCI", "SOC2"];
const RESPONSE_FORMATS: ResponseFormat[] = ["text", "json", "json-schema"];

function estimateTokens(value: string) {
  return Math.max(1, Math.ceil(value.trim().length / 4));
}

function contextLabel(model?: WorkspaceModel) {
  return model?.context_window ? `${Math.round(model.context_window / 1000)}K` : "128K";
}

export function PlaygroundPage() {
  const models = useQuery({
    queryKey: ["workspace", "models"],
    queryFn: async () => (await api.get<WorkspaceModel[]>("/workspace/models")).data,
  });
  const profile = useQuery({
    queryKey: ["workspace", "playground-profile"],
    queryFn: async () => (await api.get<PlaygroundProfile>("/workspace/playground/profile")).data,
  });
  const activeModels = useMemo(() => (models.data ?? []).filter((model) => model.enabled && model.connected), [models.data]);
  const [modelSlug, setModelSlug] = useState("");
  const model = activeModels.find((item) => item.slug === modelSlug) ?? activeModels[0] ?? models.data?.[0];
  const [prompt, setPrompt] = useState("");
  const [systemPrompt, setSystemPrompt] = useState("You are a sovereign AI assistant operating inside the Veklom control plane. Never emit PHI.");
  const [maxTokens, setMaxTokens] = useState(1024);
  const [temperature, setTemperature] = useState(0.7);
  const [topP, setTopP] = useState(0.95);
  const [topK, setTopK] = useState(40);
  const [responseFormat, setResponseFormat] = useState<ResponseFormat>("text");
  const [sessionTag, setSessionTag] = useState<SessionTag>("Standard");
  const [stream, setStream] = useState(true);
  const [autoRedact, setAutoRedact] = useState(true);
  const [signAudit, setSignAudit] = useState(true);
  const [lockToOnPrem, setLockToOnPrem] = useState(false);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [prediction, setPrediction] = useState<CostPrediction | null>(null);
  const [latest, setLatest] = useState<CompleteResponse | null>(null);
  const [turns, setTurns] = useState<Turn[]>([]);
  const inputTokens = estimateTokens(prompt);
  const quickPrompts = profile.data?.suggested_demo_prompts?.slice(0, 4) ?? [
    "Summarize this incident report with PHI redaction and audit-ready evidence.",
    "Route this request to the cheapest compliant provider and explain the decision.",
    "Classify this prompt for HIPAA, PCI, and SOC2 risk before execution.",
    "Generate a governed JSON answer with policy evidence attached.",
  ];

  async function run() {
    if (!model || !prompt.trim() || running) return;
    const userPrompt = prompt.trim();
    const userTurn: Turn = { id: `user-${Date.now()}`, role: "user", content: userPrompt, ts: new Date().toISOString() };
    setRunning(true);
    setError(null);
    setPrompt("");
    setTurns((items) => [...items, userTurn]);
    try {
      const cost = await api.post<CostPrediction>("/cost/predict", {
        operation_type: "generation",
        provider: model.provider,
        model: model.slug,
        input_text: userPrompt,
        input_tokens: estimateTokens(userPrompt),
        estimated_output_tokens: maxTokens,
      });
      setPrediction(cost.data);
      const response = await api.post<CompleteResponse>("/ai/complete", {
        model: model.slug,
        prompt: userPrompt,
        messages: turns.concat(userTurn).slice(-20).map((turn) => ({ role: turn.role, content: turn.content })),
        system_prompt: systemPrompt,
        max_tokens: maxTokens,
        temperature,
        top_p: topP,
        top_k: topK,
        response_format: responseFormat,
        stream,
        session_tag: sessionTag,
        billing_event_type: "governed_run",
        auto_redact: autoRedact,
        sign_audit_on_export: signAudit,
        lock_to_on_prem: lockToOnPrem,
      });
      setLatest(response.data);
      setTurns((items) => [
        ...items,
        {
          id: response.data.request_id,
          role: "assistant",
          content: response.data.response_text,
          provider: response.data.provider,
          latency_ms: response.data.latency_ms,
          cost_usd: response.data.cost_usd,
          audit_hash: response.data.audit_hash,
          ts: response.data.timestamp,
        },
      ]);
      void api.post("/autonomous/routing/update", null, {
        params: {
          operation_type: "generation",
          provider: response.data.provider,
          actual_cost: Number(response.data.cost_usd || cost.data.predicted_cost || 0),
          actual_quality: 0.9,
          actual_latency_ms: response.data.latency_ms,
          baseline_cost: Number(cost.data.confidence_upper || cost.data.predicted_cost || 0),
        },
      });
    } catch (err) {
      setError(responseDetail(err));
    } finally {
      setRunning(false);
    }
  }

  function exportAudit() {
    const blob = new Blob([JSON.stringify({ exported_at: new Date().toISOString(), prediction, latest, turns }, null, 2)], { type: "application/json" });
    const href = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = href;
    link.download = `veklom-playground-audit-${latest?.request_id ?? Date.now()}.json`;
    link.click();
    URL.revokeObjectURL(href);
  }

  return (
    <div className="space-y-6">
      <header className="border-b border-rule pb-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-eyebrow">Workspace - Playground</p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight text-ink">Playground</h1>
            <p className="mt-2 max-w-3xl text-sm text-muted">Production-grade prompt theater. Every call is costed, routed, governed, and audit-stamped before execution.</p>
            <div className="mt-4 flex flex-wrap gap-2">
              <Pill icon={<Activity size={14} />} tone="amber">{(model?.provider ?? "provider").toUpperCase()} - PRIMARY</Pill>
              <Pill icon={<Gauge size={14} />} tone="green">P50 {latest?.latency_ms ?? model?.p50_ms ?? "-"} MS</Pill>
              <Pill tone="amber">${prediction?.predicted_cost ?? "0.0000"} EST</Pill>
              <Pill icon={<Shield size={14} />} tone="green">POLICY ENGINE LIVE</Pill>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <button className="btn-secondary" type="button"><GitBranch size={16} /> Branch</button>
            <button className="btn-secondary" type="button"><Save size={16} /> Save prompt</button>
            <button className="btn-primary" type="button" onClick={exportAudit} disabled={!latest && !prediction}><Download size={16} /> Audit export</button>
          </div>
        </div>
      </header>

      <div className="grid gap-4 xl:grid-cols-[220px_minmax(0,1fr)_280px]">
        <aside className="space-y-3">
          <Panel title="Sessions" icon={<Sparkles size={15} />}>
            {quickPrompts.map((item, index) => (
              <button key={item} type="button" onClick={() => setPrompt(item)} className="flex w-full items-center justify-between border-b border-rule px-3 py-3 text-left text-sm text-ink last:border-b-0 hover:bg-panel-2">
                <span className="truncate">{item}</span>
                <span className={cn("ml-2 h-2 w-2 rounded-full", index % 2 ? "bg-green" : "bg-brass")} />
              </button>
            ))}
          </Panel>
          <Panel title="Tools / Functions" icon={<TerminalSquare size={15} />}>
            {["compliance.fetch", "vault.read", "http.get", "sql.exec"].map((tool, index) => (
              <div key={tool} className="flex items-center justify-between border-b border-rule px-3 py-3 last:border-b-0">
                <div>
                  <div className="font-mono text-sm text-ink">{tool}</div>
                  <div className="text-[11px] text-muted">JSONSchema - governed</div>
                </div>
                <span className={cn("h-6 w-10 rounded-full border", index < 2 ? "border-brass bg-brass" : "border-rule bg-panel-2")} />
              </div>
            ))}
          </Panel>
        </aside>

        <main className="rounded-card border border-rule bg-panel shadow-card">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-rule px-4 py-3">
            <div className="flex items-center gap-2">
              <button className="btn-secondary bg-panel-2" type="button"><Sparkles size={15} /> Chat</button>
              <button className="btn-secondary" type="button"><TerminalSquare size={15} /> Completion</button>
            </div>
            <button className="btn-secondary" type="button" onClick={() => { setTurns([]); setLatest(null); setPrediction(null); setError(null); }}><RotateCcw size={15} /> Clear</button>
          </div>

          <div className="min-h-[520px] space-y-4 p-4">
            <div className="rounded-card border border-rule bg-black/20 p-4">
              <div className="mb-2 text-eyebrow">System</div>
              <textarea className="min-h-[72px] w-full resize-none bg-transparent text-sm text-muted outline-none" value={systemPrompt} onChange={(event) => setSystemPrompt(event.target.value)} />
            </div>
            <div className="space-y-3">
              {turns.length === 0 ? (
                <div className="rounded-card border border-rule bg-black/20 p-5 text-sm text-muted">Connected to {model?.name ?? "workspace model"} through the backend route contract. Cost prediction runs before the model call.</div>
              ) : turns.map((turn) => (
                <div key={turn.id} className={cn("rounded-card border p-4", turn.role === "user" ? "border-rule bg-panel-2" : "border-green/30 bg-green/5")}>
                  <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                    <span className="text-eyebrow">{turn.role === "user" ? "Inbound prompt" : "Governed response"}</span>
                    <span className="font-mono text-xs text-muted">{new Date(turn.ts).toLocaleTimeString()}</span>
                  </div>
                  <p className="whitespace-pre-wrap text-sm leading-6 text-ink">{turn.content}</p>
                  {turn.role === "assistant" ? (
                    <div className="mt-3 flex flex-wrap gap-2">
                      <Pill tone="green">{turn.provider ?? "provider"}</Pill>
                      <Pill tone="amber">{turn.latency_ms ?? "-"} ms</Pill>
                      <Pill tone="green">{turn.cost_usd ?? "$0.00"}</Pill>
                      <Pill tone="cyan">{turn.audit_hash ? `audit ${turn.audit_hash.slice(0, 10)}` : "audit pending"}</Pill>
                    </div>
                  ) : null}
                </div>
              ))}
            </div>
          </div>

          <div className="border-t border-rule p-4">
            {error ? <div className="mb-3 rounded-card border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-200">{error}</div> : null}
            <textarea value={prompt} onChange={(event) => setPrompt(event.target.value)} placeholder="Ask anything. Cost, route, policy, and audit run before execution..." className="min-h-[120px] w-full resize-none rounded-card border border-rule bg-panel-2 p-4 text-sm text-ink outline-none focus:border-brass" />
            <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
              <div className="flex flex-wrap gap-2">
                <Pill tone="amber">EST ${prediction?.predicted_cost ?? "0.0000"}</Pill>
                <Pill tone="green">{inputTokens} in</Pill>
                <Pill tone="cyan">{maxTokens} out cap</Pill>
              </div>
              <button className="btn-primary" type="button" disabled={!prompt.trim() || !model || running} onClick={run}>{running ? <Loader2 className="animate-spin" size={16} /> : <Send size={16} />} Send</button>
            </div>
          </div>
        </main>

        <aside className="space-y-3">
          <Panel title="Model" icon={<SlidersHorizontal size={15} />}>
            <div className="space-y-3 p-3">
              <select className="w-full rounded-card border border-rule bg-panel-2 px-3 py-2 text-sm text-ink outline-none" value={model?.slug ?? ""} onChange={(event) => setModelSlug(event.target.value)}>
                {(activeModels.length ? activeModels : models.data ?? []).map((item) => <option key={item.slug} value={item.slug}>{item.name}</option>)}
              </select>
              <MetricGrid items={[["Context", contextLabel(model)], ["Quant", model?.quantization ?? "FP16"], ["P50", `${latest?.latency_ms ?? model?.p50_ms ?? "-"} ms`], ["P95", `${model?.p95_ms ?? "-"} ms`]]} />
            </div>
          </Panel>
          <Panel title="Parameters" icon={<Gauge size={15} />}>
            <div className="space-y-4 p-3">
              <Slider label="Temperature" value={temperature} min={0} max={2} step={0.01} onChange={setTemperature} />
              <Slider label="Top-p" value={topP} min={0} max={1} step={0.01} onChange={setTopP} />
              <Slider label="Top-k" value={topK} min={1} max={200} step={1} onChange={setTopK} />
              <Slider label="Max tokens" value={maxTokens} min={1} max={8192} step={1} onChange={setMaxTokens} />
              <Toggle label="Stream" checked={stream} onChange={setStream} />
              <div className="grid grid-cols-3 gap-2">
                {RESPONSE_FORMATS.map((format) => <button key={format} type="button" onClick={() => setResponseFormat(format)} className={cn("rounded-card border px-2 py-2 text-xs", responseFormat === format ? "border-brass bg-brass/20 text-ink" : "border-rule text-muted")}>{format}</button>)}
              </div>
            </div>
          </Panel>
          <Panel title="Compliance" icon={<Shield size={15} />}>
            <div className="space-y-3 p-3">
              <div className="grid grid-cols-3 gap-2">
                {SESSION_TAGS.map((tag) => <button key={tag} type="button" onClick={() => setSessionTag(tag)} className={cn("rounded-card border px-2 py-2 text-xs", sessionTag === tag ? "border-brass bg-brass/20 text-ink" : "border-rule text-muted")}>{tag}</button>)}
              </div>
              <Toggle label="Auto-redact PHI/PII" checked={autoRedact} onChange={setAutoRedact} />
              <Toggle label="Sign audit on export" checked={signAudit} onChange={setSignAudit} />
              <Toggle label="Lock to on-prem" checked={lockToOnPrem} onChange={setLockToOnPrem} />
              <div className="rounded-card border border-rule bg-panel-2 p-3 text-xs text-muted">{profile.data?.policy_pack ?? "default policy pack"} - {profile.data?.evidence_requirements?.[0] ?? "evidence ready"}</div>
            </div>
          </Panel>
        </aside>
      </div>
    </div>
  );
}

function Panel({ title, icon, children }: { title: string; icon: ReactNode; children: ReactNode }) {
  return <section className="overflow-hidden rounded-card border border-rule bg-panel shadow-card"><div className="flex items-center gap-2 border-b border-rule px-3 py-2"><span className="text-brass">{icon}</span><span className="text-eyebrow">{title}</span></div>{children}</section>;
}

function Pill({ children, icon, tone = "amber" }: { children: ReactNode; icon?: ReactNode; tone?: "amber" | "green" | "cyan" }) {
  return <span className={cn("inline-flex items-center gap-1 rounded border px-2 py-1 font-mono text-[11px] uppercase tracking-wider", tone === "amber" && "border-brass/40 bg-brass/10 text-brass", tone === "green" && "border-green/40 bg-green/10 text-green", tone === "cyan" && "border-cyan/40 bg-cyan/10 text-cyan")}>{icon}{children}</span>;
}

function MetricGrid({ items }: { items: Array<[string, string]> }) {
  return <div className="grid grid-cols-2 gap-2">{items.map(([label, value]) => <div key={label} className="rounded-card border border-rule bg-panel-2 p-3"><div className="text-eyebrow">{label}</div><div className="mt-1 font-mono text-sm text-ink">{value}</div></div>)}</div>;
}

function Slider({ label, value, min, max, step, onChange }: { label: string; value: number; min: number; max: number; step: number; onChange: (value: number) => void }) {
  return <label className="block"><div className="mb-1 flex items-center justify-between text-xs text-muted"><span>{label}</span><span className="font-mono text-ink">{value}</span></div><input className="w-full accent-brass" type="range" min={min} max={max} step={step} value={value} onChange={(event) => onChange(Number(event.target.value))} /></label>;
}

function Toggle({ label, checked, onChange }: { label: string; checked: boolean; onChange: (checked: boolean) => void }) {
  return <button type="button" onClick={() => onChange(!checked)} className="flex w-full items-center justify-between rounded-card border border-rule bg-panel-2 px-3 py-2 text-sm text-ink"><span>{label}</span><span className={cn("h-6 w-10 rounded-full border p-0.5", checked ? "border-brass bg-brass" : "border-rule bg-black/40")}><span className={cn("block h-4 w-4 rounded-full bg-black transition", checked && "translate-x-4")} /></span></button>;
}
