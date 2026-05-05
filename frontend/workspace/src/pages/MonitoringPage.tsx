import { useMemo, useState, type ReactNode } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  AlertCircle,
  Bell,
  CheckCircle2,
  Download,
  FileCheck2,
  Loader2,
  Search,
  ShieldAlert,
  ShieldCheck,
  ShieldX,
  X,
} from "lucide-react";
import { api } from "@/lib/api";
import { cn, dateFromApiTimestamp, fmtNumber, formatApiDateTime, relativeTime } from "@/lib/cn";

interface AuditLog {
  id: string;
  operation_type: string;
  provider: string;
  model: string;
  cost: string;
  pii_detected: boolean;
  pii_types: string[] | null;
  created_at: string;
  input_preview: string;
  output_preview: string;
  latency_ms?: number | null;
  total_latency_ms?: number | null;
  status?: string | null;
  log_hash?: string | null;
}

interface AuditLogsResp {
  total: number;
  offset: number;
  limit: number;
  logs: AuditLog[];
}

interface VerifyResp {
  log_id: string;
  verified: boolean;
  hash_match: boolean;
  verification_status?: "verified" | "verified_legacy" | "mismatch" | "inconclusive";
  verification_scheme?: "current" | "legacy_preflush" | null;
  reason?: string | null;
  log_hash: string | null;
}

interface Bucket {
  label: string;
  primary: number;
  burst: number;
  total: number;
}

async function fetchLogs(params: { operation_type?: string; limit: number; offset: number }) {
  const resp = await api.get<AuditLogsResp>("/audit/logs", { params });
  return resp.data;
}

async function verifyLog(id: string) {
  const resp = await api.get<VerifyResp>(`/audit/verify/${encodeURIComponent(id)}`);
  return resp.data;
}

const OP_TYPES = ["all", "exec", "chat", "completion", "embedding", "tool"] as const;

