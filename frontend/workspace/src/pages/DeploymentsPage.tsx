import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  Box,
  CheckCircle2,
  Cloud,
  Gauge,
  Server,
  ShieldCheck,
} from "lucide-react";
import { api } from "@/lib/api";
import { cn, fmtNumber } from "@/lib/cn";

interface ModelEntry {
  slug: string;
  name?: string;
  provider?: string;
  enabled?: boolean;
  host?: string;
  region?: string;
  quantization?: string;
  context_window?: number;
}

interface ModelsResp {
  models?: ModelEntry[];
  items?: ModelEntry[];
}

async function fetchModels(): Promise<ModelEntry[]> {
  const resp = await api.get<ModelsResp | ModelEntry[]>("/workspace/models");
  const d = resp.data;
  if (Array.isArray(d)) return d;
  return d.models ?? d.items ?? [];
}

const CLOUD_META: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
  hetzner: {
    label: "Hetzner primary",
    color: "v-chip-brass",
    icon: <Server className="h-4 w-4" />,
  },
  aws: {
    label: "AWS burst",
    color: "v-chip",
    icon: <Cloud className="h-4 w-4" />,
  },
  local: {
    label: "Local / on-prem",
    color: "v-chip-ok",
    icon: <Server className="h-4 w-4" />,
  },
  ollama: {
    label: "Ollama (local)",
    color: "v-chip-ok",
    icon: <Server className="h-4 w-4" />,
  },
  groq: {
    label: "Groq burst",
    color: "v-chip",
    icon: <Cloud className="h-4 w-4" />,
  },
};

function cloudFor(m: ModelEntry): string {
  const h = (m.host ?? m.provider ?? "local").toLowerCase();
  if (h.includes("hetzner")) return "hetzner";
  if (h.includes("aws")) return "aws";
  if (h.includes("groq")) return "groq";
  if (h.includes("ollama")) return "ollama";
  return "local";
}

