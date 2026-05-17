import { useEffect, useState, useCallback } from "react";
import { Plus, Upload, GitBranch, ExternalLink, Search, Server } from "lucide-react";
import { api } from "@/lib/api";

interface Model {
  id: string; name: string; family: string; category: string; license: string;
  context: string; quant: string; replicas: number; p50: string; p95: string;
  costPer1k: string; zone: string; tags: string[];
}

const MODELS: Model[] = [
  { id: "veklom-llama3-70b", name: "Llama 3.1 70B Instruct", family: "META", category: "CHAT", license: "Llama 3 Community", context: "128K", quant: "FP16", replicas: 4, p50: "142 ms", p95: "380 ms", costPer1k: "$0.79", zone: "HETZNER · PRIMARY", tags: ["FUNCTION-CALLING", "JSON-MODE", "STREAMING"] },
  { id: "veklom-mixtral-8x22", name: "Mixtral 8×22B", family: "MISTRAL", category: "CHAT", license: "Apache 2.0", context: "66K", quant: "INT8", replicas: 6, p50: "121 ms", p95: "290 ms", costPer1k: "$0.60", zone: "HETZNER · PRIMARY", tags: ["FUNCTION-CALLING", "JSON-MODE", "STREAMING"] },
  { id: "veklom-qwen2-72b", name: "Qwen 2.5 72B", family: "OPEN SOURCE", category: "CHAT", license: "Apache 2.0", context: "131K", quant: "INT4", replicas: 8, p50: "96 ms", p95: "240 ms", costPer1k: "$0.27", zone: "HETZNER · PRIMARY", tags: ["FUNCTION-CALLING", "JSON-MODE", "STREAMING"] },
  { id: "veklom-claude-haiku", name: "Claude 3.5 Haiku (proxy)", family: "ANTHROPIC-COMPATIBLE", category: "CHAT", license: "Commercial", context: "200K", quant: "FP16", replicas: 2, p50: "228 ms", p95: "540 ms", costPer1k: "$4.00", zone: "AWS · BURST", tags: ["FUNCTION-CALLING", "VISION", "JSON-MODE"] },
  { id: "veklom-deepseek-v3", name: "DeepSeek v3 Coder", family: "OPEN SOURCE", category: "COMPLETION", license: "MIT", context: "66K", quant: "INT8", replicas: 3, p50: "88 ms", p95: "210 ms", costPer1k: "$0.41", zone: "HETZNER · PRIMARY", tags: ["STREAMING", "CODE", "FIM"] },
  { id: "veklom-bge-large", name: "BGE-M3 Embeddings", family: "OPEN SOURCE", category: "EMBEDDING", license: "MIT", context: "8K", quant: "FP16", replicas: 12, p50: "14 ms", p95: "38 ms", costPer1k: "$0.00", zone: "HETZNER · PRIMARY", tags: ["MULTILINGUAL", "LONG-CONTEXT"] },
  { id: "veklom-cohere-rerank", name: "Veklom Reranker", family: "VEKLOM NATIVE", category: "RERANK", license: "Commercial", context: "4K", quant: "FP16", replicas: 6, p50: "22 ms", p95: "60 ms", costPer1k: "$0.00", zone: "HETZNER · PRIMARY", tags: ["FAST", "BINARY"] },
  { id: "veklom-whisper-v3", name: "Whisper Large v3", family: "AUDIO-STT · WHISPER", category: "AUDIO-STT", license: "MIT", context: "0K", quant: "FP16", replicas: 2, p50: "380 ms", p95: "920 ms", costPer1k: "$0.00", zone: "HETZNER · PRIMARY", tags: ["MULTILINGUAL", "DIARIZATION"] },
];

const VERSIONS = [
  { label: "llama3-70b@v3.2", deploy: "chat-prod", split: "75 / 25", link: "llama3-70b@v3.3" },
  { label: "qwen2-72b@v1.4", deploy: "code-assist", split: "50 / 50", link: "qwen2-72b@v1.5-int4" },
];

