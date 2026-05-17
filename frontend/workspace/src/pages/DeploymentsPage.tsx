import { useEffect, useCallback } from "react";
import { Plus, Webhook, Copy, ExternalLink } from "lucide-react";
import { api } from "@/lib/api";

const ENDPOINTS = [
  { name: "chat-prod", url: "https://api.veklom.com/v1/chat/completions", type: "CHAT", model: "veklom-llama3-70b", region: "fsn1-hetz", auth: "API-KEY", rateLimit: "240 rpm / 1.2M tpm", rps: 38.4, errors: "0.20%", status: "LIVE" },
  { name: "embed-rag", url: "https://api.veklom.com/v1/embeddings", type: "EMBEDDING", model: "veklom-bge-large", region: "fra1-hetz", auth: "API-KEY", rateLimit: "600 rpm / 4M tpm", rps: 112.7, errors: "0.00%", status: "LIVE" },
  { name: "code-assist", url: "https://api.veklom.com/v1/completions", type: "COMPLETION", model: "veklom-deepseek-v3", region: "fsn1-hetz", auth: "JWT", rateLimit: "120 rpm", rps: 6.1, errors: "0.10%", status: "LIVE" },
  { name: "patient-intake-pipeline", url: "https://api.veklom.com/p/patient-intake", type: "PIPELINE", model: "veklom-llama3-70b", region: "fsn1-hetz", auth: "API-KEY", rateLimit: "60 rpm", rps: 1.4, errors: "0.00%", status: "LIVE" },
  { name: "nightly-batch-summarize", url: "https://api.veklom.com/v1/batches", type: "BATCH", model: "veklom-mixtral-8x22", region: "ash-aws", auth: "API-KEY", rateLimit: "burst 4× nightly", rps: 0.0, errors: "0.00%", status: "PAUSED" },
  { name: "audit-pii-classifier", url: "https://api.veklom.com/v1/chat/completions", type: "CHAT", model: "veklom-qwen2-72b", region: "fsn1-hetz", auth: "IP-ALLOWLIST", rateLimit: "60 rpm", rps: 0.0, errors: "0.00%", status: "DRAFT" },
];