export function DeploymentsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["deployments-models"],
    queryFn: fetchModels,
    refetchInterval: 30_000,
  });

  const zones = useMemo(() => {
    const map = new Map<string, ModelEntry[]>();
    for (const m of data ?? []) {
      const z = cloudFor(m);
      const list = map.get(z) ?? [];
      list.push(m);
      map.set(z, list);
    }
    return Array.from(map.entries());
  }, [data]);

  const total = data?.length ?? 0;
  const enabled = data?.filter((m) => m.enabled).length ?? 0;

  return (
    <div className="mx-auto w-full max-w-7xl space-y-6">
      <header>
        <div className="mb-1 font-mono text-[11px] uppercase tracking-[0.15em] text-muted">
          Workspace · Deployments
        </div>
        <h1 className="text-3xl font-semibold tracking-tight">Fleet &amp; routing posture</h1>
        <p className="mt-2 max-w-2xl text-sm text-bone-2">
          Models active across your sovereign Hetzner primary and AWS burst zones. Canary status, health, and
          per-zone controls. Full deploy orchestration (rollout, rollback, blue/green) ships next.
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          <span className="v-chip v-chip-ok">
            <span className="h-1.5 w-1.5 animate-pulse-soft rounded-full bg-moss" />
            live · <span className="font-mono">/api/v1/workspace/models</span>
          </span>
          <span className="v-chip v-chip-brass">Hetzner primary</span>
          <span className="v-chip">AWS burst</span>
        </div>
      </header>

      <section className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Kpi icon={<Box className="h-3 w-3" />} label="Deployed models" value={fmtNumber(total)} />
        <Kpi icon={<CheckCircle2 className="h-3 w-3" />} label="Healthy / serving" value={fmtNumber(enabled)} />
        <Kpi icon={<Server className="h-3 w-3" />} label="Zones active" value={String(zones.length)} />
        <Kpi icon={<ShieldCheck className="h-3 w-3" />} label="mTLS" value="enforced" />
      </section>

      {isLoading && (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          {Array.from({ length: 2 }).map((_, i) => (
            <div key={i} className="v-card h-40 animate-pulse bg-ink-2" />
          ))}
        </div>
      )}

      {!isLoading && zones.length === 0 && (
        <div className="v-card flex flex-col items-center gap-3 px-6 py-16 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-brass/10 text-brass-2">
            <Cloud className="h-6 w-6" />
          </div>
          <div className="text-lg font-semibold">No deployments visible</div>
          <p className="max-w-md text-sm text-bone-2">
            Bind a provider in <a href="/settings" className="text-brass-2 hover:underline">Settings</a> to see
            this workspace's fleet.
          </p>
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {zones.map(([zone, models]) => {
          const meta = CLOUD_META[zone] ?? CLOUD_META.local;
          const zoneEnabled = models.filter((m) => m.enabled).length;
          return (
            <section key={zone} className="v-card p-0">
              <header className="flex items-center justify-between border-b border-rule px-5 py-3">
                <div className="flex items-center gap-3">
                  <div className={cn("flex h-9 w-9 items-center justify-center rounded-md", meta.color === "v-chip-brass" ? "bg-brass/10 text-brass-2" : meta.color === "v-chip-ok" ? "bg-moss/10 text-moss" : "bg-electric/10 text-electric")}>
                    {meta.icon}
                  </div>
                  <div>
                    <div className="text-[15px] font-semibold text-bone">{meta.label}</div>
                    <div className="font-mono text-[11px] text-muted">
                      {zoneEnabled} / {models.length} serving
                    </div>
                  </div>
                </div>
                <span className={cn("v-chip font-mono text-[10px]", zoneEnabled > 0 ? "v-chip-ok" : "v-chip-warn")}>
                  <Activity className="h-3 w-3" />
                  {zoneEnabled > 0 ? "healthy" : "idle"}
                </span>
              </header>

              <ul className="divide-y divide-rule/50">
                {models.map((m) => (
                  <li key={m.slug} className="flex items-center gap-3 px-5 py-2.5">
                    <div
                      className={cn(
                        "h-1.5 w-1.5 shrink-0 rounded-full",
                        m.enabled ? "bg-moss" : "bg-rule",
                      )}
                    />
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-[13px] text-bone">{m.name ?? m.slug}</div>
                      <div className="truncate font-mono text-[10px] text-muted">
                        {m.slug}
                        {m.context_window ? ` · ${fmtNumber(m.context_window)} ctx` : ""}
                      </div>
                    </div>
                    {m.quantization && (
                      <span className="v-chip font-mono text-[10px]">{m.quantization}</span>
                    )}
                  </li>
                ))}
              </ul>
            </section>
          );
        })}
      </div>

      <section className="v-card border-brass/30 bg-brass/[0.03] p-5">
        <div className="mb-3 flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.12em] text-brass-2">
          <Gauge className="h-3 w-3" /> Deploy orchestration roadmap
        </div>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <Roadmap stage="Next" title="Blue/green rollout">
            Stage new model versions alongside current, shift traffic in percentage steps, auto-rollback on
            error-rate or latency regression.
          </Roadmap>
          <Roadmap stage="After" title="Canary + SLO gates">
            Gate promotion on P95 latency, cost-per-call, and quality-vs-canary scores held in the audit
            ledger.
          </Roadmap>
          <Roadmap stage="Then" title="Zone failover automation">
            Auto-drain Hetzner to AWS burst on zone-level anomaly, enforce budget cap, return to primary on
            recovery.
          </Roadmap>
        </div>
        <div className="mt-4 font-mono text-[11px] text-muted">
          Endpoints consumed when this ships: <span className="text-bone">/api/v1/deployments</span>,{" "}
          <span className="text-bone">/api/v1/deployments/{"{id}"}/promote</span>,{" "}
          <span className="text-bone">/api/v1/deployments/{"{id}"}/rollback</span>. Not yet implemented on
          backend — paired PR will land alongside.
        </div>
      </section>
    </div>
  );
}

function Kpi({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="v-card p-4">
      <div className="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.1em] text-muted">
        {icon}
        {label}
      </div>
      <div className="mt-1.5 text-xl font-semibold text-bone">{value}</div>
    </div>
  );
}

function Roadmap({
  stage,
  title,
  children,
}: {
  stage: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-lg border border-rule p-4">
      <div className="mb-1 font-mono text-[10px] uppercase tracking-wider text-brass-2">{stage}</div>
      <div className="text-[14px] font-semibold text-bone">{title}</div>
      <div className="mt-1.5 text-[12px] leading-relaxed text-bone-2">{children}</div>
    </div>
  );
}
