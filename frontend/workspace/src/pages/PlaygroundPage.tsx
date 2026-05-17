import { useState } from "react";
import { Send, RotateCcw, Sliders } from "lucide-react";

const MODELS = ["llama-3.1-70b", "mixtral-8x22b", "qwen-2.5-72b", "claude-3.5-haiku", "deepseek-v3", "bge-m3"];

export function PlaygroundPage() {
  const [prompt, setPrompt] = useState("");
  const [model, setModel] = useState(MODELS[0]);
  const [messages, setMessages] = useState<{ role: string; content: string; meta?: string }[]>([
    { role: "system", content: "Sovereign AI playground. All prompts are policy-checked, routed, audited, and evidence-signed before execution." },
  ]);

  function onSend() {
    if (!prompt.trim()) return;
    setMessages((m) => [...m, { role: "user", content: prompt }, { role: "assistant", content: "Response will appear here once connected to live backend.", meta: `${model} · Hetzner FSN1 · 142ms · $0.00091 · policy: PASSED` }]);
    setPrompt("");
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
            {MODELS.map((m) => <option key={m} value={m}>{m}</option>)}
          </select>
          <button className="v-btn-ghost text-xs"><Sliders className="h-3.5 w-3.5" /> Params</button>
          <button className="v-btn-ghost text-xs" onClick={() => setMessages([])}><RotateCcw className="h-3.5 w-3.5" /> Clear</button>
        </div>
      </div>

      {/* Chat area */}
      <div className="flex-1 overflow-y-auto rounded-lg border border-rule bg-ink-2 p-4 space-y-4">
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
      </div>

      {/* Input */}
      <div className="mt-3 flex gap-2">
        <input
          type="text"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && onSend()}
          placeholder="Enter prompt — policy engine evaluates before routing..."
          className="v-input flex-1"
        />
        <button onClick={onSend} className="v-btn-primary"><Send className="h-4 w-4" /></button>
      </div>

      {/* Status bar */}
      <div className="mt-2 flex items-center gap-4 font-mono text-[9px] text-muted-2">
        <span className="flex items-center gap-1"><span className="h-1.5 w-1.5 rounded-full bg-moss animate-pulse-soft" /> Live</span>
        <span>Model: {model}</span>
        <span>Route: Hetzner FSN1 (primary)</span>
        <span>Policy: outbound.public.v3</span>
        <span>Audit: SHA-256 chain active</span>
      </div>
    </div>
  );
}