export function DeploymentsPage() {
  const fetchData = useCallback(async () => {
    try { await api.get("/deployments"); } catch { /* static */ }
  }, []);
  useEffect(() => { fetchData(); }, [fetchData]);

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <p className="v-section-label">Deployments · Endpoints</p>
          <h1 className="mt-1 text-2xl font-bold text-bone">OpenAI-compatible endpoints</h1>
          <p className="mt-1 max-w-2xl text-sm text-muted">
            Chat, completion, embedding, pipeline, and async batch endpoints — each with auth, rate limits, CORS, webhooks, and SDK guides.
          </p>
        </div>
        <div className="flex gap-2">
          <button className="flex items-center gap-1.5 rounded-md border border-rule px-3 py-1.5 text-xs text-muted hover:text-bone"><Webhook className="h-3.5 w-3.5" /> Webhooks</button>
          <button className="v-btn-primary text-xs"><Plus className="h-3.5 w-3.5" /> New endpoint</button>
        </div>
      </div>

      {/* Endpoints table */}
      <div className="v-card-flush">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-rule text-left">
              <th className="px-4 py-2.5 font-mono text-[9px] uppercase text-muted">Endpoint</th>
              <th className="px-3 py-2.5 font-mono text-[9px] uppercase text-muted">Type</th>
              <th className="px-3 py-2.5 font-mono text-[9px] uppercase text-muted">Model</th>
              <th className="px-3 py-2.5 font-mono text-[9px] uppercase text-muted">Region</th>
              <th className="px-3 py-2.5 font-mono text-[9px] uppercase text-muted">Auth</th>
              <th className="px-3 py-2.5 font-mono text-[9px] uppercase text-muted">Rate Limit</th>
              <th className="px-3 py-2.5 font-mono text-[9px] uppercase text-muted">RPS</th>
              <th className="px-3 py-2.5 font-mono text-[9px] uppercase text-muted">Errors</th>
              <th className="px-3 py-2.5 font-mono text-[9px] uppercase text-muted">Status</th>
              <th className="w-8"></th>
            </tr>
          </thead>
          <tbody>
            {ENDPOINTS.map((ep) => (
              <tr key={ep.name} className="border-b border-rule/40 hover:bg-white/[0.02]">
                <td className="px-4 py-2.5">
                  <p className="font-medium text-bone">{ep.name}</p>
                  <p className="font-mono text-[9px] text-muted">{ep.url}</p>
                </td>
                <td className="px-3 py-2.5 text-muted uppercase">{ep.type}</td>
                <td className="px-3 py-2.5 font-mono text-muted">{ep.model}</td>
                <td className="px-3 py-2.5 font-mono text-muted">{ep.region}</td>
                <td className="px-3 py-2.5">
                  <span className={`rounded px-1.5 py-0.5 text-[8px] font-mono font-semibold ${ep.auth === "API-KEY" ? "bg-amber/15 text-amber" : ep.auth === "JWT" ? "bg-electric/15 text-electric" : "bg-moss/15 text-moss"}`}>
                    {ep.auth}
                  </span>
                </td>
                <td className="px-3 py-2.5 font-mono text-muted">{ep.rateLimit}</td>
                <td className="px-3 py-2.5 font-mono text-bone">{ep.rps}</td>
                <td className="px-3 py-2.5 font-mono text-muted">{ep.errors}</td>
                <td className="px-3 py-2.5">
                  <span className={`rounded px-1.5 py-0.5 text-[9px] font-mono font-semibold ${ep.status === "LIVE" ? "bg-moss/20 text-moss" : ep.status === "PAUSED" ? "bg-crimson/20 text-crimson" : "bg-bone/10 text-muted"}`}>
                    ● {ep.status}
                  </span>
                </td>
                <td className="px-2 py-2.5">
                  <span className="text-muted cursor-pointer hover:text-bone">&lt;/&gt;</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Endpoint Detail + Drop-in Code */}
      <div className="grid gap-4 lg:grid-cols-2">
        {/* Detail panel */}
        <div className="v-card">
          <div className="flex items-center gap-2 flex-wrap">
            <p className="v-section-label">Endpoint Detail · CHAT-PROD</p>
          </div>
          <div className="mt-2 flex items-center gap-2 flex-wrap">
            <span className="font-mono text-xs text-bone">https://api.veklom.com/v1/chat/completions</span>
            <span className="rounded bg-moss/15 px-1.5 py-0.5 text-[8px] font-mono text-moss">● LIVE</span>
            <span className="rounded bg-amber/15 px-1.5 py-0.5 text-[8px] font-mono text-amber">HETZNER · PRIMARY</span>
            <span className="rounded bg-electric/15 px-1.5 py-0.5 text-[8px] font-mono text-electric">P50 142 ms</span>
          </div>

          <div className="mt-4 grid grid-cols-3 gap-4">
            <div>
              <p className="font-mono text-[8px] uppercase text-muted">Auth</p>
              <p className="font-mono text-xs text-bone">Bearer · vk_live_8h2x</p>
            </div>
            <div>
              <p className="font-mono text-[8px] uppercase text-muted">Rate</p>
              <p className="font-mono text-xs text-bone">240 rpm · 1.2M tpm</p>
            </div>
            <div>
              <p className="font-mono text-[8px] uppercase text-muted">Timeout</p>
              <p className="font-mono text-xs text-bone">30s · stream OK</p>
            </div>
            <div>
              <p className="font-mono text-[8px] uppercase text-muted">CORS</p>
              <p className="font-mono text-xs text-bone">https://app.acme.io</p>
            </div>
            <div>
              <p className="font-mono text-[8px] uppercase text-muted">IP Allowlist</p>
              <p className="font-mono text-xs text-bone">off</p>
            </div>
            <div>
              <p className="font-mono text-[8px] uppercase text-muted">Webhook</p>
              <p className="font-mono text-xs text-bone">on async only</p>
            </div>
          </div>

          <p className="mt-4 font-mono text-[9px] uppercase text-muted">RPS · Last 24h</p>
          <div className="mt-2 h-16 rounded bg-ink-3/50 overflow-hidden">
            <svg viewBox="0 0 400 60" className="w-full h-full" preserveAspectRatio="none">
              <path d="M0,45 Q50,30 100,35 T200,25 T300,30 T400,20" fill="none" stroke="#e5a832" strokeWidth="2" opacity="0.7" />
            </svg>
          </div>
        </div>

        {/* OpenAI drop-in */}
        <div className="v-card">
          <div className="flex items-center justify-between">
            <div>
              <p className="v-section-label">Adoption · Drop-in</p>
              <p className="mt-0.5 text-sm font-semibold text-bone">Veklom is OpenAI-compatible</p>
            </div>
          </div>
          <p className="mt-2 text-xs text-muted">Existing OpenAI clients work unchanged — flip one base URL.</p>

          <div className="mt-4 rounded-md border border-rule bg-ink-2 p-4 font-mono text-[11px] leading-relaxed text-bone">
            <p className="text-electric">from</p><p> openai <span className="text-electric">import</span> OpenAI</p>
            <p className="mt-2">client = OpenAI(</p>
            <p className="pl-4">base_url=<span className="text-amber">"https://api.veklom.com/v1"</span>,</p>
            <p className="pl-4">api_key=os.environ[<span className="text-amber">"VEKLOM_API_KEY"</span>],</p>
            <p>)</p>
            <p className="mt-2">client.chat.completions.create(</p>
            <p className="pl-4">model=<span className="text-amber">"veklom-llama3-70b"</span>,</p>
            <p className="pl-4">messages=[{"{"}<span className="text-amber">"role"</span>:<span className="text-amber">"user"</span>,<span className="text-amber">"content"</span>:<span className="text-amber">"hi"</span>{"}"}],</p>
            <p>)</p>
          </div>

          <div className="mt-3 flex items-center gap-2">
            <button className="flex items-center gap-1.5 rounded border border-rule px-3 py-1.5 text-xs text-muted hover:text-bone">
              <Copy className="h-3 w-3" /> Copy
            </button>
            <button className="flex items-center gap-1.5 rounded border border-amber/30 bg-amber/10 px-3 py-1.5 text-xs text-amber">
              <ExternalLink className="h-3 w-3" /> Vercel guide
            </button>
            <ExternalLink className="h-3 w-3 text-muted ml-auto cursor-pointer" />
          </div>
        </div>
      </div>
    </div>
  );
}
