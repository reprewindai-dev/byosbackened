import { useMemo } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertCircle, Box, Cpu, Gauge, Loader2, Zap } from "lucide-react";
import { api } from "@/lib/api";
import { cn, fmtNumber } from "@/lib/cn";

interface ModelEntry {
  slug: string;
  name?: string;
  provider?: string;
  enabled?: boolean;
  context_window?: number;
  input_cost_per_1k?: number;
  output_cost_per_1k?: number;
  quantization?: string;
  host?: string;
  region?: string;
}

interface ModelsResp {
  models?: ModelEntry[];
  items?: ModelEntry[];
}

async function fetchModels(): Promise<ModelEntry[]> {
  const resp = await api.get<ModelsResp | ModelEntry[] | { models?: unknown[]; items?: unknown[] }>("/workspace/models");
  const d = resp.data;
  const raw = Array.isArray(d) ? d : d.models ?? d.items ?? [];
  return raw.map(normalizeModel).filter((model) => Boolean(model.slug));
}

async function toggleModel({ slug, enabled }: { slug: string; enabled: boolean }) {
  await api.patch(`/workspace/models/${encodeURIComponent(slug)}`, { enabled });
}

function normalizeModel(raw: unknown): ModelEntry {
  const row = raw as Record<string, unknown>;
  const costIn = Number(row.input_cost_per_1k ?? row.input_cost_per_1m_tokens ?? 0);
  const costOut = Number(row.output_cost_per_1k ?? row.output_cost_per_1m_tokens ?? 0);
  return {
    slug: String(row.slug ?? row.model_slug ?? row.bedrock_model_id ?? ""),
    name: String(row.name ?? row.display_name ?? row.model_slug ?? row.slug ?? ""),
    provider: row.provider ? String(row.provider) : undefined,
    enabled: row.enabled !== false,
    context_window: Number(row.context_window ?? 0) || undefined,
    input_cost_per_1k: costIn > 1 ? costIn / 1000 : costIn,
    output_cost_per_1k: costOut > 1 ? costOut / 1000 : costOut,
    quantization: row.quantization ? String(row.quantization) : undefined,
    host: row.host ? String(row.host) : row.connected === false ? "not connected" : "connected",
    region: row.region ? String(row.region) : undefined,
  };
}

