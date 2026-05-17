import { useState, useEffect, useRef, useCallback } from "react";
import { Send, RotateCcw, Sliders, Loader2 } from "lucide-react";
import { api } from "@/lib/api";

const DEFAULT_MODELS = ["qwen2.5:3b"];

interface ChatMessage {
  role: string;
  content: string;
  meta?: string;
}

function genConvId() {
  return `conv_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

export function PlaygroundPage() {
  const [prompt, setPrompt] = useState("");
  const [models, setModels] = useState<string[]>(DEFAULT_MODELS);
  const [model, setModel] = useState(DEFAULT_MODELS[0]);
  const [convId, setConvId] = useState(genConvId);
  const [sending, setSending] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([
    { role: "system", content: "Sovereign AI playground. All prompts are policy-checked, routed, audited, and evidence-signed before execution." },
  ]);
  const [lastProvider, setLastProvider] = useState<string>("—");
  const [lastCbState, setLastCbState] = useState<string>("—");
  const chatRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    (async () => {
      try {
        const { data } = await api.get("/monitoring/health").catch(() =>
          fetch(`${window.__VEKLOM_API_BASE__ || ""}/status`).then(r => r.json()).then(data => ({ data }))
        );
        if (data?.llm_models_available?.length) {
          setModels(data.llm_models_available);
          setModel(data.llm_model || data.llm_models_available[0]);
        }
        if (data?.circuit_breaker?.state) setLastCbState(data.circuit_breaker.state);
      } catch { /* fallback models */ }
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
      const { data } = await api.post("/exec", {
        prompt: userMsg,
        model,
        conversation_id: convId,
        use_memory: true,
      });
      const meta = [
        data.model || model,
        data.provider || "—",
        data.latency_ms ? `${data.latency_ms}ms` : null,
        data.total_tokens ? `${data.total_tokens} tok` : null,
        data.log_id ? `audit: ${data.log_id}` : null,
      ].filter(Boolean).join(" · ");
      setMessages((m) => [...m, { role: "assistant", content: data.response || "(empty response)", meta }]);
      if (data.provider) setLastProvider(data.provider);
    } catch (err: unknown) {
      const axErr = err as { response?: { data?: { detail?: string }; status?: number }; code?: string; message?: string };
      const detail = axErr.response?.data?.detail || axErr.message || "Inference failed";
      setMessages((m) => [...m, { role: "assistant", content: `Error: ${detail}`, meta: `status: ${axErr.response?.status || "network"}` }]);
    } finally {
      setSending(false);
    }
  }, [prompt, model, convId, sending]);

  function clearChat() {
    setMessages([{ role: "system", content: "Sovereign AI playground. All prompts are policy-checked, routed, audited, and evidence-signed before execution." }]);
    setConvId(genConvId());
  }

  return (
    <div className="flex h-full flex-col animate-fade-in">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <p className="v-section-label">Playground</p>
          <h1 className="mt-1 text-xl font-bold text-bone">Interactive inference console</h1>
        </div>
        <div className="flex items-center gap-3">
          <select value={model} onChange={(e) => setModel(e.target.value)} className="v-input w-48 text-xs">
            {models.map((m) => <option key={m} value={m}>{m}</option>)}
          </select>
          <button className="v-btn-ghost text-xs"><Sliders className="h-3.5 w-3.5" /> Params</button>
          <button className="v-btn-ghost text-xs" onClick={clearChat}><RotateCcw className="h-3.5 w-3.5" /> Clear</button>
        </div>
      </div>

      {/* Chat area */}
      <div ref={chatRef} className="flex-1 overflow-y-auto rounded-lg border border-rule bg-ink-2 p-4 space-y-4">
        {messages.map((msg, i) => (
          <div key={i} className={`flex gap-3 ${msg.role === "user" ? "justify-end" : ""}`}>
            {msg.role !== "user" && (
              <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-ink-3 border border-rule">
                <svg viewBox="0 0 32 32" className="h-4 w-4">
                  <path d="M16 4 L6 24 L10 24 L16 13 L22 24 L26 24 Z" fill="#e5a832" />
                  <circle cx="16" cy="20" r="2" fill="#e5a832" />
                </svg>
              </div>
            )}
            <div className={`max-w-[70%] rounded-lg px-3 py-2 ${msg.role === "user" ? "bg-brass/15 text-bone" : msg.role === "system" ? "bg-ink-3 border border-rule text-muted" : "bg-ink-3 text-bone"}`}>
              <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
              {msg.meta && (
                <p className="mt-1.5 font-mono text-[9px] text-muted-2 border-t border-rule/50 pt-1.5">{msg.meta}</p>
              )}
            </div>
          </div>
        ))}
        {sending && (
          <div className="flex gap-3">
            <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-ink-3 border border-rule">
              <Loader2 className="h-4 w-4 animate-spin text-amber" />
            </div>
            <div className="rounded-lg bg-ink-3 px-3 py-2 text-sm text-muted">Thinking...</div>
          </div>
        )}
      </div>

      {/* Input */}
      <div className="mt-3 flex gap-2">
        <input
          type="text"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && onSend()}
          placeholder="Enter prompt — policy engine evaluates before routing..."
          className="v-input flex-1"
          disabled={sending}
        />
        <button onClick={onSend} disabled={sending} className="v-btn-primary">
          {sending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
        </button>
      </div>

      {/* Status bar */}
      <div className="mt-2 flex items-center gap-4 font-mono text-[9px] text-muted-2">
        <span className="flex items-center gap-1"><span className={`h-1.5 w-1.5 rounded-full ${sending ? "bg-amber animate-pulse" : "bg-moss animate-pulse-soft"}`} /> {sending ? "Inferring" : "Live"}</span>
        <span>Model: {model}</span>
        <span>Provider: {lastProvider}</span>
        <span>Circuit: {lastCbState}</span>
        <span>Conv: {convId.slice(0, 16)}</span>
      </div>
    </div>
  );
}
