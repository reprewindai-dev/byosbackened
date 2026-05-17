import { useState, useEffect, useRef, useCallback } from "react";
import { Send, Code, FileDown, RotateCcw, Loader2, Copy } from "lucide-react";
import { api, rawApi } from "@/lib/api";

const DEFAULT_MODELS = ["Llama 3.1 70B Instruct"];

interface ChatMessage {
  role: string;
  content: string;
  meta?: string;
}

function genConvId() {
  return `conv_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

const SESSIONS = [
  { name: "PHI-safe summary", tokens: "3k" },
  { name: "Risk classifier...", tokens: "12k" },
  { name: "Legal redactor v3", tokens: "1h" },
  { name: "Pricing lookup tool", tokens: "2h" },
];

const PROMPT_LIB = [
  { name: "soc2.evidence.collect", version: "3" },
  { name: "phi.summarize.json", version: "7" },
  { name: "outbound.public.policy", version: "2" },
  { name: "code.repair.fim", version: "1" },
];

const TOOLS = [
  { name: "compliance.fetch", schema: "JSONSchema", enabled: true },
  { name: "vault.read", schema: "JSONSchema", enabled: true },
  { name: "http.get", schema: "JSONSchema", enabled: false },
  { name: "sql.exec", schema: "JSONSchema", enabled: false },
];

const COMPLIANCE_TAGS = ["Standard", "PHI", "PII", "HIPAA", "PCI", "SOC2"];

export function PlaygroundPage() {
  const [prompt, setPrompt] = useState("");
  const [models, setModels] = useState<string[]>(DEFAULT_MODELS);
  const [model, setModel] = useState(DEFAULT_MODELS[0]);
  const [convId, setConvId] = useState(genConvId);
  const [sending, setSending] = useState(false);
  const [temperature, setTemperature] = useState(0.70);
  const [topP, setTopP] = useState(0.95);
  const [maxTokens, setMaxTokens] = useState(1024);
  const [stream, setStream] = useState(true);
  const [complianceTag, setComplianceTag] = useState("Standard");
  const [messages, setMessages] = useState<ChatMessage[]>([
    { role: "system", content: "You are a sovereign AI assistant operating inside the Veklom control plane. Never emit PHI." },
  ]);
  const chatRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    (async () => {
      try {
        const results = await Promise.allSettled([
          api.get("/workspace/models").then(r => r.data),
          rawApi.get("/status").then(r => r.data),
        ]);
        if (results[0].status === "fulfilled") {
          const wm = results[0].value;
          const modelList = Array.isArray(wm) ? wm.map((m: { id?: string; name?: string }) => m.id || m.name || "").filter(Boolean) : wm?.models?.map((m: { id?: string; name?: string }) => m.id || m.name || "").filter(Boolean) || [];
          if (modelList.length) { setModels(modelList); setModel(modelList[0]); }
        }
        if (results[1].status === "fulfilled") {
          const data = results[1].value;
          if (data?.llm_models_available?.length) {
            setModels(data.llm_models_available);
            setModel(data.llm_model || data.llm_models_available[0]);
          }
        }
      } catch { /* fallback */ }
    })();
  }, []);

  useEffect(() => {
    chatRef.current?.scrollTo({ top: chatRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const onSend = useCallback(async () => {
    if (!prompt.trim() || sending) return;
    const userMsg = prompt;
    setPrompt("");
    setMessages((m) => [...m, { role: "user", content: userMsg }]);
    setSending(true);

    try {
      const { data } = await rawApi.post("/v1/exec", {
        prompt: userMsg,
        model,
        conversation_id: convId,
        use_memory: true,
        temperature,
        max_tokens: maxTokens,
      });
      const meta = [
        data.model || model,
        data.provider || "—",
        data.latency_ms ? `${data.latency_ms}ms` : null,
        data.total_tokens ? `${data.total_tokens} tok` : null,
      ].filter(Boolean).join(" · ");
      setMessages((m) => [...m, { role: "assistant", content: data.response || "(empty response)", meta }]);
    } catch (err: unknown) {
      const axErr = err as { response?: { data?: { detail?: string }; status?: number }; message?: string };
      const detail = axErr.response?.data?.detail || axErr.message || "Inference failed";
      setMessages((m) => [...m, { role: "assistant", content: `Error: ${detail}` }]);
    } finally {
      setSending(false);
    }
  }, [prompt, model, convId, sending, temperature, maxTokens]);

  function clearChat() {
    setMessages([{ role: "system", content: "You are a sovereign AI assistant operating inside the Veklom control plane. Never emit PHI." }]);
    setConvId(genConvId());
  }

  return (
    <div className="flex h-full flex-col animate-fade-in">
      {/* Header */}
      <div className="mb-4 flex items-start justify-between">
        <div>
          <p className="v-section-label">Workspace · Playground</p>
          <h1 className="mt-1 text-xl font-bold text-bone">Playground</h1>
          <p className="mt-1 text-xs text-muted">Production-grade prompt theater. Every call is policed, routed, costed, and audit-stamped before a single token is generated.</p>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <span className="rounded bg-amber/15 px-2 py-0.5 font-mono text-[9px] font-semibold text-amber">Hetzner · Primary</span>
            <span className="rounded bg-moss/15 px-1.5 py-0.5 font-mono text-[9px] text-moss">P50 96 ms</span>
            <span className="font-mono text-[9px] text-muted">$0.0001 Session · 38 Tok</span>
            <span className="font-mono text-[9px] text-muted">· {complianceTag}</span>
          </div>
          <div className="mt-1.5 flex items-center gap-2">
            <span className="rounded bg-amber/10 px-1.5 py-0.5 text-[8px] font-mono text-amber">Auto-Redact</span>
            <span className="rounded bg-moss/10 px-1.5 py-0.5 text-[8px] font-mono text-moss">Policy Engine Live</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button className="flex items-center gap-1.5 rounded-md border border-rule px-2.5 py-1.5 text-xs text-muted hover:text-bone"><Code className="h-3.5 w-3.5" /> View code</button>
          <button className="flex items-center gap-1.5 rounded-md border border-rule px-2.5 py-1.5 text-xs text-muted hover:text-bone">Branch</button>
          <button className="flex items-center gap-1.5 rounded-md border border-rule px-2.5 py-1.5 text-xs text-muted hover:text-bone">Save prompt</button>
          <button className="flex items-center gap-1.5 rounded-md border border-amber/30 bg-amber/10 px-2.5 py-1.5 text-xs text-amber"><FileDown className="h-3.5 w-3.5" /> Audit export</button>
        </div>
      </div>

      {/* 3-column layout */}
      <div className="flex flex-1 gap-4 overflow-hidden">
        {/* Left panel */}
        <div className="w-56 shrink-0 space-y-4 overflow-y-auto">
          {/* Sessions */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="font-mono text-[9px] uppercase text-muted">Sessions</span>
              <span className="text-[9px] text-brass cursor-pointer">+ New</span>
            </div>
            <div className="space-y-1">
              {SESSIONS.map((s, i) => (
                <div key={s.name} className={`flex items-center justify-between rounded px-2 py-1.5 text-xs cursor-pointer ${i === 0 ? "bg-brass/10 text-bone" : "text-muted hover:bg-white/[0.03]"}`}>
                  <span className="truncate">{s.name}</span>
                  <span className="font-mono text-[9px] text-muted-2">{s.tokens}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Prompt Library */}
          <div>
            <span className="font-mono text-[9px] uppercase text-muted">Prompt Library</span>
            <div className="mt-2 space-y-1">
              {PROMPT_LIB.map((p) => (
                <div key={p.name} className="flex items-center justify-between rounded px-2 py-1.5 text-xs text-muted hover:bg-white/[0.03] cursor-pointer">
                  <span className="truncate font-mono text-[10px]">{p.name}</span>
                  <span className="font-mono text-[8px] text-muted-2">v{p.version}</span>
                </div>
              ))}
            </div>
            <p className="mt-2 px-2 font-mono text-[8px] text-muted/60">Versioned · diffable · JSON / YAML import-export</p>
          </div>

          {/* Tools */}
          <div>
            <span className="font-mono text-[9px] uppercase text-muted">Tools / Functions</span>
            <div className="mt-2 space-y-1.5">
              {TOOLS.map((t) => (
                <div key={t.name} className="flex items-center justify-between rounded px-2 py-1.5">
                  <div>
                    <span className="text-xs font-mono text-bone">{t.name}</span>
                    <p className="text-[8px] text-muted">{t.schema} · mockable</p>
                  </div>
                  <div className={`h-4 w-7 rounded-full ${t.enabled ? "bg-amber" : "bg-ink-3 border border-rule"} relative`}>
                    <div className={`absolute top-0.5 h-3 w-3 rounded-full bg-white transition-all ${t.enabled ? "left-3.5" : "left-0.5"}`} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Center - Chat */}
        <div className="flex flex-1 flex-col overflow-hidden">
          {/* Chat tabs */}
          <div className="mb-2 flex items-center gap-4 border-b border-rule pb-2">
            <button className="rounded px-2 py-1 text-xs font-medium bg-brass/10 text-brass">Chat</button>
            <button className="text-xs text-muted hover:text-bone">Completion</button>
            <span className="ml-auto text-[9px] text-muted font-mono">{model} · 128K ctx · Compare off · Clear</span>
          </div>

          {/* Messages */}
          <div ref={chatRef} className="flex-1 overflow-y-auto space-y-4 pr-2">
            {messages.map((msg, i) => (
              <div key={i} className={`flex gap-3 ${msg.role === "user" ? "justify-end" : ""}`}>
                {msg.role !== "user" && (
                  <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-ink-3 border border-rule">
                    {msg.role === "system" ? (
                      <span className="text-[9px] text-muted">SYS</span>
                    ) : (
                      <svg viewBox="0 0 32 32" className="h-3.5 w-3.5">
                        <path d="M16 4 L6 24 L10 24 L16 13 L22 24 L26 24 Z" fill="#e5a832" />
                      </svg>
                    )}
                  </div>
                )}
                <div className={`max-w-[80%] rounded-lg px-3 py-2 ${msg.role === "user" ? "bg-brass/15 text-bone" : "bg-ink-3 border border-rule/50 text-bone"}`}>
                  <p className="text-xs whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                  {msg.meta && (
                    <div className="mt-2 flex items-center gap-2 border-t border-rule/40 pt-2">
                      <span className="rounded bg-amber/10 px-1.5 py-0.5 font-mono text-[8px] text-amber">Hetzner · Primary</span>
                      <span className="rounded bg-moss/10 px-1 py-0.5 font-mono text-[8px] text-moss">Policy Passed</span>
                      <span className="font-mono text-[8px] text-muted">{msg.meta}</span>
                      <button className="ml-auto"><Copy className="h-3 w-3 text-muted/50 hover:text-bone" /></button>
                    </div>
                  )}
                </div>
              </div>
            ))}
            {sending && (
              <div className="flex gap-3">
                <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-ink-3 border border-rule">
                  <Loader2 className="h-3.5 w-3.5 animate-spin text-amber" />
                </div>
                <div className="rounded-lg bg-ink-3 border border-rule/50 px-3 py-2 text-xs text-muted">Thinking...</div>
              </div>
            )}
          </div>

          {/* Input + capabilities */}
          <div className="mt-3 flex items-center gap-2 text-[9px] text-muted">
            <button className="rounded border border-rule px-2 py-0.5 hover:text-bone">PHI-safe summarization</button>
            <button className="rounded border border-rule px-2 py-0.5 hover:text-bone">Multi-step function call</button>
            <button className="rounded border border-rule px-2 py-0.5 hover:text-bone">Policy-bound rewrite</button>
            <button className="rounded border border-rule px-2 py-0.5 hover:text-bone">Code repair (FIM)</button>
          </div>
          <div className="mt-2 flex gap-2">
            <input
              type="text"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && onSend()}
              placeholder="Ask anything, ⌘ + Enter to send..."
              className="v-input flex-1 text-xs"
              disabled={sending}
            />
            <button onClick={onSend} disabled={sending} className="v-btn-primary px-3">
              {sending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
            </button>
          </div>
          {/* Status bar */}
          <div className="mt-2 flex items-center gap-3 font-mono text-[8px] text-muted-2">
            <span>EST</span>
            <span>$0.0003 0.00070/Tok</span>
            <span>~0</span>
            <span>· policy: outbound.public.v3</span>
            <span>· Tok ↗</span>
            <span>· Tools</span>
            <span>· JSON</span>
            <button onClick={clearChat} className="ml-auto flex items-center gap-1 text-brass hover:text-brass-2">
              <RotateCcw className="h-2.5 w-2.5" /> Send
            </button>
          </div>
        </div>

        {/* Right panel */}
        <div className="w-52 shrink-0 space-y-4 overflow-y-auto">
          {/* Model */}
          <div>
            <span className="font-mono text-[9px] uppercase text-muted">Model</span>
            <select value={model} onChange={(e) => setModel(e.target.value)} className="v-input mt-1.5 w-full text-[10px]">
              {models.map((m) => <option key={m} value={m}>{m}</option>)}
            </select>
            <div className="mt-2 grid grid-cols-2 gap-2">
              <div className="rounded border border-rule bg-ink-3/50 p-2">
                <p className="font-mono text-[8px] text-muted">Context</p>
                <p className="font-mono text-xs text-bone">128K</p>
              </div>
              <div className="rounded border border-rule bg-ink-3/50 p-2">
                <p className="font-mono text-[8px] text-muted">Quant</p>
                <p className="font-mono text-xs text-bone">FP16</p>
              </div>
              <div className="rounded border border-rule bg-ink-3/50 p-2">
                <p className="font-mono text-[8px] text-muted">P50</p>
                <p className="font-mono text-xs text-bone">142 ms</p>
              </div>
              <div className="rounded border border-rule bg-ink-3/50 p-2">
                <p className="font-mono text-[8px] text-muted">P95</p>
                <p className="font-mono text-xs text-bone">380 ms</p>
              </div>
              <div className="rounded border border-rule bg-ink-3/50 p-2">
                <p className="font-mono text-[8px] text-muted">In $/1K Tok</p>
                <p className="font-mono text-xs text-bone">$0.50</p>
              </div>
              <div className="rounded border border-rule bg-ink-3/50 p-2">
                <p className="font-mono text-[8px] text-muted">Out $/1K Tok</p>
                <p className="font-mono text-xs text-bone">$0.79</p>
              </div>
            </div>
          </div>

          {/* Parameters */}
          <div>
            <div className="flex items-center justify-between">
              <span className="font-mono text-[9px] uppercase text-muted">Parameters</span>
              <button className="text-[8px] text-brass">Reset</button>
            </div>
            <div className="mt-2 space-y-3">
              <ParamSlider label="Temperature" sublabel="creativity" value={temperature} min={0} max={2} step={0.01} onChange={setTemperature} />
              <ParamSlider label="Top-p" sublabel="nucleus" value={topP} min={0} max={1} step={0.01} onChange={setTopP} />
              <div className="flex items-center justify-between">
                <span className="text-[10px] text-bone">Max tokens <span className="text-muted">cap</span></span>
                <input type="number" value={maxTokens} onChange={(e) => setMaxTokens(Number(e.target.value))} className="w-16 rounded border border-rule bg-ink-3 px-2 py-0.5 text-right font-mono text-[10px] text-bone" />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-[10px] text-bone">Stream</span>
                <div onClick={() => setStream(!stream)} className={`h-4 w-7 cursor-pointer rounded-full ${stream ? "bg-amber" : "bg-ink-3 border border-rule"} relative`}>
                  <div className={`absolute top-0.5 h-3 w-3 rounded-full bg-white transition-all ${stream ? "left-3.5" : "left-0.5"}`} />
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-[10px] text-bone">Seed</span>
                <input type="number" value={42} className="w-16 rounded border border-rule bg-ink-3 px-2 py-0.5 text-right font-mono text-[10px] text-bone" readOnly />
              </div>
            </div>
          </div>

          {/* Compliance */}
          <div>
            <span className="font-mono text-[9px] uppercase text-muted">Compliance</span>
            <p className="mt-1 text-[9px] uppercase text-muted">Session Tag</p>
            <div className="mt-1.5 flex flex-wrap gap-1">
              {COMPLIANCE_TAGS.map((tag) => (
                <button
                  key={tag}
                  onClick={() => setComplianceTag(tag)}
                  className={`rounded px-2 py-0.5 text-[9px] font-mono ${tag === complianceTag ? "bg-brass/15 text-brass border border-brass/30" : "border border-rule text-muted hover:text-bone"}`}
                >
                  {tag}
                </button>
              ))}
            </div>
            <p className="mt-2 text-[8px] text-muted leading-relaxed">
              Tag scopes routing rules and redaction. PHI/HIPAA forces Hetzner-only with auto-redact and audit export pinned ON.
            </p>
            <div className="mt-3 space-y-2">
              <ToggleRow label="Auto-redact PHI/PII" on={true} />
              <ToggleRow label="Sign audit on export" on={true} />
              <ToggleRow label="Lock to on-prem (no AWS burst)" on={false} />
            </div>
            <p className="mt-3 font-mono text-[8px] text-muted/60">SHA-256 manifest emitted per session · evidence ready</p>
          </div>
        </div>
      </div>
    </div>
  );
}

function ParamSlider({ label, sublabel, value, min, max, step, onChange }: {
  label: string; sublabel: string; value: number; min: number; max: number; step: number; onChange: (v: number) => void;
}) {
  return (
    <div>
      <div className="flex items-center justify-between">
        <span className="text-[10px] text-bone">{label} <span className="text-muted">{sublabel}</span></span>
        <span className="font-mono text-[10px] text-bone">{value.toFixed(2)}</span>
      </div>
      <input type="range" min={min} max={max} step={step} value={value} onChange={(e) => onChange(Number(e.target.value))}
        className="mt-1 h-1 w-full cursor-pointer appearance-none rounded-full bg-ink-3 accent-amber" />
    </div>
  );
}

function ToggleRow({ label, on }: { label: string; on: boolean }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-[10px] text-bone">{label}</span>
      <div className={`h-4 w-7 rounded-full ${on ? "bg-amber" : "bg-ink-3 border border-rule"} relative`}>
        <div className={`absolute top-0.5 h-3 w-3 rounded-full bg-white transition-all ${on ? "left-3.5" : "left-0.5"}`} />
      </div>
    </div>
  );
}
