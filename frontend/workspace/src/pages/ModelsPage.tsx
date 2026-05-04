import { useMemo, useState, type ReactNode } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertCircle,
  ArrowRight,
  Box,
  CheckCircle2,
  GitBranch,
  Grid2X2,
  List,
  Loader2,
  Rocket,
  Search,
  ShieldCheck,
  Upload,
} from "lucide-react";
import { api } from "@/lib/api";
import { cn, fmtNumber } from "@/lib/cn";

interface ModelEntry {
  slug: string;
  name: string;
  provider?: string;
  enabled: boolean;
  connected: boolean;
  context_window?: number;
  input_cost_per_1k?: number;
  output_cost_per_1k?: number;
  quantization?: string;
  host?: string;
  region?: string;
  modality: string;
  family: string;
  license?: string;
  route?: string;
  replicas?: number;
  p50_ms?: number;
  p95_ms?: number;
  features: string[];
  telemetry_series: number[];
}

interface ModelsResp {
  models?: ModelEntry[];
  items?: ModelEntry[];
}

interface SplitEntry {
  from: string;
  to: string;
  split: number;
  deployment: string;
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
  const slug = String(row.slug ?? row.model_slug ?? row.bedrock_model_id ?? "");
  const name = String(row.name ?? row.display_name ?? row.model_slug ?? row.slug ?? slug);
  const provider = row.provider ? String(row.provider) : undefined;
  const status = String(row.status ?? "").toLowerCase();
  const connected = row.connected !== false && status !== "not_connected" && status !== "disconnected";
  const host = row.host ? String(row.host) : connected ? undefined : "not connected";
  const contextWindow = optionalNumber(row.context_window ?? row.context_length ?? row.context);
  const quantization = row.quantization ? String(row.quantization) : undefined;
  const features = toStringArray(row.features ?? row.capabilities ?? row.tags);

  return {
    slug,
    name,
    provider,
    enabled: row.enabled !== false,
    connected,
    context_window: contextWindow,
    input_cost_per_1k: normalizeUnitCost(row.input_cost_per_1k ?? row.input_cost_per_1m_tokens),
    output_cost_per_1k: normalizeUnitCost(row.output_cost_per_1k ?? row.output_cost_per_1m_tokens),
    quantization,
    host,
    region: row.region ? String(row.region) : undefined,
    modality: String(row.modality ?? row.type ?? inferModality(slug, name)),
    family: String(row.family ?? inferFamily(slug, name)),
    license: row.license ? String(row.license) : row.license_type ? String(row.license_type) : undefined,
    route: row.route ? String(row.route) : row.default_route ? String(row.default_route) : inferRoute(provider, host),
    replicas: optionalNumber(row.replicas ?? row.replica_count ?? row.instances),
    p50_ms: optionalNumber(row.p50_latency_ms ?? row.latency_p50_ms ?? row.p50_ms ?? row.p50),
    p95_ms: optionalNumber(row.p95_latency_ms ?? row.latency_p95_ms ?? row.p95_ms ?? row.p95),
    features,
    telemetry_series: toNumberArray(row.telemetry_series ?? row.latency_series ?? row.usage_series),
  };
}

function optionalNumber(value: unknown): number | undefined {
  const n = Number(value);
  return Number.isFinite(n) ? n : undefined;
}

function normalizeUnitCost(value: unknown): number | undefined {
  const n = optionalNumber(value);
  if (n === undefined) return undefined;
  return n > 1 ? n / 1000 : n;
}

function toStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.map((entry) => String(entry)).filter(Boolean);
}

function toNumberArray(value: unknown): number[] {
  if (!Array.isArray(value)) return [];
  return value.map(Number).filter((entry) => Number.isFinite(entry) && entry >= 0);
}

function inferModality(slug: string, name: string): string {
  const text = `${slug} ${name}`.toLowerCase();
  if (text.includes("embed")) return "embedding";
  if (text.includes("vision")) return "vision";
  if (text.includes("whisper") || text.includes("audio")) return "audio-stt";
  if (text.includes("rerank")) return "rerank";
  return "chat";
}

