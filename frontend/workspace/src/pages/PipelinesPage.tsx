import { Plus, Play, Pause } from "lucide-react";

const PIPELINES = [
  { name: "patient-intake-rag", desc: "PHI redaction → chunking → embedding → vector store", status: "running", steps: 4, lastRun: "2 min ago", throughput: "1.2k docs/hr" },
  { name: "contract-redliner", desc: "PDF extract → PII scan → clause diff → signed output", status: "running", steps: 5, lastRun: "8 min ago", throughput: "340 docs/hr" },
  { name: "compliance-evidence-collector", desc: "Log scan → control mapping → evidence bundling → S3 export", status: "running", steps: 4, lastRun: "1 hr ago", throughput: "continuous" },
  { name: "model-eval-nightly", desc: "Benchmark suite → drift check → alert if degraded", status: "scheduled", steps: 3, lastRun: "12 hr ago", throughput: "nightly" },
  { name: "cost-anomaly-detector", desc: "Spend stream → z-score → alert → optional kill-switch", status: "running", steps: 3, lastRun: "live", throughput: "real-time" },
];

export function PipelinesPage() {
  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-start justify-between">
        <div>
          <p className="v-section-label">Infrastructure · Pipelines</p>
          <h1 className="mt-1 text-2xl font-bold text-bone">Data & inference pipelines</h1>
          <p className="mt-1 text-sm text-muted">Composable multi-step workflows — policy-checked at every stage.</p>
        </div>
        <button className="v-btn-primary text-xs"><Plus className="h-3.5 w-3.5" /> New pipeline</button>
      </div>

      <div className="space-y-3">
        {PIPELINES.map((p) => (
          <div key={p.name} className="v-card flex items-center gap-4">
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <p className="text-sm font-semibold text-bone">{p.name}</p>
                <span className={`v-badge ${p.status === "running" ? "v-badge-green" : "v-badge-muted"}`}>● {p.status}</span>
              </div>
              <p className="mt-0.5 text-xs text-muted">{p.desc}</p>
            </div>
            <div className="flex items-center gap-6 text-[11px]">
              <div className="text-center"><span className="text-muted block">Steps</span><span className="text-bone font-mono">{p.steps}</span></div>
              <div className="text-center"><span className="text-muted block">Last run</span><span className="text-bone font-mono">{p.lastRun}</span></div>
              <div className="text-center"><span className="text-muted block">Throughput</span><span className="text-bone font-mono">{p.throughput}</span></div>
            </div>
            <div className="flex gap-1.5">
              <button className="v-btn-ghost px-2 py-1"><Play className="h-3 w-3" /></button>
              <button className="v-btn-ghost px-2 py-1"><Pause className="h-3 w-3" /></button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
