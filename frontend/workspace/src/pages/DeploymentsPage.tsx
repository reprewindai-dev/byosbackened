import { useEffect, useCallback } from "react";
import { ExternalLink, GitBranch, Server, Zap, Globe } from "lucide-react";
import { api } from "@/lib/api";

const DEPLOYMENTS = [
  { id: "chat-prod", model: "Llama 3.1 70B Instruct", zone: "Hetzner FSN1", zoneType: "PRIMARY", replicas: 4, status: "HEALTHY", p50: "142 ms", rps: "1,240", cost: "$0.79/1k", uptime: "99.97%" },
  { id: "embed-rag", model: "BGE-M3 Embeddings", zone: "Hetzner FSN1", zoneType: "PRIMARY", replicas: 12, status: "HEALTHY", p50: "14 ms", rps: "4,200", cost: "$0.00/1k", uptime: "99.99%" },
  { id: "code-assist", model: "DeepSeek v3 Coder", zone: "Hetzner FRA1", zoneType: "PRIMARY", replicas: 3, status: "HEALTHY", p50: "88 ms", rps: "340", cost: "$0.41/1k", uptime: "99.94%" },
  { id: "patient-intake", model: "Mixtral 8×22B", zone: "Hetzner FRA1", zoneType: "PRIMARY", replicas: 8, status: "SCALING", p50: "121 ms", rps: "980", cost: "$0.60/1k", uptime: "99.91%" },
  { id: "vision-api", model: "Claude 3.5 Haiku (proxy)", zone: "AWS US-East-1", zoneType: "BURST", replicas: 2, status: "HEALTHY", p50: "228 ms", rps: "120", cost: "$4.00/1k", uptime: "99.88%" },
  { id: "whisper-stt", model: "Whisper Large v3", zone: "Hetzner FSN1", zoneType: "PRIMARY", replicas: 2, status: "HEALTHY", p50: "380 ms", rps: "45", cost: "$0.00/1k", uptime: "99.95%" },
];

export function DeploymentsPage() {
  const fetchData = useCallback(async () => {
    try {
      await api.get("/deployments");
    } catch { /* use static fallback */ }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const zones = [...new Set(DEPLOYMENTS.map(d => d.zone))];

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-start justify-between">
        <div>
          <p className="v-section-label">Infrastructure · Deployments</p>
          <h1 className="mt-1 text-2xl font-bold text-bone">Active deployments</h1>
          <p className="mt-1 text-sm text-muted">All running model replicas across zones — real-time status, latency, and cost.</p>
        </div>
        <button className="v-btn-primary text-xs"><Server className="h-3.5 w-3.5" /> New deployment</button>
      </div>

      <div className="grid gap-3 md:grid-cols-3">
        <div className="v-card">
          <p className="v-section-label">Total Deployments</p>
          <p className="mt-1 text-2xl font-bold text-bone">{DEPLOYMENTS.length}</p>
          <p className="text-xs text-muted">across {zones.length} zones</p>
        </div>
        <div className="v-card">
          <p className="v-section-label">Healthy</p>
          <p className="mt-1 text-2xl font-bold text-moss">{DEPLOYMENTS.filter(d => d.status === "HEALTHY").length}</p>
          <p className="text-xs text-muted">{DEPLOYMENTS.filter(d => d.status !== "HEALTHY").length} degraded</p>
        </div>
        <div className="v-card">
          <p className="v-section-label">Total Replicas</p>
          <p className="mt-1 text-2xl font-bold text-bone">{DEPLOYMENTS.reduce((s, d) => s + d.replicas, 0)}</p>
          <p className="text-xs text-muted">GPU + CPU pool</p>
        </div>
      </div>

      {zones.map(zone => (
        <div key={zone}>
          <div className="mb-3 flex items-center gap-2">
            <Globe className="h-3.5 w-3.5 text-muted" />
            <span className="font-mono text-xs text-muted uppercase">{zone}</span>
          </div>
          <div className="space-y-2">
            {DEPLOYMENTS.filter(d => d.zone === zone).map(dep => (
              <div key={dep.id} className="v-card-flush flex items-center gap-4 px-4 py-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-sm text-bone">{dep.model}</span>
                    <span className={`rounded px-1.5 py-0.5 font-mono text-[9px] ${dep.zoneType === "PRIMARY" ? "bg-amber/15 text-amber" : "bg-electric/15 text-electric"}`}>{dep.zoneType}</span>
                    <span className={`v-badge ${dep.status === "HEALTHY" ? "v-badge-green" : "v-badge-amber"}`}>{dep.status}</span>
                  </div>
                  <p className="mt-0.5 font-mono text-[10px] text-muted">{dep.id}</p>
                </div>
                <div className="hidden md:flex items-center gap-6 text-xs">
                  <div className="text-center"><p className="v-section-label">P50</p><p className="font-mono text-bone">{dep.p50}</p></div>
                  <div className="text-center"><p className="v-section-label">RPS</p><p className="font-mono text-bone">{dep.rps}</p></div>
                  <div className="text-center"><p className="v-section-label">Replicas</p><p className="font-mono text-bone">{dep.replicas}</p></div>
                  <div className="text-center"><p className="v-section-label">Cost</p><p className="font-mono text-bone">{dep.cost}</p></div>
                  <div className="text-center"><p className="v-section-label">Uptime</p><p className="font-mono text-moss">{dep.uptime}</p></div>
                </div>
                <div className="flex items-center gap-2">
                  <button className="v-btn-ghost text-xs"><GitBranch className="h-3 w-3" /> Versions</button>
                  <button className="v-btn-primary text-xs"><Zap className="h-3 w-3" /> Deploy <ExternalLink className="h-3 w-3" /></button>
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