function inferFamily(slug: string, name: string): string {
  const text = (name || slug).split(/[/:@ ]/)[0];
  return text || "model";
}

function inferRoute(provider?: string, host?: string): string | undefined {
  const key = `${provider ?? ""} ${host ?? ""}`.toLowerCase();
  if (!key.trim()) return undefined;
  if (key.includes("ollama") || key.includes("hetzner") || key.includes("local")) return "primary";
  if (key.includes("groq") || key.includes("bedrock") || key.includes("aws")) return "burst";
  return "workspace";
}

export function ModelsPage() {
  const qc = useQueryClient();
  const [search, setSearch] = useState("");
  const [modality, setModality] = useState("all");
  const [provider, setProvider] = useState("all");
  const [view, setView] = useState<"grid" | "table">("grid");

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["models-fleet"],
    queryFn: fetchModels,
    refetchInterval: 30_000,
  });

  const toggler = useMutation({
    mutationFn: toggleModel,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["models-fleet"] }),
  });

  const models = data ?? [];
  const providerOptions = useMemo(() => sortedUnique(models.map((model) => model.provider).filter(Boolean)), [models]);
  const modalityOptions = useMemo(() => sortedUnique(models.map((model) => model.modality).filter(Boolean)), [models]);
  const filteredModels = useMemo(() => {
    const q = search.trim().toLowerCase();
    return models.filter((model) => {
      const matchesSearch =
        !q ||
        model.name.toLowerCase().includes(q) ||
        model.slug.toLowerCase().includes(q) ||
        model.family.toLowerCase().includes(q) ||
        model.features.some((feature) => feature.toLowerCase().includes(q));
      const matchesModality = modality === "all" || model.modality === modality;
      const matchesProvider = provider === "all" || model.provider === provider;
      return matchesSearch && matchesModality && matchesProvider;
    });
  }, [models, modality, provider, search]);

  const stats = useMemo(() => {
    const enabled = models.filter((model) => model.enabled).length;
    const connected = models.filter((model) => model.connected).length;
    const quantized = models.filter((model) => model.quantization).length;
    return {
      total: models.length,
      enabled,
      connected,
      quantized,
      providers: providerOptions.length,
    };
  }, [models, providerOptions.length]);

  const activeSplits = useMemo(() => extractSplits(models), [models]);

  return (
    <div className="mx-auto w-full max-w-[1400px]">
      <PageHeader stats={stats} />

      <section>
        <FilterBar
          search={search}
          onSearch={setSearch}
          modality={modality}
          onModality={setModality}
          provider={provider}
          onProvider={setProvider}
          view={view}
          onView={setView}
          modalities={modalityOptions}
          providers={providerOptions}
        />

        {isError && (
          <div className="frame mb-4 flex items-start gap-3 border-crimson/40 bg-crimson/5 p-4 text-sm text-crimson">
            <AlertCircle className="mt-0.5 h-4 w-4" />
            <div className="flex-1">
              <div className="font-semibold">Failed to load model catalog</div>
              <div className="mt-1 text-xs opacity-80">{(error as Error)?.message ?? "Unknown error"}</div>
            </div>
            <button className="v-btn-ghost h-8 px-3 text-xs" onClick={() => refetch()}>
              Retry
            </button>
          </div>
        )}

        {isLoading && <LoadingGrid />}

        {!isLoading && !isError && filteredModels.length === 0 && (
          <div className="frame flex flex-col items-center gap-3 px-6 py-16 text-center">
            <div className="grid h-12 w-12 place-items-center rounded-xl bg-brass/10 text-brass-2">
              <Box className="h-6 w-6" />
            </div>
            <div className="font-display text-lg font-semibold">No models match this view</div>
            <p className="max-w-md text-sm text-bone-2">
              The backend returned no catalog rows for the current filters. Clear filters or connect another provider.
            </p>
          </div>
        )}

        {!isLoading && !isError && filteredModels.length > 0 && (
          view === "grid" ? (
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
              {filteredModels.map((model) => (
                <ModelCard
                  key={model.slug}
                  model={model}
                  onToggle={() => toggler.mutate({ slug: model.slug, enabled: !model.enabled })}
                  toggling={toggler.isPending}
                />
              ))}
            </div>
          ) : (
            <ModelTable
              models={filteredModels}
              onToggle={(model) => toggler.mutate({ slug: model.slug, enabled: !model.enabled })}
              toggling={toggler.isPending}
            />
          )
        )}

        <VersioningPanel splits={activeSplits} />
      </section>
    </div>
  );
}