export function ModelsPage() {
  const [search, setSearch] = useState("");
  const [view, setView] = useState<"grid" | "table">("grid");

  const fetchData = useCallback(async () => {
    try { await api.get("/workspace/models"); } catch { /* static */ }
  }, []);
  useEffect(() => { fetchData(); }, [fetchData]);

  const filtered = MODELS.filter(m =>
    m.name.toLowerCase().includes(search.toLowerCase()) ||
    m.family.toLowerCase().includes(search.toLowerCase()) ||
    m.category.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <p className="v-section-label">Models · Catalog</p>
          <h1 className="mt-1 text-2xl font-bold text-bone">Foundation & deployed models</h1>
          <p className="mt-1 max-w-2xl text-sm text-muted">
            Filter by modality, provider, quantization, license, or feature. Promote, rollback, A/B split, or upload custom GGUF and safetensors.
          </p>
        </div>
        <div className="flex gap-2">
          <button className="flex items-center gap-1.5 rounded-md border border-rule px-3 py-1.5 text-xs text-muted hover:text-bone"><Upload className="h-3.5 w-3.5" /> Upload model</button>
          <button className="v-btn-primary text-xs"><Plus className="h-3.5 w-3.5" /> Deploy from catalog</button>
        </div>
      </div>

      {/* Search + filters */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-lg">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted" />
          <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search models, family, license..." className="v-input pl-9 w-full text-xs" />
        </div>
        <select className="v-input text-xs w-36"><option>All modalities</option></select>
        <select className="v-input text-xs w-36"><option>All providers</option></select>
        <div className="flex gap-1 rounded-md border border-rule p-0.5">
          <button onClick={() => setView("grid")} className={`px-3 py-1 rounded text-xs ${view === "grid" ? "bg-ink-3 text-bone" : "text-muted"}`}>Grid</button>
          <button onClick={() => setView("table")} className={`px-3 py-1 rounded text-xs ${view === "table" ? "bg-ink-3 text-bone" : "text-muted"}`}>Table</button>
        </div>
      </div>

      {/* Model grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {filtered.map((m) => (
          <div key={m.id} className="v-card flex flex-col">
            <div className="flex items-start justify-between">
              <div>
                <p className="font-mono text-[9px] uppercase text-muted">{m.category} · {m.family}</p>
                <p className="mt-0.5 text-sm font-semibold text-bone">{m.name}</p>
                <p className="font-mono text-[9px] text-muted-2">{m.id}</p>
              </div>
              <button className="rounded border border-rule/50 p-1.5 hover:bg-ink-3"><Server className="h-3.5 w-3.5 text-muted" /></button>
            </div>

            {/* Stats grid */}
            <div className="mt-3 grid grid-cols-3 gap-x-4 gap-y-2">
              <StatCell label="Context" value={m.context} />
              <StatCell label="Quant" value={m.quant} />
              <StatCell label="Replicas" value={String(m.replicas)} />
              <StatCell label="P50" value={m.p50} />
              <StatCell label="P95" value={m.p95} />
              <StatCell label="$ / 1K Out" value={m.costPer1k} />
            </div>

            {/* Zone + tags */}
            <div className="mt-3 flex flex-wrap items-center gap-1.5">
              <span className={`rounded px-1.5 py-0.5 font-mono text-[8px] font-semibold ${m.zone.includes("AWS") ? "bg-electric/15 text-electric" : "bg-amber/15 text-amber"}`}>
                {m.zone}
              </span>
              {m.tags.map(t => (
                <span key={t} className="rounded bg-bone/5 px-1.5 py-0.5 font-mono text-[8px] text-muted">{t}</span>
              ))}
            </div>

            {/* Sparkline placeholder */}
            <div className="mt-3 h-10 rounded bg-ink-3/50 overflow-hidden">
              <svg viewBox="0 0 200 40" className="w-full h-full" preserveAspectRatio="none">
                <path d={`M0,30 Q25,${15 + Math.random() * 15} 50,${20 + Math.random() * 10} T100,${18 + Math.random() * 12} T150,${22 + Math.random() * 8} T200,${20 + Math.random() * 10}`}
                  fill="none" stroke="#e5a832" strokeWidth="1.5" opacity="0.6" />
              </svg>
            </div>

            {/* Footer */}
            <div className="mt-3 flex items-center justify-between border-t border-rule/30 pt-3">
              <span className="text-[10px] text-muted">{m.license}</span>
              <div className="flex gap-1.5">
                <button className="flex items-center gap-1 rounded border border-rule px-2 py-0.5 text-[10px] text-muted hover:text-bone">
                  <GitBranch className="h-3 w-3" /> Versions
                </button>
                <button className="flex items-center gap-1 rounded bg-amber/15 border border-amber/30 px-2 py-0.5 text-[10px] text-amber hover:bg-amber/25">
                  Deploy <ExternalLink className="h-3 w-3" />
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Versioning bar */}
      <div className="v-card">
        <div className="flex items-center justify-between">
          <div>
            <p className="v-section-label">Versioning</p>
            <p className="mt-0.5 text-sm font-semibold text-bone">A/B traffic split · 30-day rollback window · per-version audit lineage</p>
          </div>
          <span className="rounded bg-moss/15 px-2 py-0.5 font-mono text-[9px] text-moss">4 Active Splits</span>
        </div>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          {VERSIONS.map((v) => (
            <div key={v.label} className="rounded-md border border-rule/40 bg-ink-3/30 px-4 py-3">
              <div className="flex items-center gap-3">
                <span className="font-mono text-xs font-medium text-bone">{v.label}</span>
                <ExternalLink className="h-3 w-3 text-muted" />
                <span className="font-mono text-xs text-muted">{v.link}</span>
              </div>
              <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-ink-2">
                <div className="h-full rounded-full bg-amber" style={{ width: v.split.startsWith("75") ? "75%" : "50%" }} />
              </div>
              <div className="mt-1.5 flex items-center justify-between text-[10px]">
                <span className="text-muted">{v.deploy}</span>
                <span className="font-mono text-muted">{v.split}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function StatCell({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded border border-rule/30 bg-ink-3/30 px-2 py-1.5">
      <p className="font-mono text-[8px] uppercase text-muted">{label}</p>
      <p className="font-mono text-xs text-bone">{value}</p>
    </div>
  );
}
