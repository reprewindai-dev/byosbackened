import { useState, useEffect, useCallback } from "react";
import { Plus, Upload, GitBranch, ExternalLink, Search, Server, Cloud, Loader2 } from "lucide-react";
import { MiniChart } from "@/components/MiniChart";
import { api } from "@/lib/api";

interface Model {
  type: string; provider: string; name: string; slug: string;
  context: string; quant: string; replicas: number;
  p50: string; p95: string; cost: string;
  region: "hetzner" | "aws"; regionLabel: string;
  tags: string[]; license: string; sparkline: number[];
}

const MODELS: Model[] = [
  { type: "CHAT", provider: "META", name: "Llama 3.1 70B Instruct", slug: "veklom-llama3-70b", context: "128K", quant: "FP16", replicas: 4, p50: "142 ms", p95: "300 ms", cost: "$0.79", region: "hetzner", regionLabel: "HETZNER · PRIMARY", tags: ["FUNCTION-CALLING", "JSON-MODE", "STREAMING"], license: "Llama 3 Community", sparkline: [20, 35, 40, 55, 48, 60, 72, 65, 80, 75, 85, 90] },
  { type: "CHAT", provider: "MISTRAL", name: "Mixtral 8x22B", slug: "veklom-mixtral-8x22", context: "66K", quant: "INT8", replicas: 6, p50: "121 ms", p95: "290 ms", cost: "$0.60", region: "hetzner", regionLabel: "HETZNER · PRIMARY", tags: ["FUNCTION-CALLING", "STREAMING"], license: "Apache 2.0", sparkline: [30, 42, 50, 55, 60, 58, 70, 68, 75, 80, 78, 85] },
  { type: "CHAT", provider: "OPEN SOURCE", name: "Qwen 2.5 72B", slug: "veklom-qwen2-72b", context: "131K", quant: "INT4", replicas: 8, p50: "96 ms", p95: "240 ms", cost: "$0.27", region: "hetzner", regionLabel: "HETZNER · PRIMARY", tags: ["JSON-MODE", "STREAMING"], license: "Apache 2.0", sparkline: [15, 20, 30, 45, 55, 60, 65, 70, 80, 85, 90, 95] },
  { type: "CHAT", provider: "ANTHROPIC-COMPATIBLE", name: "Claude 3.5 Haiku (proxy)", slug: "veklom-claude-haiku", context: "200K", quant: "FP16", replicas: 2, p50: "228 ms", p95: "540 ms", cost: "$4.00", region: "aws", regionLabel: "AWS · BURST", tags: ["VISION", "FUNCTION-CALLING", "JSON-MODE"], license: "Commercial", sparkline: [10, 12, 15, 14, 18, 20, 22, 25, 20, 18, 22, 24] },
  { type: "COMPLETION", provider: "OPEN SOURCE", name: "DeepSeek v3 Coder", slug: "veklom-deepseek-v3", context: "66K", quant: "INT8", replicas: 3, p50: "88 ms", p95: "210 ms", cost: "$0.41", region: "hetzner", regionLabel: "HETZNER · PRIMARY", tags: ["STREAMING", "CODE", "FIM"], license: "MIT", sparkline: [40, 45, 50, 48, 55, 60, 58, 65, 70, 68, 75, 80] },
  { type: "EMBEDDING", provider: "OPEN SOURCE", name: "BGE-M3 Embeddings", slug: "veklom-bge-large", context: "8K", quant: "FP16", replicas: 12, p50: "14 ms", p95: "38 ms", cost: "$0.00", region: "hetzner", regionLabel: "HETZNER · PRIMARY", tags: ["MULTILINGUAL", "LONG-CONTEXT"], license: "MIT", sparkline: [60, 65, 70, 72, 78, 80, 85, 88, 90, 92, 95, 98] },
  { type: "RERANK", provider: "VEKLOM NATIVE", name: "Veklom Reranker", slug: "veklom-cohere-rerank", context: "4K", quant: "FP16", replicas: 6, p50: "22 ms", p95: "60 ms", cost: "$0.00", region: "hetzner", regionLabel: "HETZNER · PRIMARY", tags: ["FAST", "BINARY"], license: "Commercial", sparkline: [30, 35, 40, 38, 45, 50, 55, 52, 60, 58, 65, 68] },
  { type: "AUDIO-STT", provider: "WHISPER", name: "Whisper Large v3", slug: "veklom-whisper-v3", context: "0K", quant: "FP16", replicas: 2, p50: "380 ms", p95: "920 ms", cost: "$0.00", region: "hetzner", regionLabel: "HETZNER · PRIMARY", tags: ["MULTILINGUAL", "DIARIZATION"], license: "MIT", sparkline: [10, 15, 20, 18, 25, 30, 28, 35, 40, 38, 42, 45] },
];