export function ModelsPage() {
  const qc = useQueryClient();
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["models-fleet"],
    queryFn: fetchModels,
    refetchInterval: 30_000,
  });

  const toggler = useMutation({
    mutationFn: toggleModel,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["models-fleet"] }),
  });

  const stats = useMemo(() => {
    const all = data ?? [];
    const enabled = all.filter((m) => m.enabled);
    const providers = new Set(all.map((m) => m.provider).filter(Boolean));
    const quantized = all.filter((m) => m.quantization).length;
    return {
      total: all.length,
      enabled: enabled.length,
      providers: providers.size,
      quantized,
    };
  }, [data]);

  const groups = useMemo(() => {
    const byProvider = new Map<string, ModelEntry[]>();
    for (const m of data ?? []) {
      const key = m.provider ?? "local";
      const list = byProvider.get(key) ?? [];
      list.push(m);
      byProvider.set(key, list);
    }
    return Array.from(byProvider.entries()).sort(([a], [b]) => a.localeCompare(b));
  }, [data]);

  return (
    <div className="mx-auto w-full max-w-7xl space-y-6">
      <header>
        <div className="mb-1 font-mono text-[11px] uppercase tracking-[0.15em] text-muted">
          Workspace · Models
        </div>
        <h1 className="text-3xl font-semibold tracking-tight">Model fleet</h1>
        <p className="mt-2 max-w-2xl text-sm text-bone-2">
          Governed inventory across Hetzner primary and AWS burst. Toggle availability, inspect unit economics,
          review quantization. All decisions flow through the router in{" "}
          <a href="/overview" className="text-brass-2 hover:underline">Overview</a>.
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          <span className="v-chip v-chip-ok">
            <span className="h-1.5 w-1.5 animate-pulse-soft rounded-full bg-moss" />
            live · <span className="font-mono">/api/v1/workspace/models</span>
          </span>
        </div>
      </header>

      <section className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Kpi icon={<Box className="h-3 w-3" />} label="Total models" value={fmtNumber(stats.total)} />
        <Kpi icon={<Zap className="h-3 w-3" />} label="Enabled" value={fmtNumber(stats.enabled)} />
        <Kpi icon={<Cpu className="h-3 w-3" />} label="Providers" value={String(stats.providers)} />
        <Kpi icon={<Gauge className="h-3 w-3" />} label="Quantized" value={fmtNumber(stats.quantized)} />
      </section>

      {isError && (
        <div className="v-card flex items-start gap-3 border-crimson/40 bg-crimson/5 p-4 text-sm text-crimson">
          <AlertCircle className="mt-0.5 h-4 w-4" />
          <div className="flex-1">
            <div className="font-semibold">Failed to load fleet</div>
            <div className="mt-0.5 text-xs opacity-80">{(error as Error)?.message ?? "Unknown"}</div>
          </div>
          <button className="v-btn-ghost" onClick={() => refetch()}>
            Retry
          </button>
        </div>
      )}

      {isLoading && (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="v-card h-28 animate-pulse bg-ink-2" />
          ))}
        </div>
      )}

      {!isLoading && !isError && groups.length === 0 && (
        <div className="v-card flex flex-col items-center gap-3 px-6 py-16 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-brass/10 text-brass-2">
            <Box className="h-6 w-6" />
          </div>
          <div className="text-lg font-semibold">No models configured</div>
          <p className="max-w-md text-sm text-bone-2">
            Models will appear here once your workspace binds a provider (Ollama, Groq, OpenAI).
          </p>
        </div>
      )}

      {groups.map(([provider, models]) => (
        <section key={provider} className="space-y-3">
          <header className="flex items-center justify-between">
            <h2 className="text-lg font-semibold capitalize text-bone">{provider}</h2>
            <span className="v-chip font-mono">
              {models.filter((m) => m.enabled).length} / {models.length} enabled
            </span>
          </header>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
            {models.map((m) => (
              <div key={m.slug} className="v-card flex flex-col gap-3 p-4">
                <div className="flex items-start justify-between">
                  <div className="flex h-9 w-9 items-center justify-center rounded-md bg-electric/10 text-electric">
                    <Box className="h-4 w-4" />
                  </div>
                  <button
                    onClick={() => toggler.mutate({ slug: m.slug, enabled: !m.enabled })}
                    disabled={toggler.isPending}
                    className={cn(
                      "relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition",
                      m.enabled ? "bg-moss/80" : "bg-rule",
                    )}
                    aria-pressed={m.enabled}
                  >
                    <span
                      className={cn(
                        "inline-block h-5 w-5 translate-x-0.5 transform rounded-full bg-bone shadow transition",
                        m.enabled && "translate-x-5",
                      )}
                    />
                    {toggler.isPending && (
                      <Loader2 className="absolute left-1/2 top-1/2 h-3 w-3 -translate-x-1/2 -translate-y-1/2 animate-spin text-muted" />
                    )}
                  </button>
                </div>
                <div>
                  <div className="truncate text-[15px] font-semibold text-bone">{m.name ?? m.slug}</div>
                  <div className="mt-0.5 font-mono text-[11px] text-muted">{m.slug}</div>
                </div>
                <div className="flex flex-wrap gap-1.5 font-mono text-[10px]">
                  {m.quantization && (
                    <span className="v-chip v-chip-brass">{m.quantization}</span>
                  )}
                  {m.context_window && (
                    <span className="v-chip">ctx {fmtNumber(m.context_window)}</span>
                  )}
                  {m.input_cost_per_1k !== undefined && (
                    <span className="v-chip">
                      in ${m.input_cost_per_1k.toFixed(3)}/1k
                    </span>
                  )}
                  {m.output_cost_per_1k !== undefined && (
                    <span className="v-chip">
                      out ${m.output_cost_per_1k.toFixed(3)}/1k
                    </span>
                  )}
                  {m.host && <span className="v-chip">@ {m.host}</span>}
                </div>
              </div>
            ))}
          </div>
        </section>
      ))}
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