function sortedUnique(values: (string | undefined)[]): string[] {
  return Array.from(new Set(values.filter((value): value is string => Boolean(value)))).sort((a, b) =>
    a.localeCompare(b),
  );
}

function extractSplits(models: ModelEntry[]): SplitEntry[] {
  return models.flatMap((model) => {
    const raw = model as ModelEntry & {
      split_from?: string;
      split_to?: string;
      traffic_split_pct?: number;
      deployment_slug?: string;
    };
    if (!raw.split_from || !raw.split_to || raw.traffic_split_pct === undefined) return [];
    return [
      {
        from: raw.split_from,
        to: raw.split_to,
        split: Math.max(0, Math.min(100, Number(raw.traffic_split_pct))),
        deployment: raw.deployment_slug ?? model.slug,
      },
    ];
  });
}

function PageHeader({
  stats,
}: {
  stats: { total: number; enabled: number; connected: number; quantized: number; providers: number };
}) {
  return (
    <header className="mb-5 flex flex-wrap items-start justify-between gap-4">
      <div>
        <div className="text-eyebrow">Models · catalog</div>
        <h1 className="font-display mt-1 text-[30px] font-semibold tracking-tight text-bone">
          Foundation & deployed models
        </h1>
        <p className="mt-2 max-w-3xl text-sm text-bone-2">
          Filter by modality, provider, quantization, license, or feature. Promote, rollback, split traffic, or route
          a model through governed deployments.
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          <Badge tone="ok" dot>
            live · <span className="font-mono">/api/v1/workspace/models</span>
          </Badge>
          <Badge tone="muted">{stats.total} models</Badge>
          <Badge tone="muted">{stats.enabled} enabled</Badge>
          <Badge tone="muted">{stats.connected} connected</Badge>
          <Badge tone="muted">{stats.providers} providers</Badge>
          <Badge tone="muted">{stats.quantized} quantized</Badge>
        </div>
      </div>
      <div className="flex flex-wrap gap-2">
        <DisabledHeaderButton icon={<Upload className="h-3.5 w-3.5" />} label="Upload model" />
        <a href="#/deployments" className="v-btn-primary h-8 px-3 text-xs">
          <Rocket className="h-3.5 w-3.5" /> Deploy from catalog
        </a>
      </div>
    </header>
  );
}

function FilterBar({
  search,
  onSearch,
  modality,
  onModality,
  provider,
  onProvider,
  view,
  onView,
  modalities,
  providers,
}: {
  search: string;
  onSearch: (value: string) => void;
  modality: string;
  onModality: (value: string) => void;
  provider: string;
  onProvider: (value: string) => void;
  view: "grid" | "table";
  onView: (value: "grid" | "table") => void;
  modalities: string[];
  providers: string[];
}) {
  return (
    <div className="frame mb-4">
      <div className="flex flex-wrap items-center gap-2 px-4 py-3">
        <label className="flex min-w-[280px] flex-1 items-center gap-2 rounded-md border border-rule bg-ink-1/70 px-2.5 py-1.5">
          <Search className="h-4 w-4 text-muted" />
          <input
            className="w-full bg-transparent text-[13px] text-bone outline-none placeholder:text-muted"
            placeholder="Search models, family, license..."
            value={search}
            onChange={(event) => onSearch(event.target.value)}
          />
        </label>
        <SelectBox label="Modality" value={modality} onChange={onModality}>
          <option value="all">All modalities</option>
          {modalities.map((entry) => (
            <option key={entry} value={entry}>
              {entry}
            </option>
          ))}
        </SelectBox>
        <SelectBox label="Provider" value={provider} onChange={onProvider}>
          <option value="all">All providers</option>
          {providers.map((entry) => (
            <option key={entry} value={entry}>
              {entry}
            </option>
          ))}
        </SelectBox>
        <div className="flex h-9 rounded-md border border-rule bg-ink-1 p-1">
          <ViewButton active={view === "grid"} onClick={() => onView("grid")} icon={<Grid2X2 className="h-3.5 w-3.5" />}>
            Grid
          </ViewButton>
          <ViewButton active={view === "table"} onClick={() => onView("table")} icon={<List className="h-3.5 w-3.5" />}>
            Table
          </ViewButton>
        </div>
      </div>
    </div>
  );
}

