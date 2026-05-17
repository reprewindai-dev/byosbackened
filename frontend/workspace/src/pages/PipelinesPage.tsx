import { useEffect, useCallback } from "react";
import { Plus, Play, Search, MoreHorizontal, Layers } from "lucide-react";
import { api } from "@/lib/api";

const NODE_PALETTE = {
  Models: [{ icon: "🧠", label: "LLM (deployed)" }, { icon: "📐", label: "Embedding" }, { icon: "🔄", label: "Reranker" }],
  Retrieval: [{ icon: "🗄️", label: "pgvector" }, { icon: "🔍", label: "Qdrant" }, { icon: "🌊", label: "Weaviate" }, { icon: "📄", label: "Document loader" }],
  Tools: [{ icon: "🌐", label: "HTTP" }, { icon: "🗃️", label: "SQL" }, { icon: "🐍", label: "Python" }, { icon: "📁", label: "File reader" }],
  Routing: [{ icon: "🛡️", label: "Policy gate" }, { icon: "🧭", label: "Semantic router" }, { icon: "🔀", label: "if / else" }],
  Output: [{ icon: "📋", label: "JSON formatter" }, { icon: "📝", label: "Markdown render" }, { icon: "🔗", label: "Webhook" }, { icon: "✅", label: "Audit signer" }],
};

const PIPELINES = [
  { name: "clinical-rag", template: "RAG / pgvector", vectorStore: "PGVECTOR", nodes: 9, invocations: 18420, lastRun: "2 min ago", status: "DEPLOYED" },
  { name: "patient-intake", template: "Intake form → triage", vectorStore: "QDRANT", nodes: 12, invocations: 412, lastRun: "12 min ago", status: "DEPLOYED" },
  { name: "legal-redactor", template: "PII strip → redline", vectorStore: "WEAVIATE", nodes: 7, invocations: 2210, lastRun: "1 hr ago", status: "DEPLOYED" },
  { name: "risk-classifier", template: "Multi-label classifier", vectorStore: "PGVECTOR", nodes: 5, invocations: 0, lastRun: "—", status: "DRAFT" },
];

const VECTOR_COLORS: Record<string, string> = {
  PGVECTOR: "bg-amber/15 text-amber",
  QDRANT: "bg-electric/15 text-electric",
  WEAVIATE: "bg-moss/15 text-moss",
};