const VERSIONS = [
  { model: "llama3-70b@v3.2", deploy: "chat-prod", split: "75%", bar: 75, accent: "bg-crimson" },
  { model: "llama3-70b@v3.3", deploy: "", split: "25%", bar: 25, accent: "bg-amber" },
  { model: "qwen2-72b@v1.4", deploy: "code-assist", split: "50%", bar: 50, accent: "bg-moss" },
  { model: "qwen2-72b@v1.5-int4", deploy: "", split: "50%", bar: 50, accent: "bg-electric" },
];

export function ModelsPage() {
  const [view, setView] = useState<"grid" | "table">("grid");
  const [liveModels, setLiveModels] = useState<string[]>([]);
  const [llmModel, setLlmModel] = useState<string>("");
  const [loading, setLoading] = useState(true);

  const fetchLive = useCallback(async () => {
    try {
      const { data } = await api.get("/monitoring/health").catch(() =>
        fetch(`${window.__VEKLOM_API_BASE__ || ""}/status`).then(r => r.json()).then(data => ({ data }))
      );
      if (data?.llm_models_available) setLiveModels(data.llm_models_available);
      if (data?.llm_model) setLlmModel(data.llm_model);
    } catch { /* fallback */ }
    setLoading(false);
  }, []);

  useEffect(() => { fetchLive(); }, [fetchLive]);

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
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

      {/* Live models from backend */}
      {liveModels.length > 0 && (
        <div className="v-card">
          <div className="flex items-center justify-between">
            <div>
              <p className="v-section-label">Live · Ollama Models</p>
              <p className="mt-0.5 text-sm font-semibold text-bone">Available via backend — active model: <span className="text-amber">{llmModel || "—"}</span></p>
            </div>
            <span className="v-badge v-badge-green">● {liveModels.length} available</span>
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            {liveModels.map((m) => (
              <span key={m} className={`rounded-md border px-3 py-1.5 font-mono text-xs ${m === llmModel ? "border-amber/50 bg-amber/10 text-amber font-bold" : "border-rule bg-ink-3 text-bone-2"}`}>
                {m}{m === llmModel && " ●"}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted" />
          <input placeholder="Search models, family, license..." className="v-input w-full pl-8" />
        </div>
        <select className="v-input w-36"><option>All modalities</option></select>
        <select className="v-input w-36"><option>All providers</option></select>
        <div className="ml-auto flex rounded-md border border-rule overflow-hidden">
          <button onClick={() => setView("grid")} className={`px-3 py-1.5 text-[10px] font-semibold ${view === "grid" ? "bg-ink-3 text-bone" : "text-muted hover:text-bone"}`}>Grid</button>
          <button onClick={() => setView("table")} className={`px-3 py-1.5 text-[10px] font-semibold ${view === "table" ? "bg-ink-3 text-bone" : "text-muted hover:text-bone"}`}>Table</button>
        </div>
      </div>

      {/* Model Cards Grid */}
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {MODELS.map((m) => (
          <div key={m.slug} className="v-card flex flex-col">
            {/* Header */}
            <div className="flex items-start justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-mono text-[9px] uppercase text-muted">{m.type} · {m.provider}</span>
                </div>
                <p className="mt-1 text-sm font-bold text-bone">{m.name}</p>
                <p className="font-mono text-[10px] text-muted-2">{m.slug}</p>
              </div>
              <div className="flex h-7 w-7 items-center justify-center rounded-md border border-rule bg-ink-3">
                <Server className="h-3.5 w-3.5 text-muted" />
              </div>
            </div>

            {/* Stats grid */}
            <div className="mt-3 grid grid-cols-3 gap-3 rounded-md border border-rule/50 bg-ink-3/30 p-2.5">
              <div>
                <p className="font-mono text-[9px] uppercase text-muted">Context</p>
                <p className="font-mono text-xs font-bold text-bone">{m.context}</p>
              </div>
              <div>
                <p className="font-mono text-[9px] uppercase text-muted">Quant</p>
                <p className="font-mono text-xs font-bold text-bone">{m.quant}</p>
              </div>
              <div>
                <p className="font-mono text-[9px] uppercase text-muted">Replicas</p>
                <p className="font-mono text-xs font-bold text-bone">{m.replicas}</p>
              </div>
            </div>
            <div className="mt-2 grid grid-cols-3 gap-3 rounded-md border border-rule/50 bg-ink-3/30 p-2.5">
              <div>
                <p className="font-mono text-[9px] uppercase text-muted">P50</p>
                <p className="font-mono text-xs font-bold text-bone">{m.p50}</p>
              </div>
              <div>
                <p className="font-mono text-[9px] uppercase text-muted">P95</p>
                <p className="font-mono text-xs font-bold text-bone">{m.p95}</p>
              </div>
              <div>
                <p className="font-mono text-[9px] uppercase text-muted">$ / 1K out</p>
                <p className="font-mono text-xs font-bold text-bone">{m.cost}</p>
              </div>
            </div>

            {/* Region badge */}
            <div className="mt-3">
              <span className={`inline-flex items-center gap-1 rounded px-2 py-1 font-mono text-[9px] font-bold ${m.region === "hetzner" ? "bg-amber/15 text-amber border border-amber/30" : "bg-electric/15 text-electric border border-electric/30"}`}>
                {m.region === "hetzner" ? <Server className="h-2.5 w-2.5" /> : <Cloud className="h-2.5 w-2.5" />}
                {m.regionLabel}
              </span>
              {m.tags.map((t) => (
                <span key={t} className="ml-1.5 inline-block rounded bg-ink-3 border border-rule px-1.5 py-0.5 font-mono text-[8px] text-muted-2">{t}</span>
              ))}
            </div>

            {/* Sparkline */}
            <div className="mt-3 h-10">
              <MiniChart data={m.sparkline} color="amber" />
            </div>

            {/* Footer */}
            <div className="mt-3 flex items-center justify-between border-t border-rule pt-3">
              <span className="text-[10px] text-muted">{m.license}</span>
              <div className="flex gap-2">
                <button className="v-btn-ghost text-[10px]"><GitBranch className="h-3 w-3" /> Versions</button>
                <button className="v-btn-primary text-[10px] px-2.5 py-1">Deploy <ExternalLink className="ml-0.5 h-2.5 w-2.5" /></button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Versioning / A/B splits */}
      <div className="v-card">
        <div className="flex items-center justify-between">
          <div>
            <p className="v-section-label">Versioning</p>
            <p className="mt-0.5 text-sm font-semibold text-bone">A/B traffic split · 30-day rollback window · per-version audit lineage</p>
          </div>
          <span className="v-badge v-badge-green">✦ 4 ACTIVE SPLITS</span>
        </div>
        <div className="mt-4 grid grid-cols-4 gap-3">
          {VERSIONS.map((v, i) => (
            <div key={i} className="rounded-md border border-rule bg-ink-3/40 p-3">
              <p className="font-mono text-xs font-bold text-bone">{v.model}</p>
              {v.deploy && <p className="font-mono text-[10px] text-muted">{v.deploy}</p>}
              <div className="mt-2 flex items-center gap-2">
                <ExternalLink className="h-3 w-3 text-muted" />
                <div className="flex-1 h-1.5 rounded-full bg-ink-2 overflow-hidden">
                  <div className={`h-full rounded-full ${v.accent}`} style={{ width: `${v.bar}%` }} />
                </div>
                <span className="font-mono text-[10px] text-bone-2">{v.split}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