function SelectBox({
  label,
  value,
  onChange,
  children,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  children: ReactNode;
}) {
  return (
    <select
      aria-label={label}
      value={value}
      onChange={(event) => onChange(event.target.value)}
      className="h-9 min-w-[160px] rounded-md border border-rule bg-ink-1 px-2.5 font-mono text-[11px] uppercase tracking-[0.1em] text-bone outline-none focus:border-brass/60"
    >
      {children}
    </select>
  );
}

function ModelCard({
  model,
  onToggle,
  toggling,
}: {
  model: ModelEntry;
  onToggle: () => void;
  toggling: boolean;
}) {
  return (
    <div className="frame group p-4 transition hover:border-brass/30">
      <div className="flex items-start justify-between">
        <div className="min-w-0">
          <div className="text-eyebrow">
            {model.modality} · {model.provider ?? "workspace"}
          </div>
          <div className="font-display truncate text-[15px] font-semibold text-bone">{model.name}</div>
          <div className="mt-0.5 truncate font-mono text-[11px] text-muted">{model.slug}</div>
        </div>
        <div className="grid h-8 w-8 shrink-0 place-items-center rounded-md bg-brass/10 text-brass-2">
          <Box className="h-4 w-4" />
        </div>
      </div>

      <div className="mt-3 grid grid-cols-3 gap-2 text-[11px]">
        <MetricTile label="Context" value={model.context_window ? `${fmtNumber(Math.round(model.context_window / 1000))}K` : "not set"} />
        <MetricTile label="Quant" value={model.quantization ?? "not set"} />
        <MetricTile label="Replicas" value={model.replicas !== undefined ? String(model.replicas) : model.enabled ? "enabled" : "0"} />
        <MetricTile label="P50" value={model.p50_ms !== undefined ? `${model.p50_ms} ms` : "no data"} />
        <MetricTile label="P95" value={model.p95_ms !== undefined ? `${model.p95_ms} ms` : "no data"} />
        <MetricTile
          label="$ / 1K out"
          value={model.output_cost_per_1k !== undefined ? `$${model.output_cost_per_1k.toFixed(3)}` : "not set"}
        />
      </div>

      <div className="mt-3 flex flex-wrap gap-1.5">
        <RouteBadge route={model.route} connected={model.connected} />
        {model.region && <Badge tone="muted">{model.region}</Badge>}
        {model.host && <Badge tone={model.connected ? "muted" : "warn"}>{model.host}</Badge>}
        {model.features.slice(0, 3).map((feature) => (
          <Badge key={feature} tone="muted">
            {feature}
          </Badge>
        ))}
      </div>

      <div className="mt-3 h-9">
        <MiniSeries data={model.telemetry_series} label={model.telemetry_series.length ? "Live telemetry" : "No telemetry yet"} />
      </div>

      <div className="mt-3 flex items-center justify-between border-t border-rule/80 pt-3">
        <div className="max-w-[44%] truncate font-mono text-[10.5px] text-muted">{model.license ?? model.family}</div>
        <div className="flex items-center gap-1">
          <button
            className="inline-flex h-7 cursor-not-allowed items-center gap-1 rounded-md px-2 text-[11.5px] text-muted opacity-70"
            disabled
            title="Version history endpoint is not wired yet."
          >
            <GitBranch className="h-3.5 w-3.5" /> Versions
          </button>
          <a href="#/deployments" className="v-btn-primary h-7 px-2.5 text-[11.5px]">
            Deploy <ArrowRight className="h-3.5 w-3.5" />
          </a>
        </div>
      </div>

      <div className="mt-3 flex items-center justify-between rounded-md border border-rule bg-ink-1/50 px-2.5 py-2">
        <div className="flex items-center gap-2 text-[11px] text-bone-2">
          <span className={cn("h-1.5 w-1.5 rounded-full", model.enabled ? "bg-moss" : "bg-muted")} />
          {model.enabled ? "Available to router" : "Router disabled"}
        </div>
        <ToggleSwitch enabled={model.enabled} disabled={toggling} onClick={onToggle} />
      </div>
    </div>
  );
}

