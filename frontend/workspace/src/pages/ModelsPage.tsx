import { useEffect, useState, useCallback } from "react";
import { Plus, Upload, GitBranch, ExternalLink, Search, Server, Cloud } from "lucide-react";
import { api } from "@/lib/api";

const MODELS = [
  { id: "veklom-llama3-70b", name: "Llama 3.1 70B Instruct", family: "META", category: "CHAT", license: "Llama 3 Community", context: "128K", quant: "FP16", replicas: 4, p50: "142 ms", p95: "380 ms", costPer1k: "$0.79", zone: "HETZNER · PRIMARY", tags: ["FUNCTION-CALLING", "JSON-MODE", "STREAMING"], enabled: true },
  { id: "veklom-mixtral-8x22b", name: "Mixtral 8×22B", family: "MISTRAL", category: "CHAT", license: "Apache 2.0", context: "66K", quant: "INT8", replicas: 8, p50: "121 ms", p95: "290 ms", costPer1k: "$0.60", zone: "HETZNER · PRIMARY", tags: ["FUNCTION-CALLING", "JSON-MODE", "STREAMING"], enabled: true },
  { id: "veklom-qwen2-72b", name: "Qwen 2.5 72B", family: "OPEN SOURCE", category: "CHAT", license: "Apache 2.0", context: "131K", quant: "INT4", replicas: 8, p50: "96 ms", p95: "240 ms", costPer1k: "$0.27", zone: "HETZNER · PRIMARY", tags: ["JSON-MODE", "STREAMING", "FUNCTION-CALLING"], enabled: true },
  { id: "veklom-claude-haiku", name: "Claude 3.5 Haiku (proxy)", family: "ANTHROPIC-COMPATIBLE", category: "CHAT", license: "Commercial", context: "200K", quant: "FP16", replicas: 2, p50: "228 ms", p95: "540 ms", costPer1k: "$4.00", zone: "AWS · BURST", tags: ["VISION", "FUNCTION-CALLING", "JSON-MODE"], enabled: true },
  { id: "veklom-deepseek-v3", name: "DeepSeek v3 Coder", family: "OPEN SOURCE", category: "COMPLETION", license: "MIT", context: "66K", quant: "INT8", replicas: 3, p50: "88 ms", p95: "210 ms", costPer1k: "$0.41", zone: "HETZNER · PRIMARY", tags: ["STREAMING", "CODE", "FIM"], enabled: true },
  { id: "veklom-bge-large", name: "BGE-M3 Embeddings", family: "OPEN SOURCE", category: "EMBEDDING", license: "MIT", context: "8K", quant: "FP16", replicas: 12, p50: "14 ms", p95: "38 ms", costPer1k: "$0.00", zone: "HETZNER · PRIMARY", tags: ["MULTILINGUAL", "LONG-CONTEXT"], enabled: true },
  { id: "veklom-cohere-rerank", name: "Veklom Reranker", family: "VEKLOM NATIVE", category: "RERANK", license: "Commercial", context: "4K", quant: "FP16", replicas: 6, p50: "22 ms", p95: "60 ms", costPer1k: "$0.00", zone: "HETZNER · PRIMARY", tags: ["FAST", "BINARY"], enabled: true },
  { id: "veklom-whisper-v3", name: "Whisper Large v3", family: "AUDIO-STT", category: "COMPLETION", license: "MIT", context: "0K", quant: "FP16", replicas: 2, p50: "380 ms", p95: "920 ms", costPer1k: "$0.00", zone: "HETZNER · PRIMARY", tags: ["MULTILINGUAL", "DIARIZATION"], enabled: true },
];

export function ModelsPage() {
  const [search, setSearch] = useState("");
  const [view, setView] = useState<"grid" | "table">("grid");

  const fetchData = useCallback(async () => {
    try {
      await api.get("/workspace/models");
    } catch { /* use static fallback */ }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const filtered = MODELS.filter(m =>
    m.name.toLowerCase().includes(search.toLowerCase()) ||
    m.family.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-start justify-between">
        <div>
          <p className="v-section-label">Models · Catalog</p>
          <h1 className="mt-1 text-2xl font-bold text-bone">Foundation & deployed models</h1>
          <p className="mt-1 text-sm text-muted">Filter by modality, provider, quantization, license, or feature. Promote, rollback, A/B split, or upload custom GGUF and safetensors.</p>
        </div>
        <div className="flex gap-2">
          <button className="v-btn-ghost text-xs"><Upload className="h-3.5 w-3.5" /> Upload model</button>
          <button className="v-btn-primary text-xs"><Plus className="h-3.5 w-3.5" /> Deploy from catalog</button>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted" />
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search models, family, license..."
            className="v-input pl-9 w-full text-sm"
          />
        </div>
        <div className="flex gap-1 rounded-md border border-rule p-1">
          <button onClick={() => setView("grid")} className={`px-3 py-1 rounded text-xs ${view === "grid" ? "bg-ink-3 text-bone" : "text-muted"}`}>Grid</button>
          <button onClick={() => setView("table")} className={`px-3 py-1 rounded text-xs ${view === "table" ? "bg-ink-3 text-bone" : "text-muted"}`}>Table</button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {filtered.map((model) => (
          <div key={model.id} className="v-card">
            <div className="flex items-start justify-between">
              <div>
                <p className="font-mono text-[9px] uppercase text-muted">{model.category} · {model.family}</p>
                <p className="mt-0.5 text-sm font-semibold text-bone">{model.name}</p>
                <p className="font-mono text-[9px] text-muted-2">{model.id}</p>
              </div>
              <button className="rounded border border-rule/50 p-1 hover:bg-ink-3"><Server className="h-3.5 w-3.5 text-muted" /></button>
            </div>
            <div className="mt-3 grid grid-cols-3 gap-2">
              <div><p className="v-section-label">Context</p><p className="text-xs font-mono text-bone">{model.context}</p></div>
              <div><p className="v-section-label">Quant</p><p className="text-xs font-mono text-bone">{model.quant}</p></div>
              <div><p className="v-section-label">Replicas</p><p className="text-xs font-mono text-bone">{model.replicas}</p></div>
              <div><p className="v-section-label">P50</p><p className="text-xs font-mono text-bone">{model.p50}</p></div>
              <div><p className="v-section-label">P95</p><p className="text-xs font-mono text-bone">{model.p95}</p></div>
              <div><p className="v-section-label">$ / 1K Out</p><p className="text-xs font-mono text-bone">{model.costPer1k}</p></div>
            </div>
            <div className="mt-3 flex items-center gap-1.5">
              <span className={`rounded px-1.5 py-0.5 font-mono text-[9px] ${model.zone.includes("AWS") ? "bg-electric/15 text-electric" : "bg-amber/15 text-amber"}`}>{model.zone}</span>
              {model.tags.map(t => <span key={t} className="v-badge-muted text-[9px]">{t}</span>)}
            </div>
            <div className="mt-3 flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <Cloud className="h-3 w-3 text-muted" />
                <span className="text-[10px] text-muted">{model.license}</span>
              </div>
              <div className="flex gap-1.5">
                <button className="v-btn-ghost text-[10px]"><GitBranch className="h-3 w-3" /> Versions</button>
                <button className="v-btn-primary text-[10px]">Deploy <ExternalLink className="h-3 w-3" /></button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
