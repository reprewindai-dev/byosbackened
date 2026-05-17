import { useState, useEffect, useCallback } from "react";
import { Plus, Webhook, Lock, Key, Globe, Copy, ExternalLink, Server } from "lucide-react";
import { MiniChart } from "@/components/MiniChart";
import { api } from "@/lib/api";

interface Endpoint {
  name: string; url: string; type: string; model: string; region: string;
  regionType: "hetzner" | "aws"; auth: string; authBadge: string;
  rateLimit: string; rps: number; errors: string; status: "LIVE" | "PAUSED" | "DRAFT";
  sparkline: number[];
}

const ENDPOINTS: Endpoint[] = [
  { name: "chat-prod", url: "https://api.veklom.com/v1/chat/completions", type: "CHAT", model: "veklom-llama3-70b", region: "fsn1-hetz", regionType: "hetzner", auth: "API-KEY", authBadge: "v-badge-amber", rateLimit: "240 rpm / 1.2M tpm", rps: 38.4, errors: "0.20%", status: "LIVE", sparkline: [20, 35, 45, 55, 48, 60, 72, 65, 80, 75, 85, 90] },
  { name: "embed-rag", url: "https://api.veklom.com/v1/embeddings", type: "EMBEDDING", model: "veklom-bge-large", region: "fra1-hetz", regionType: "hetzner", auth: "API-KEY", authBadge: "v-badge-amber", rateLimit: "600 rpm / 4M tpm", rps: 112.7, errors: "0.00%", status: "LIVE", sparkline: [60, 65, 70, 72, 78, 80, 85, 88, 90, 92, 95, 98] },
  { name: "code-assist", url: "https://api.veklom.com/v1/completions", type: "COMPLETION", model: "veklom-deepseek-v3", region: "fsn1-hetz", regionType: "hetzner", auth: "JWT", authBadge: "v-badge-electric", rateLimit: "120 rpm", rps: 6.1, errors: "0.10%", status: "LIVE", sparkline: [40, 45, 50, 48, 55, 60, 58, 65, 70, 68, 75, 80] },
  { name: "patient-intake-pipeline", url: "https://api.veklom.com/p/patient-intake", type: "PIPELINE", model: "veklom-llama3-70b", region: "fsn1-hetz", regionType: "hetzner", auth: "API-KEY", authBadge: "v-badge-amber", rateLimit: "60 rpm", rps: 1.4, errors: "0.00%", status: "LIVE", sparkline: [10, 15, 20, 18, 25, 30, 28, 35, 40, 38, 42, 45] },
  { name: "nightly-batch-summarize", url: "https://api.veklom.com/v1/batches", type: "BATCH", model: "veklom-mixtral-8x22", region: "ash-aws", regionType: "aws", auth: "API-KEY", authBadge: "v-badge-amber", rateLimit: "burst 4× nightly", rps: 0.0, errors: "0.00%", status: "PAUSED", sparkline: [5, 8, 12, 10, 15, 18, 14, 20, 22, 18, 25, 20] },
  { name: "audit-pii-classifier", url: "https://api.veklom.com/v1/chat/completions", type: "CHAT", model: "veklom-qwen2-72b", region: "fsn1-hetz", regionType: "hetzner", auth: "IP-ALLOWLIST", authBadge: "v-badge-muted", rateLimit: "60 rpm", rps: 0.0, errors: "0.00%", status: "DRAFT", sparkline: [2, 3, 5, 4, 6, 8, 7, 10, 12, 10, 14, 12] },
];