function ModelTable({
  models,
  onToggle,
  toggling,
}: {
  models: ModelEntry[];
  onToggle: (model: ModelEntry) => void;
  toggling: boolean;
}) {
  return (
    <div className="frame overflow-hidden">
      <div className="grid grid-cols-[1.5fr_0.8fr_0.7fr_0.7fr_0.7fr_0.6fr] gap-3 border-b border-rule bg-ink-1/70 px-4 py-2 text-eyebrow">
        <span>Model</span>
        <span>Provider</span>
        <span>Context</span>
        <span>Route</span>
        <span>Cost</span>
        <span>Status</span>
      </div>
      {models.map((model) => (
        <div
          key={model.slug}
          className="grid grid-cols-[1.5fr_0.8fr_0.7fr_0.7fr_0.7fr_0.6fr] items-center gap-3 border-b border-rule/60 px-4 py-3 text-xs last:border-b-0"
        >
          <div className="min-w-0">
            <div className="truncate font-semibold text-bone">{model.name}</div>
            <div className="truncate font-mono text-[11px] text-muted">{model.slug}</div>
          </div>
          <div className="text-bone-2">{model.provider ?? "workspace"}</div>
          <div className="font-mono text-muted">
            {model.context_window ? `${fmtNumber(Math.round(model.context_window / 1000))}K` : "not set"}
          </div>
          <div>
            <RouteBadge route={model.route} connected={model.connected} />
          </div>
          <div className="font-mono text-muted">
            {model.output_cost_per_1k !== undefined ? `$${model.output_cost_per_1k.toFixed(3)}` : "not set"}
          </div>
          <ToggleSwitch enabled={model.enabled} disabled={toggling} onClick={() => onToggle(model)} />
        </div>
      ))}
    </div>
  );
}