export function MonitoringPage() {
  const [opType, setOpType] = useState<string>("all");
  const [selected, setSelected] = useState<AuditLog | null>(null);
  const [logSearch, setLogSearch] = useState("");

  const query = useQuery({
    queryKey: ["audit-logs", opType],
    queryFn: () => fetchLogs({ limit: 50, offset: 0, operation_type: opType === "all" ? undefined : opType }),
    refetchInterval: 20_000,
  });

  const logs = query.data?.logs ?? [];
  const filteredLogs = useMemo(() => filterLogs(logs, logSearch), [logs, logSearch]);
  const stats = useMemo(() => summarize(logs), [logs]);
  const throughput = useMemo(() => buildBuckets(logs), [logs]);
  const latencySamples = useMemo(() => logs.map(latencyFor).filter((v): v is number => v !== undefined), [logs]);

  return (
    <div className="mx-auto w-full max-w-[1400px]">
      <PageHeader />

      <section>
        <KpiStrip stats={stats} />

        <div className="mt-4 grid grid-cols-12 gap-4">
          <ThroughputPanel buckets={throughput} />
          <LatencyPanel samples={latencySamples} />
        </div>

        <div className="mt-4 grid grid-cols-12 gap-4">
          <StructuredLogsPanel
            logs={filteredLogs}
            query={logSearch}
            onQuery={setLogSearch}
            loading={query.isLoading}
          />
          <AuditRailPanel logs={filteredLogs} loading={query.isLoading} onSelect={setSelected} />
        </div>

        <AlertsPanel />
      </section>

      <nav className="frame mt-4 flex flex-wrap gap-1 p-1">
        {OP_TYPES.map((op) => (
          <button
            key={op}
            onClick={() => setOpType(op)}
            className={cn(
              "rounded-md px-3 py-1 text-[12px] font-medium transition",
              opType === op ? "bg-brass/15 text-brass-2" : "text-bone-2 hover:bg-white/5 hover:text-bone",
            )}
          >
            {op}
          </button>
        ))}
      </nav>

      {query.isError && (
        <div className="frame mt-4 flex items-start gap-3 border-crimson/40 bg-crimson/5 p-4 text-sm text-crimson">
          <AlertCircle className="mt-0.5 h-4 w-4" />
          <div className="flex-1">
            <div className="font-semibold">Failed to load audit logs</div>
            <div className="mt-0.5 text-xs opacity-80">{(query.error as Error)?.message ?? "Unknown"}</div>
          </div>
          <button className="v-btn-ghost" onClick={() => query.refetch()}>
            Retry
          </button>
        </div>
      )}

      <AuditTable logs={filteredLogs} loading={query.isLoading} total={query.data?.total ?? 0} onSelect={setSelected} />

      {selected && <VerifyDrawer log={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}

function PageHeader() {
  return (
    <header className="mb-5 flex flex-wrap items-start justify-between gap-4">
      <div>
        <div className="text-eyebrow">Monitoring · APM</div>
        <h1 className="font-display mt-1 text-[30px] font-semibold tracking-tight text-bone">
          Real-time observability
        </h1>
        <p className="mt-2 max-w-3xl text-sm text-bone-2">
          Throughput, latency, error rates, and tamper-evident audit logs - one console, one perimeter.
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          <Badge tone="ok" dot>
            live · <span className="font-mono">/api/v1/audit/logs</span>
          </Badge>
          <Badge tone="muted">auto-refresh 20s</Badge>
        </div>
      </div>
      <div className="flex flex-wrap gap-2">
        <button
          className="v-btn-ghost h-8 cursor-not-allowed px-3 text-xs opacity-70"
          disabled
          title="Alert-rule persistence is not wired yet."
        >
          <Bell className="h-3.5 w-3.5" /> Alerts
        </button>
        <button
          className="v-btn-primary h-8 cursor-not-allowed px-3 text-xs opacity-70"
          disabled
          title="Activation required. Free evaluation can inspect runs but cannot export compliance-grade evidence."
        >
          <Download className="h-3.5 w-3.5" /> Export Evidence Pack
        </button>
      </div>
    </header>
  );
}

function KpiStrip({ stats }: { stats: ReturnType<typeof summarize> }) {
  const cards = [
    { label: "Requests / min", value: stats.requestsPerMinute.toFixed(2), delta: `${stats.total} shown`, data: stats.activitySeries },
    { label: "Cost observed", value: `$${stats.totalCost.toFixed(4)}`, delta: "visible logs", data: stats.costSeries },
    { label: "Error rate", value: `${stats.errorRate.toFixed(2)}%`, delta: `${stats.errorCount} errors`, data: stats.errorSeries },
    { label: "PII events", value: fmtNumber(stats.piiCount), delta: `${stats.providers} providers`, data: stats.piiSeries },
  ];
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
      {cards.map((card) => (
        <div key={card.label} className="frame p-3">
          <div className="flex items-center justify-between text-eyebrow">
            {card.label}
            <span className="font-mono text-[10.5px] text-moss">{card.delta}</span>
          </div>
          <div className="font-display text-[18px] font-semibold text-bone">{card.value}</div>
          <div className="mt-1 h-9">
            <MiniLine data={card.data} />
          </div>
        </div>
      ))}
    </div>
  );
}

function ThroughputPanel({ buckets }: { buckets: Bucket[] }) {
  return (
    <div className="frame col-span-12 p-4 lg:col-span-7">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-eyebrow">Throughput</div>
          <div className="font-display text-[14px] text-bone">Primary vs approved fallback - audit events</div>
        </div>
        <Badge tone="ok">healthy</Badge>
      </div>
      <div className="mt-2">
        <AreaChart buckets={buckets} />
      </div>
    </div>
  );
}

function LatencyPanel({ samples }: { samples: number[] }) {
  return (
    <div className="frame col-span-12 p-4 lg:col-span-5">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-eyebrow">Latency · P50 / P95 / P99</div>
          <div className="font-display text-[14px] text-bone">All observed audit rows</div>
        </div>
      </div>
      <div className="mt-2">
        {samples.length ? (
          <BarChart data={samples.slice(-18)} />
        ) : (
          <div className="grid h-[210px] place-items-center rounded-md border border-dashed border-rule bg-ink-1/50 text-center font-mono text-[10px] uppercase tracking-[0.12em] text-muted">
            No latency samples returned by audit logs yet
          </div>
        )}
      </div>
    </div>
  );
}

function StructuredLogsPanel({
  logs,
  query,
  onQuery,
  loading,
}: {
  logs: AuditLog[];
  query: string;
  onQuery: (value: string) => void;
  loading: boolean;
}) {
  return (
    <div className="frame col-span-12 p-4 lg:col-span-7">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="text-eyebrow">Logs · structured</div>
          <div className="font-display text-[14px] text-bone">Search, filter, inspect - PII flagged before write</div>
        </div>
        <label className="flex w-[260px] items-center gap-1.5 rounded-md border border-rule bg-ink-1/70 px-2 py-1">
          <Search className="h-3 w-3 text-muted" />
          <input
            className="w-full bg-transparent text-[12px] text-bone outline-none placeholder:text-muted"
            placeholder="provider:groq operation:ai"
            value={query}
            onChange={(event) => onQuery(event.target.value)}
          />
        </label>
      </div>
      <pre className="mt-3 max-h-[300px] overflow-auto rounded-md border border-rule bg-ink-1/70 p-3 font-mono text-[11px] leading-[1.55] text-bone-2">
        {loading
          ? "loading..."
          : logs.length
            ? logs.map(formatStructuredLine).join("\n")
            : "No structured audit logs in this window."}
      </pre>
    </div>
  );
}

function AuditRailPanel({
  logs,
  loading,
  onSelect,
}: {
  logs: AuditLog[];
  loading: boolean;
  onSelect: (log: AuditLog) => void;
}) {
  return (
    <div className="frame col-span-12 overflow-hidden lg:col-span-5">
      <div className="flex items-center justify-between border-b border-rule/80 px-4 py-3">
        <div>
          <div className="text-eyebrow">Audit log · tamper-evident</div>
          <div className="font-display text-[14px] text-bone">Hash verification</div>
        </div>
        <Badge tone="ok" icon={<ShieldCheck className="h-3 w-3" />}>
          verifiable
        </Badge>
      </div>
      <div className="max-h-[300px] divide-y divide-rule/60 overflow-auto">
        {loading && <div className="px-4 py-8 text-center font-mono text-[12px] text-muted">loading...</div>}
        {!loading && logs.length === 0 && (
          <div className="px-4 py-8 text-center font-mono text-[12px] text-muted">No audit rows in this window.</div>
        )}
        {logs.slice(0, 12).map((log) => (
          <button key={log.id} className="block w-full px-4 py-2.5 text-left hover:bg-white/[0.035]" onClick={() => onSelect(log)}>
            <div className="flex items-center justify-between">
              <span className="font-mono text-[12px] text-bone">{log.operation_type}</span>
              <span className="font-mono text-[10.5px] text-muted">{relativeTime(log.created_at)}</span>
            </div>
            <div className="flex items-center justify-between gap-3 text-[11px] text-muted">
              <span className="truncate">
                {log.provider || "provider unset"} · {log.model || "model unset"}
              </span>
              <span className="font-mono">{(log.log_hash ?? log.id).slice(0, 12)}</span>
            </div>
          </button>
        ))}
      </div>
      <div className="flex items-center justify-between border-t border-rule/80 px-4 py-2 text-[11px] text-muted">
        <span>
          Hash anchor: <span className="font-mono text-bone">{logs[0]?.log_hash?.slice(0, 12) ?? "not available"}</span>
        </span>
        <button className="inline-flex h-7 cursor-not-allowed items-center gap-1 rounded-md px-2 text-muted opacity-70" disabled title="Activation required for signed evidence export.">
          <Download className="h-3.5 w-3.5" /> Export locked
        </button>
      </div>
    </div>
  );
}

function AlertsPanel() {
  return (
    <div className="frame mt-4 p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="text-eyebrow">Alerts · routes & thresholds</div>
          <div className="font-display text-[14px] text-bone">Email · Slack · PagerDuty</div>
        </div>
        <button className="v-btn-ghost h-7 cursor-not-allowed px-2 text-xs opacity-70" disabled title="Alert-rule backend is not wired yet.">
          + New alert
        </button>
      </div>
      <div className="mt-3 rounded-md border border-dashed border-rule bg-ink-1/40 px-4 py-5 text-sm text-bone-2">
        No live alert-rule endpoint is wired yet. This panel is intentionally empty until real alert rules can be read
        and saved.
      </div>
    </div>
  );
}

function AuditTable({
  logs,
  loading,
  total,
  onSelect,
}: {
  logs: AuditLog[];
  loading: boolean;
  total: number;
  onSelect: (log: AuditLog) => void;
}) {
  return (
    <section className="frame mt-4 overflow-hidden">
      <header className="flex items-center justify-between border-b border-rule/80 px-5 py-3">
        <div>
          <div className="text-eyebrow">Audit log</div>
          <h3 className="font-display mt-0.5 text-sm font-semibold text-bone">Hashed, tamper-evident, per-decision</h3>
        </div>
        <Badge tone="muted">{loading ? "loading" : `${logs.length} / ${total} entries`}</Badge>
      </header>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[860px] text-[13px]">
          <thead>
            <tr className="border-b border-rule font-mono text-[10px] uppercase tracking-wider text-muted">
              <th className="px-5 py-2 text-left font-medium">When</th>
              <th className="px-5 py-2 text-left font-medium">Operation</th>
              <th className="px-5 py-2 text-left font-medium">Provider · model</th>
              <th className="px-5 py-2 text-left font-medium">PII</th>
              <th className="px-5 py-2 text-right font-medium">Cost</th>
              <th className="px-5 py-2 text-right font-medium">Action</th>
            </tr>
          </thead>
          <tbody className="font-mono">
            {loading && (
              <tr>
                <td colSpan={6} className="px-5 py-8 text-center text-muted">
                  loading...
                </td>
              </tr>
            )}
            {!loading && logs.length === 0 && (
              <tr>
                <td colSpan={6} className="px-5 py-8 text-center text-muted">
                  No audit entries in this window.
                </td>
              </tr>
            )}
            {logs.map((log) => (
              <tr key={log.id} className="border-b border-rule/60 last:border-0 hover:bg-ink-2/40">
                <td className="px-5 py-2.5 text-muted">{relativeTime(log.created_at)}</td>
                <td className="px-5 py-2.5">
                  <Badge tone="muted">{log.operation_type}</Badge>
                </td>
                <td className="px-5 py-2.5 text-bone-2">
                  <span className="text-brass-2">{log.provider || "-"}</span>
                  {" · "}
                  <span className="text-muted">{log.model || "-"}</span>
                </td>
                <td className="px-5 py-2.5">
                  {log.pii_detected ? (
                    <Badge tone="warn">
                      <ShieldAlert className="h-3 w-3" />
                      {(log.pii_types ?? []).join(", ") || "detected"}
                    </Badge>
                  ) : (
                    <Badge tone="ok">
                      <CheckCircle2 className="h-3 w-3" /> clean
                    </Badge>
                  )}
                </td>
                <td className="px-5 py-2.5 text-right text-bone">${parseFloat(log.cost || "0").toFixed(4)}</td>
                <td className="px-5 py-2.5 text-right">
                  <button className="v-btn-ghost h-8 px-3 text-xs" onClick={() => onSelect(log)}>
                    <FileCheck2 className="h-3.5 w-3.5" /> Inspect & verify
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function VerifyDrawer({ log, onClose }: { log: AuditLog; onClose: () => void }) {
  const verify = useMutation({
    mutationFn: () => verifyLog(log.id),
  });

  return (
    <div className="fixed inset-0 z-50 flex" role="dialog" aria-modal="true">
      <button className="flex-1 bg-black/60 backdrop-blur-sm" onClick={onClose} aria-label="Close" />
      <aside className="flex h-full w-full max-w-2xl flex-col overflow-y-auto border-l border-rule bg-ink-1">
        <header className="sticky top-0 flex items-center justify-between border-b border-rule bg-ink-1/90 px-5 py-3 backdrop-blur">
          <div className="font-mono text-[11px] uppercase tracking-[0.12em] text-muted">Audit entry</div>
          <button onClick={onClose} className="rounded p-1 text-muted hover:bg-white/5 hover:text-bone" aria-label="Close">
            <X className="h-4 w-4" />
          </button>
        </header>

        <div className="space-y-4 px-5 py-5">
          <div className="frame p-4">
            <div className="mb-2 font-mono text-[10px] uppercase tracking-wider text-muted">ID</div>
            <div className="break-all font-mono text-[12px] text-bone">{log.id}</div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <Cell label="Operation" value={log.operation_type} />
            <Cell label="Provider" value={log.provider || "-"} />
            <Cell label="Model" value={log.model || "-"} />
            <Cell label="Cost" value={`$${parseFloat(log.cost || "0").toFixed(6)}`} />
            <Cell label="When" value={formatApiDateTime(log.created_at)} />
            <Cell label="PII" value={log.pii_detected ? "detected" : "clean"} warn={log.pii_detected} />
          </div>

          <PreviewBlock title="Input preview" value={log.input_preview} />
          <PreviewBlock title="Output preview" value={log.output_preview} />

          <section>
            <div className="mb-2 font-mono text-[11px] uppercase tracking-[0.12em] text-muted">Integrity verification</div>
            <div className="frame p-4">
              <div className="mb-3 text-[12px] text-bone-2">
                Recomputes the hash of this record and compares to the stored signature. A match means the record has
                not been tampered with since it was written.
              </div>
              <button className="v-btn-primary w-full" onClick={() => verify.mutate()} disabled={verify.isPending}>
                {verify.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <ShieldCheck className="h-4 w-4" />}
                {verify.isPending ? "Verifying..." : "Verify hash"}
              </button>

              {verify.data && <VerifyResult data={verify.data} />}
              {verify.isError && (
                <div className="mt-3 flex items-start gap-2 rounded-md border border-crimson/40 bg-crimson/5 p-3 text-[12px] text-crimson">
                  <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                  {(verify.error as Error)?.message ?? "Verification failed"}
                </div>
              )}
            </div>
          </section>
        </div>
      </aside>
    </div>
  );
}

function VerifyResult({ data }: { data: VerifyResp }) {
  const inconclusive = data.verification_status === "inconclusive";
  const legacy = data.verification_status === "verified_legacy" || data.verification_scheme === "legacy_preflush";
  const ok = data.verified && !inconclusive;
  return (
    <div
      className={cn(
        "mt-3 flex items-start gap-3 rounded-md border p-3 text-[12px]",
        inconclusive || legacy
          ? "border-brass/40 bg-brass/10 text-brass-2"
          : ok
            ? "border-moss/40 bg-moss/5 text-moss"
            : "border-crimson/40 bg-crimson/5 text-crimson",
      )}
    >
      {inconclusive || legacy ? (
        <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" />
      ) : ok ? (
        <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0" />
      ) : (
        <ShieldX className="mt-0.5 h-4 w-4 shrink-0" />
      )}
      <div>
        <div className="font-semibold">
          {legacy ? "Integrity verified with legacy hash scheme" : inconclusive ? "Verification inconclusive for this legacy record" : ok ? "Integrity verified" : "Hash mismatch - record may be tampered"}
        </div>
        {(inconclusive || legacy) && (
          <div className="mt-1 text-[11px] opacity-80">
            This older entry used a previous hash envelope. New entries use the current verifiable scheme.
          </div>
        )}
        {data.log_hash && <div className="mt-1 break-all font-mono text-[11px] opacity-80">hash: {data.log_hash}</div>}
      </div>
    </div>
  );
}

function summarize(logs: AuditLog[]) {
  const totalCost = logs.reduce((sum, log) => sum + (parseFloat(log.cost) || 0), 0);
  const piiCount = logs.filter((log) => log.pii_detected).length;
  const providers = new Set(logs.map((log) => log.provider).filter(Boolean)).size;
  const errorCount = logs.filter((log) => isErrorLog(log)).length;
  const minutes = activeWindowMinutes(logs);
  const buckets = buildBuckets(logs);
  return {
    total: logs.length,
    requestsPerMinute: logs.length / minutes,
    totalCost,
    piiCount,
    providers,
    errorCount,
    errorRate: logs.length ? (errorCount / logs.length) * 100 : 0,
    activitySeries: buckets.map((bucket) => bucket.total),
    costSeries: bucketCost(logs),
    errorSeries: bucketFlag(logs, isErrorLog),
    piiSeries: bucketFlag(logs, (log) => log.pii_detected),
  };
}

function activeWindowMinutes(logs: AuditLog[]): number {
  const times = logs.map((log) => dateFromApiTimestamp(log.created_at)?.getTime()).filter((time): time is number => Boolean(time));
  if (times.length < 2) return 1;
  return Math.max(1, (Math.max(...times) - Math.min(...times)) / 60000);
}

function buildBuckets(logs: AuditLog[]): Bucket[] {
  const buckets = Array.from({ length: 24 }, (_, index) => ({ label: `${index}`, primary: 0, burst: 0, total: 0 }));
  if (!logs.length) return buckets;
  const sorted = [...logs].sort((a, b) => {
    const at = dateFromApiTimestamp(a.created_at)?.getTime() ?? 0;
    const bt = dateFromApiTimestamp(b.created_at)?.getTime() ?? 0;
    return at - bt;
  });
  sorted.forEach((log, index) => {
    const bucket = buckets[Math.min(23, Math.floor((index / Math.max(1, sorted.length)) * 24))];
    if (isBurstProvider(log.provider)) bucket.burst += 1;
    else bucket.primary += 1;
    bucket.total += 1;
  });
  return buckets;
}

function bucketFlag(logs: AuditLog[], predicate: (log: AuditLog) => boolean): number[] {
  const buckets = Array.from({ length: 20 }, () => 0);
  logs.forEach((log, index) => {
    if (!predicate(log)) return;
    buckets[Math.min(19, Math.floor((index / Math.max(1, logs.length)) * 20))] += 1;
  });
  return buckets;
}

function bucketCost(logs: AuditLog[]): number[] {
  const buckets = Array.from({ length: 20 }, () => 0);
  logs.forEach((log, index) => {
    buckets[Math.min(19, Math.floor((index / Math.max(1, logs.length)) * 20))] += parseFloat(log.cost || "0") || 0;
  });
  return buckets;
}

function filterLogs(logs: AuditLog[], query: string): AuditLog[] {
  const q = query.trim().toLowerCase();
  if (!q) return logs;
  return logs.filter((log) =>
    [log.operation_type, log.provider, log.model, log.status, log.input_preview, log.output_preview]
      .filter(Boolean)
      .some((value) => String(value).toLowerCase().includes(q)),
  );
}

function formatStructuredLine(log: AuditLog): string {
  const date = dateFromApiTimestamp(log.created_at);
  const time = date ? date.toISOString().slice(11, 23) : "--:--:--.---";
  const status = isErrorLog(log) ? "WARN" : "inf ";
  const latency = latencyFor(log);
  const pii = log.pii_detected ? "[PII]" : "[CLEAN]";
  const preview = (log.input_preview || "").replace(/\s+/g, " ").slice(0, 60) || "[no preview]";
  return `${time}  ${status}  ${pad(log.operation_type, 14)} ${pad(log.model || "model", 18)} ${pad(latency ? `${latency}ms` : "--", 7)} ${pii}  "${preview}"  $${parseFloat(log.cost || "0").toFixed(5)}`;
}

function pad(value: string, len: number): string {
  return value.length >= len ? value.slice(0, len) : value.padEnd(len, " ");
}

function latencyFor(log: AuditLog): number | undefined {
  const latency = Number(log.latency_ms ?? log.total_latency_ms);
  return Number.isFinite(latency) && latency > 0 ? latency : undefined;
}

function isErrorLog(log: AuditLog): boolean {
  const text = `${log.status ?? ""} ${log.operation_type}`.toLowerCase();
  return text.includes("error") || text.includes("failed") || text.includes("blocked");
}

function isBurstProvider(provider: string): boolean {
  const p = provider.toLowerCase();
  return p.includes("groq") || p.includes("aws") || p.includes("bedrock");
}

function MiniLine({ data }: { data: number[] }) {
  const points = data.length ? data : [0];
  const max = Math.max(1, ...points);
  const path = points
    .map((value, index) => {
      const x = points.length === 1 ? 80 : (index / (points.length - 1)) * 160;
      const y = 34 - (value / max) * 28;
      return `${index === 0 ? "M" : "L"} ${x.toFixed(2)} ${y.toFixed(2)}`;
    })
    .join(" ");
  return (
    <svg viewBox="0 0 160 40" className="h-full w-full" preserveAspectRatio="none">
      <path d={path} fill="none" stroke="rgba(229,177,110,0.95)" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

function AreaChart({ buckets }: { buckets: Bucket[] }) {
  const max = Math.max(1, ...buckets.map((bucket) => bucket.primary + bucket.burst));
  const line = (key: "primary" | "burst") =>
    buckets
      .map((bucket, index) => {
        const x = buckets.length === 1 ? 400 : (index / (buckets.length - 1)) * 800;
        const y = 210 - (bucket[key] / max) * 190;
        return `${index === 0 ? "M" : "L"} ${x.toFixed(2)} ${y.toFixed(2)}`;
      })
      .join(" ");
  return (
    <svg viewBox="0 0 800 220" className="h-[210px] w-full" preserveAspectRatio="none">
      <path d={line("burst")} fill="none" stroke="rgba(110,168,254,0.9)" strokeWidth="2" />
      <path d={line("primary")} fill="none" stroke="rgba(229,177,110,0.95)" strokeWidth="2.4" />
    </svg>
  );
}

function BarChart({ data }: { data: number[] }) {
  const max = Math.max(1, ...data);
  return (
    <div className="flex h-[210px] items-end gap-1 rounded-md border border-rule bg-ink-1/50 p-3">
      {data.map((value, index) => (
        <div key={index} className="flex flex-1 items-end">
          <div className="w-full rounded-t bg-brass/80" style={{ height: `${Math.max(3, (value / max) * 100)}%` }} />
        </div>
      ))}
    </div>
  );
}

function PreviewBlock({ title, value }: { title: string; value: string }) {
  return (
    <section>
      <div className="mb-2 font-mono text-[11px] uppercase tracking-[0.12em] text-muted">{title}</div>
      <pre className="max-h-40 overflow-auto rounded-md border border-rule bg-ink-2/60 p-3 font-mono text-[11px] leading-relaxed text-bone-2">
        {value || "-"}
      </pre>
    </section>
  );
}

function Cell({ label, value, warn }: { label: string; value: string; warn?: boolean }) {
  return (
    <div className="rounded-lg border border-rule p-3">
      <div className="mb-0.5 font-mono text-[10px] uppercase tracking-wider text-muted">{label}</div>
      <div className={cn("break-all text-[13px]", warn ? "text-crimson" : "text-bone")}>{value}</div>
    </div>
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