export function PipelinesPage() {
  const fetchData = useCallback(async () => {
    try { await api.get("/pipelines"); } catch { /* static */ }
  }, []);
  useEffect(() => { fetchData(); }, [fetchData]);

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <p className="v-section-label">Pipelines</p>
          <h1 className="mt-1 text-2xl font-bold text-bone">Visual builder for governed inference</h1>
          <p className="mt-1 max-w-2xl text-sm text-muted">
            Drag-and-drop graphs that chain models, retrieval, memory, tools, and routing — every node gated by your policy engine.
          </p>
        </div>
        <div className="flex gap-2">
          <button className="flex items-center gap-1.5 rounded-md border border-rule px-3 py-1.5 text-xs text-muted hover:text-bone">
            <Layers className="h-3.5 w-3.5" /> Templates
          </button>
          <button className="v-btn-primary text-xs"><Plus className="h-3.5 w-3.5" /> New pipeline</button>
        </div>
      </div>

      {/* Canvas + Node Palette */}
      <div className="flex gap-4">
        {/* Canvas area */}
        <div className="flex-1">
          <div className="rounded-lg border border-rule bg-ink-2 overflow-hidden">
            {/* Pipeline header bar */}
            <div className="flex items-center gap-3 border-b border-rule px-4 py-2.5">
              <span className="font-mono text-xs font-medium text-bone">clinical-rag</span>
              <span className="rounded bg-bone/10 px-1.5 py-0.5 text-[8px] font-mono text-muted">V3 · DRAFT</span>
              <div className="ml-auto flex items-center gap-2">
                <button className="flex items-center gap-1 rounded border border-rule px-2 py-1 text-[10px] text-muted hover:text-bone">
                  <Play className="h-3 w-3" /> Test
                </button>
                <button className="flex items-center gap-1 rounded bg-amber/15 border border-amber/30 px-2 py-1 text-[10px] text-amber">
                  <Plus className="h-3 w-3" /> Deploy as endpoint
                </button>
              </div>
            </div>

            {/* Canvas placeholder */}
            <div className="relative h-72 bg-[#0d0d0d]">
              {/* Pipeline nodes (visual representation) */}
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="flex items-center gap-3">
                  {["Input", "Policy gate", "Embed BGE-M3", "Retrieve pgvector", "Rerank · cohere", "LLM · Llama 3.1", "PII redact", "Audit signer", "Webhook"].map((node, i) => (
                    <div key={i} className="flex flex-col items-center gap-1">
                      <div className="rounded-md border border-rule/60 bg-ink-3 px-2.5 py-1.5 text-[9px] text-bone whitespace-nowrap">
                        {node}
                      </div>
                      {i < 8 && <span className="text-muted/30 text-[10px]">→</span>}
                    </div>
                  ))}
                </div>
              </div>
              {/* Status bar */}
              <div className="absolute bottom-0 left-0 right-0 flex items-center gap-3 border-t border-rule/30 bg-ink-2/80 px-4 py-1.5">
                <span className="flex items-center gap-1.5">
                  <span className="h-1.5 w-1.5 rounded-full bg-moss" />
                  <span className="font-mono text-[9px] text-moss">POLICY ENGINE INLINE</span>
                </span>
                <span className="font-mono text-[9px] text-muted">9 nodes · 12 edges · est. p50 → 248ms</span>
              </div>
            </div>
          </div>
        </div>

        {/* Node palette */}
        <div className="w-52 shrink-0 space-y-4 overflow-y-auto">
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3 w-3 text-muted" />
            <input placeholder="Search nodes..." className="v-input pl-8 w-full text-[10px]" />
          </div>
          {Object.entries(NODE_PALETTE).map(([group, nodes]) => (
            <div key={group}>
              <p className="font-mono text-[9px] uppercase text-muted mb-1.5">{group}</p>
              <div className="grid grid-cols-2 gap-1.5">
                {nodes.map((node) => (
                  <div key={node.label} className="flex items-center gap-1.5 rounded border border-rule/40 bg-ink-3/30 px-2 py-1.5 text-[10px] text-bone cursor-pointer hover:border-rule hover:bg-ink-3/60">
                    <span className="text-xs">{node.icon}</span>
                    <span className="truncate">{node.label}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Pipelines table */}
      <div className="v-card-flush">
        <div className="flex items-center justify-between px-4 py-3 border-b border-rule">
          <div className="flex items-center gap-3">
            <span className="font-mono text-[10px] uppercase text-muted">Pipelines · Deployed & Draft</span>
            <span className="font-mono text-xs text-bone font-semibold">{PIPELINES.length} pipelines</span>
          </div>
          <div className="flex items-center gap-2">
            {Object.keys(VECTOR_COLORS).map((vs) => (
              <span key={vs} className={`rounded px-1.5 py-0.5 text-[8px] font-mono font-semibold ${VECTOR_COLORS[vs]}`}>{vs}</span>
            ))}
          </div>
        </div>
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-rule text-left">
              <th className="px-4 py-2.5 font-mono text-[9px] uppercase text-muted">Name</th>
              <th className="px-3 py-2.5 font-mono text-[9px] uppercase text-muted">Template</th>
              <th className="px-3 py-2.5 font-mono text-[9px] uppercase text-muted">Vector Store</th>
              <th className="px-3 py-2.5 font-mono text-[9px] uppercase text-muted">Nodes</th>
              <th className="px-3 py-2.5 font-mono text-[9px] uppercase text-muted">Invocations</th>
              <th className="px-3 py-2.5 font-mono text-[9px] uppercase text-muted">Last Run</th>
              <th className="px-3 py-2.5 font-mono text-[9px] uppercase text-muted">Status</th>
              <th className="w-8"></th>
            </tr>
          </thead>
          <tbody>
            {PIPELINES.map((p) => (
              <tr key={p.name} className="border-b border-rule/40 hover:bg-white/[0.02]">
                <td className="px-4 py-2.5 font-medium text-bone">{p.name}</td>
                <td className="px-3 py-2.5 text-muted">{p.template}</td>
                <td className="px-3 py-2.5">
                  <span className={`rounded px-1.5 py-0.5 text-[8px] font-mono font-semibold ${VECTOR_COLORS[p.vectorStore]}`}>
                    {p.vectorStore}
                  </span>
                </td>
                <td className="px-3 py-2.5 font-mono text-bone">{p.nodes}</td>
                <td className="px-3 py-2.5 font-mono text-bone">{p.invocations.toLocaleString()}</td>
                <td className="px-3 py-2.5 text-muted">{p.lastRun}</td>
                <td className="px-3 py-2.5">
                  <span className={`rounded px-1.5 py-0.5 text-[9px] font-mono font-semibold ${p.status === "DEPLOYED" ? "bg-moss/20 text-moss" : "bg-bone/10 text-muted"}`}>
                    ● {p.status}
                  </span>
                </td>
                <td className="px-2 py-2.5">
                  <MoreHorizontal className="h-3.5 w-3.5 text-muted cursor-pointer hover:text-bone" />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