function VersioningPanel({ splits }: { splits: SplitEntry[] }) {
  return (
    <div className="frame mt-6 p-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <div className="text-eyebrow">Versioning</div>
          <div className="font-display text-[14px] text-bone">
            A/B traffic split · rollback window · per-version audit lineage
          </div>
        </div>
        <Badge tone={splits.length ? "primary" : "muted"} icon={<ShieldCheck className="h-3 w-3" />}>
          {splits.length ? `${splits.length} active splits` : "no active splits"}
        </Badge>
      </div>

      {splits.length ? (
        <div className="mt-3 grid grid-cols-1 gap-2 lg:grid-cols-2">
          {splits.map((split) => (
            <div key={`${split.from}-${split.to}-${split.deployment}`} className="rounded-md border border-rule bg-ink-1/50 p-3">
              <div className="flex items-center justify-between gap-2 text-[12px]">
                <span className="truncate font-mono text-bone-2">{split.from}</span>
                <ArrowRight className="h-3.5 w-3.5 shrink-0 text-muted" />
                <span className="truncate font-mono text-bone">{split.to}</span>
              </div>
              <div className="mt-2 h-2 overflow-hidden rounded-full bg-ink-3">
                <div className="h-full bg-brass" style={{ width: `${split.split}%` }} />
              </div>
              <div className="mt-1.5 flex items-center justify-between text-[11px] text-muted">
                <span>{split.deployment}</span>
                <span className="font-mono">
                  {split.split}% / {100 - split.split}%
                </span>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="mt-3 rounded-md border border-dashed border-rule bg-ink-1/40 px-4 py-5 text-sm text-bone-2">
          No live split data returned yet. When deployment traffic splits are active, they will render here instead of
          placeholder examples.
        </div>
      )}
    </div>
  );
}

function LoadingGrid() {
  return (
    <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
      {Array.from({ length: 6 }).map((_, index) => (
        <div key={index} className="frame h-64 animate-pulse bg-ink-2" />
      ))}
    </div>
  );
}

function MetricTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-rule bg-ink-1/50 px-2 py-1.5">
      <div className="text-eyebrow">{label}</div>
      <div className="truncate font-mono text-[12px] text-bone">{value}</div>
    </div>
  );
}

function MiniSeries({ data, label }: { data: number[]; label: string }) {
  const points = data.length ? data.slice(-20) : [];
  const max = Math.max(1, ...points);
  const path = points
    .map((value, index) => {
      const x = points.length === 1 ? 100 : (index / (points.length - 1)) * 200;
      const y = 32 - (value / max) * 28;
      return `${index === 0 ? "M" : "L"} ${x.toFixed(2)} ${y.toFixed(2)}`;
    })
    .join(" ");

  return (
    <div className="relative h-full overflow-hidden rounded-md border border-rule bg-ink-1/40">
      {points.length ? (
        <svg viewBox="0 0 200 36" preserveAspectRatio="none" className="h-full w-full">
          <path d={path} fill="none" stroke="rgba(229,177,110,0.95)" strokeWidth="2" strokeLinecap="round" />
        </svg>
      ) : (
        <div className="absolute inset-x-2 top-1/2 h-px bg-rule" />
      )}
      <div className="absolute right-2 top-1/2 -translate-y-1/2 rounded bg-ink-2/80 px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-[0.12em] text-muted">
        {label}
      </div>
    </div>
  );
}

function RouteBadge({ route, connected }: { route?: string; connected: boolean }) {
  const label = route ?? (connected ? "workspace" : "offline");
  const tone = !connected ? "warn" : route === "burst" ? "info" : route === "primary" ? "primary" : "muted";
  return (
    <Badge tone={tone} icon={connected ? <CheckCircle2 className="h-3 w-3" /> : <AlertCircle className="h-3 w-3" />}>
      {label}
    </Badge>
  );
}

function Badge({
  children,
  tone = "muted",
  dot,
  icon,
}: {
  children: ReactNode;
  tone?: "muted" | "primary" | "ok" | "warn" | "info";
  dot?: boolean;
  icon?: ReactNode;
}) {
  return (
    <span
      className={cn(
        "chip",
        tone === "muted" && "border-rule bg-white/[0.02] text-bone-2",
        tone === "primary" && "border-brass/40 bg-brass/5 text-brass-2",
        tone === "ok" && "border-moss/30 bg-moss/5 text-moss",
        tone === "warn" && "border-amber/30 bg-amber/5 text-amber",
        tone === "info" && "border-electric/30 bg-electric/5 text-electric",
      )}
    >
      {dot && <span className="h-1.5 w-1.5 rounded-full bg-current" />}
      {icon}
      {children}
    </span>
  );
}

function ViewButton({
  active,
  onClick,
  icon,
  children,
}: {
  active: boolean;
  onClick: () => void;
  icon: ReactNode;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "inline-flex items-center gap-1.5 rounded px-2.5 text-xs text-muted transition",
        active && "bg-brass/10 text-brass-2",
      )}
    >
      {icon}
      {children}
    </button>
  );
}

function ToggleSwitch({
  enabled,
  disabled,
  onClick,
}: {
  enabled: boolean;
  disabled?: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={cn(
        "relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition disabled:cursor-not-allowed disabled:opacity-60",
        enabled ? "bg-moss/80" : "bg-rule",
      )}
      aria-pressed={enabled}
    >
      <span
        className={cn(
          "inline-block h-5 w-5 translate-x-0.5 transform rounded-full bg-bone shadow transition",
          enabled && "translate-x-5",
        )}
      />
      {disabled && <Loader2 className="absolute left-1/2 top-1/2 h-3 w-3 -translate-x-1/2 -translate-y-1/2 animate-spin text-muted" />}
    </button>
  );
}

function DisabledHeaderButton({ icon, label }: { icon: ReactNode; label: string }) {
  return (
    <button
      className="v-btn-ghost h-8 cursor-not-allowed px-3 text-xs opacity-70"
      disabled
      title="Model upload is not exposed by the backend yet."
    >
      {icon}
      {label}
    </button>
  );
}