export function DeploymentsPage() {
  const [selected] = useState(0);
  const ep = ENDPOINTS[selected];
  const [liveModels, setLiveModels] = useState<string[]>([]);

  const fetchLive = useCallback(async () => {
    try {
      const { data } = await api.get("/monitoring/health").catch(() =>
        fetch(`${window.__VEKLOM_API_BASE__ || ""}/status`).then(r => r.json()).then(data => ({ data }))
      );
      if (data?.llm_models_available) setLiveModels(data.llm_models_available);
    } catch { /* fallback */ }
  }, []);

  useEffect(() => { fetchLive(); }, [fetchLive]);

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-start justify-between">
        <div>
          <p className="v-section-label">Deployments · Endpoints</p>
          <h1 className="mt-1 text-2xl font-bold text-bone">OpenAI-compatible endpoints</h1>
          <p className="mt-1 text-sm text-muted">Chat, completion, embedding, pipeline, and async batch endpoints — each with auth, rate limits, CORS, webhooks, and SDK guides.</p>
        </div>
        <div className="flex gap-2">
          <button className="v-btn-ghost text-xs"><Webhook className="h-3.5 w-3.5" /> Webhooks</button>
          <button className="v-btn-primary text-xs"><Plus className="h-3.5 w-3.5" /> New endpoint</button>
        </div>
      </div>

      {/* Endpoint table */}
      <div className="v-card-flush">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-rule text-left">
              <th className="px-4 py-3 font-mono text-[9px] uppercase text-muted">Endpoint</th>
              <th className="px-3 py-3 font-mono text-[9px] uppercase text-muted">Type</th>
              <th className="px-3 py-3 font-mono text-[9px] uppercase text-muted">Model</th>
              <th className="px-3 py-3 font-mono text-[9px] uppercase text-muted">Region</th>
              <th className="px-3 py-3 font-mono text-[9px] uppercase text-muted">Auth</th>
              <th className="px-3 py-3 font-mono text-[9px] uppercase text-muted">Rate Limit</th>
              <th className="px-3 py-3 font-mono text-[9px] uppercase text-muted text-right">RPS</th>
              <th className="px-3 py-3 font-mono text-[9px] uppercase text-muted text-right">Errors</th>
              <th className="px-3 py-3 font-mono text-[9px] uppercase text-muted">Status</th>
              <th className="w-8"></th>
            </tr>
          </thead>
          <tbody>
            {ENDPOINTS.map((e, i) => (
              <tr key={e.name} className={`border-b border-rule/50 cursor-pointer transition-colors ${i === selected ? "bg-ink-3/60" : "hover:bg-ink-3/30"}`}>
                <td className="px-4 py-3">
                  <p className="font-semibold text-bone">{e.name}</p>
                  <p className="font-mono text-[9px] text-muted-2 truncate max-w-[200px]">{e.url}</p>
                </td>
                <td className="px-3 py-3 font-mono text-[10px] text-muted-2">{e.type}</td>
                <td className="px-3 py-3 font-mono text-[10px] text-bone-2">{e.model}</td>
                <td className="px-3 py-3 font-mono text-[10px] text-muted">{e.region}</td>
                <td className="px-3 py-3">
                  <span className={`v-badge ${e.authBadge}`}>
                    {e.auth === "API-KEY" ? <><Key className="mr-0.5 h-2.5 w-2.5" /> API-KEY</> :
                     e.auth === "JWT" ? <><Lock className="mr-0.5 h-2.5 w-2.5" /> JWT</> :
                     <><Globe className="mr-0.5 h-2.5 w-2.5" /> IP-ALLOWLIST</>}
                  </span>
                </td>
                <td className="px-3 py-3 font-mono text-[10px] text-muted">{e.rateLimit}</td>
                <td className="px-3 py-3 font-mono text-[10px] text-bone-2 text-right">{e.rps}</td>
                <td className="px-3 py-3 font-mono text-[10px] text-right">{e.errors}</td>
                <td className="px-3 py-3">
                  <span className={`v-badge ${e.status === "LIVE" ? "v-badge-green" : e.status === "PAUSED" ? "v-badge-amber" : "v-badge-muted"}`}>● {e.status}</span>
                </td>
                <td className="px-2"><ExternalLink className="h-3 w-3 text-muted" /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Detail panel */}
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="v-card space-y-4">
          <div>
            <p className="v-section-label">Endpoint Detail · {ep.name}</p>
            <div className="mt-2 flex items-center gap-2 rounded-md bg-ink-3 border border-rule px-3 py-2">
              <span className="flex-1 font-mono text-xs text-bone truncate">{ep.url}</span>
              <span className="v-badge v-badge-green">● LIVE</span>
              <span className="inline-flex items-center gap-1 rounded px-2 py-0.5 font-mono text-[9px] font-bold bg-amber/15 text-amber border border-amber/30"><Server className="h-2.5 w-2.5" /> HETZNER · PRIMARY</span>
              <span className="v-badge v-badge-electric">P50 142 ms</span>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-4 text-[11px]">
            <div><span className="v-section-label">Auth</span><p className="mt-1 font-mono text-bone">Bearer · vk_live_8h2x</p></div>
            <div><span className="v-section-label">Rate</span><p className="mt-1 font-mono text-bone">240 rpm · 1.2M tpm</p></div>
            <div><span className="v-section-label">Timeout</span><p className="mt-1 font-mono text-bone">30s · Stream OK</p></div>
          </div>
          <div className="grid grid-cols-3 gap-4 text-[11px]">
            <div><span className="v-section-label">CORS</span><p className="mt-1 font-mono text-bone">https://app.acme.io</p></div>
            <div><span className="v-section-label">IP Allowlist</span><p className="mt-1 font-mono text-bone">off</p></div>
            <div><span className="v-section-label">Webhook</span><p className="mt-1 font-mono text-bone">on async only</p></div>
          </div>

          <div>
            <p className="v-section-label">RPS · Last 24h</p>
            <div className="mt-2 h-20"><MiniChart data={ep.sparkline} color="amber" /></div>
          </div>
        </div>

        {/* Code snippet */}
        <div className="v-card space-y-3">
          <div>
            <p className="v-section-label">Adoption · Drop-in</p>
            <p className="mt-0.5 text-sm font-semibold text-bone">Veklom is OpenAI-compatible</p>
            <p className="text-xs text-muted">Existing OpenAI clients work unchanged — flip one base URL.</p>
          </div>
          <div className="rounded-lg border border-rule bg-ink-2 overflow-hidden">
            <div className="border-b border-rule/50 px-3 py-1.5 flex items-center justify-between">
              <span className="font-mono text-[9px] text-muted">python</span>
              <div className="flex gap-1"><span className="h-2 w-2 rounded-full bg-crimson/60" /><span className="h-2 w-2 rounded-full bg-amber/60" /><span className="h-2 w-2 rounded-full bg-moss/60" /></div>
            </div>
            <pre className="p-4 text-[11px] leading-relaxed overflow-x-auto">
              <code>
                <span className="text-violet">from</span> <span className="text-bone">openai</span> <span className="text-violet">import</span> <span className="text-bone">OpenAI</span>{"\n\n"}
                <span className="text-bone">client</span> <span className="text-muted">=</span> <span className="text-bone">OpenAI(</span>{"\n"}
                <span className="text-bone">{"    "}base_url=</span><span className="text-moss">"https://api.veklom.com/v1"</span><span className="text-bone">,</span>{"\n"}
                <span className="text-bone">{"    "}api_key=os.environ[</span><span className="text-moss">"VEKLOM_API_KEY"</span><span className="text-bone">],</span>{"\n"}
                <span className="text-bone">)</span>{"\n\n"}
                <span className="text-bone">client.chat.completions.create(</span>{"\n"}
                <span className="text-bone">{"    "}model=</span><span className="text-moss">"veklom-llama3-70b"</span><span className="text-bone">,</span>{"\n"}
                <span className="text-bone">{"    "}messages=[{"{"}</span><span className="text-moss">"role"</span><span className="text-bone">:</span><span className="text-moss">"user"</span><span className="text-bone">,</span><span className="text-moss">"content"</span><span className="text-bone">:</span><span className="text-moss">"hi"</span><span className="text-bone">{"}"}],</span>{"\n"}
                <span className="text-bone">)</span>
              </code>
            </pre>
          </div>
          <div className="flex gap-2">
            <button className="v-btn-ghost text-[10px]"><Copy className="h-3 w-3" /> Copy</button>
            <button className="v-btn-ghost text-[10px]"><ExternalLink className="h-3 w-3" /> Vercel guide</button>
          </div>
        </div>
      </div>
    </div>
  );
}
