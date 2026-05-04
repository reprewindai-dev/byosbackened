import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  AlertCircle,
  CheckCircle2,
  FileCheck2,
  Loader2,
  ShieldCheck,
  ShieldAlert,
  ShieldX,
  X,
} from "lucide-react";
import { api } from "@/lib/api";
import { cn, fmtNumber, formatApiDateTime, relativeTime } from "@/lib/cn";

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
  verification_status?: "verified" | "mismatch" | "inconclusive";
  reason?: string | null;
  log_hash: string | null;
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

  const query = useQuery({
    queryKey: ["audit-logs", opType],
    queryFn: () => fetchLogs({ limit: 50, offset: 0, operation_type: opType === "all" ? undefined : opType }),
    refetchInterval: 20_000,
  });

  const stats = useMemo(() => {
    const logs = query.data?.logs ?? [];
    const piiCount = logs.filter((l) => l.pii_detected).length;
    const providers = new Set(logs.map((l) => l.provider).filter(Boolean));
    const totalCost = logs.reduce((sum, l) => sum + (parseFloat(l.cost) || 0), 0);
    return {
      total: query.data?.total ?? 0,
      visible: logs.length,
      piiCount,
      providers: providers.size,
      costUsd: totalCost,
    };
  }, [query.data]);

  return (
    <div className="mx-auto w-full max-w-7xl space-y-6">
      <header>
        <div className="mb-1 font-mono text-[11px] uppercase tracking-[0.15em] text-muted">
          Workspace · Monitoring
        </div>
        <h1 className="text-3xl font-semibold tracking-tight">Tamper-evident audit trail</h1>
        <p className="mt-2 max-w-2xl text-sm text-bone-2">
          Every AI decision writes a hashed audit record. Each record is independently verifiable against its
          signed hash — nothing executed without a receipt.
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          <span className="v-chip v-chip-ok">
            <span className="h-1.5 w-1.5 animate-pulse-soft rounded-full bg-moss" />
            live · <span className="font-mono">/api/v1/audit/logs</span>
          </span>
          <span className="v-chip">auto-refresh 20s</span>
        </div>
      </header>

      <section className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <KpiCell label="Audit entries" value={fmtNumber(stats.total)} />
        <KpiCell label="Shown" value={fmtNumber(stats.visible)} />
        <KpiCell label="PII detected" value={fmtNumber(stats.piiCount)} warn={stats.piiCount > 0} />
        <KpiCell label="Providers active" value={String(stats.providers)} />
      </section>

      <nav className="v-card flex flex-wrap gap-1 p-1">
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
        <div className="v-card flex items-start gap-3 border-crimson/40 bg-crimson/5 p-4 text-sm text-crimson">
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

      <section className="v-card p-0">
        <header className="flex items-center justify-between border-b border-rule px-5 py-3">
          <div>
            <div className="font-mono text-[11px] uppercase tracking-[0.12em] text-muted">Audit log</div>
            <h3 className="mt-0.5 text-sm font-semibold">Hashed, tamper-evident, per-decision</h3>
          </div>
          <span className="v-chip font-mono">{query.isLoading ? "…" : `${stats.visible} entries`}</span>
        </header>

        <table className="w-full text-[13px]">
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
            {query.isLoading && (
              <tr>
                <td colSpan={6} className="px-5 py-8 text-center text-muted">
                  loading…
                </td>
              </tr>
            )}
            {!query.isLoading && query.data?.logs.length === 0 && (
              <tr>
                <td colSpan={6} className="px-5 py-8 text-center text-muted">
                  No audit entries in this window.
                </td>
              </tr>
            )}
            {query.data?.logs.map((l) => (
              <tr key={l.id} className="border-b border-rule/60 last:border-0 hover:bg-ink-2/40">
                <td className="px-5 py-2.5 text-muted">{relativeTime(l.created_at)}</td>
                <td className="px-5 py-2.5">
                  <span className="v-chip font-mono">{l.operation_type}</span>
                </td>
                <td className="px-5 py-2.5 text-bone-2">
                  <span className="text-brass-2">{l.provider || "—"}</span>
                  {" · "}
                  <span className="text-muted">{l.model || "—"}</span>
                </td>
                <td className="px-5 py-2.5">
                  {l.pii_detected ? (
                    <span className="v-chip v-chip-warn">
                      <ShieldAlert className="h-3 w-3" />
                      {(l.pii_types ?? []).join(", ") || "detected"}
                    </span>
                  ) : (
                    <span className="v-chip v-chip-ok">
                      <CheckCircle2 className="h-3 w-3" /> clean
                    </span>
                  )}
                </td>
                <td className="px-5 py-2.5 text-right text-bone">${parseFloat(l.cost || "0").toFixed(4)}</td>
                <td className="px-5 py-2.5 text-right">
                  <button className="v-btn-ghost" onClick={() => setSelected(l)}>
                    <FileCheck2 className="h-3.5 w-3.5" /> Inspect &amp; verify
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {selected && <VerifyDrawer log={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}

function KpiCell({ label, value, warn }: { label: string; value: string; warn?: boolean }) {
  return (
    <div className="v-card p-4">
      <div className="font-mono text-[10px] uppercase tracking-[0.1em] text-muted">{label}</div>
      <div className={cn("mt-1.5 text-2xl font-semibold", warn ? "text-crimson" : "text-bone")}>{value}</div>
    </div>
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
          <div className="font-mono text-[11px] uppercase tracking-[0.12em] text-muted">
            Audit entry
          </div>
          <button
            onClick={onClose}
            className="rounded p-1 text-muted hover:bg-white/5 hover:text-bone"
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </header>

        <div className="space-y-4 px-5 py-5">
          <div className="v-card p-4">
            <div className="mb-2 font-mono text-[10px] uppercase tracking-wider text-muted">ID</div>
            <div className="break-all font-mono text-[12px] text-bone">{log.id}</div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <Cell label="Operation" value={log.operation_type} />
            <Cell label="Provider" value={log.provider || "—"} />
            <Cell label="Model" value={log.model || "—"} />
            <Cell label="Cost" value={`$${parseFloat(log.cost || "0").toFixed(6)}`} />
            <Cell label="When" value={formatApiDateTime(log.created_at)} />
            <Cell label="PII" value={log.pii_detected ? "detected" : "clean"} warn={log.pii_detected} />
          </div>

          <section>
            <div className="mb-2 font-mono text-[11px] uppercase tracking-[0.12em] text-muted">Input preview</div>
            <pre className="max-h-40 overflow-auto rounded-md border border-rule bg-ink-2/60 p-3 font-mono text-[11px] leading-relaxed text-bone-2">
              {log.input_preview || "—"}
            </pre>
          </section>

          <section>
            <div className="mb-2 font-mono text-[11px] uppercase tracking-[0.12em] text-muted">Output preview</div>
            <pre className="max-h-40 overflow-auto rounded-md border border-rule bg-ink-2/60 p-3 font-mono text-[11px] leading-relaxed text-bone-2">
              {log.output_preview || "—"}
            </pre>
          </section>

          <section>
            <div className="mb-2 font-mono text-[11px] uppercase tracking-[0.12em] text-muted">
              Integrity verification
            </div>
            <div className="v-card p-4">
              <div className="mb-3 text-[12px] text-bone-2">
                Recomputes the hash of this record and compares to the stored signature. If they match, the record
                has not been tampered with since it was written.
              </div>
              <button
                className="v-btn-primary w-full"
                onClick={() => verify.mutate()}
                disabled={verify.isPending}
              >
                {verify.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <ShieldCheck className="h-4 w-4" />}
                {verify.isPending ? "Verifying…" : "Verify hash"}
              </button>

              {verify.data && (
                <div
                  className={cn(
                    "mt-3 flex items-start gap-3 rounded-md border p-3 text-[12px]",
                    verify.data.verification_status === "inconclusive"
                      ? "border-brass/40 bg-brass/10 text-brass-2"
                      : verify.data.verified
                      ? "border-moss/40 bg-moss/5 text-moss"
                      : "border-crimson/40 bg-crimson/5 text-crimson",
                  )}
                >
                  {verify.data.verification_status === "inconclusive" ? (
                    <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" />
                  ) : verify.data.verified ? (
                    <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0" />
                  ) : (
                    <ShieldX className="mt-0.5 h-4 w-4 shrink-0" />
                  )}
                  <div>
                    <div className="font-semibold">
                      {verify.data.verification_status === "inconclusive"
                        ? "Verification inconclusive for this legacy record"
                        : verify.data.verified
                        ? "Integrity verified"
                        : "Hash mismatch — record may be tampered"}
                    </div>
                    {verify.data.verification_status === "inconclusive" && (
                      <div className="mt-1 text-[11px] opacity-80">
                        This older entry used a previous hash envelope. New entries use the current verifiable scheme.
                      </div>
                    )}
                    {verify.data.log_hash && (
                      <div className="mt-1 break-all font-mono text-[11px] opacity-80">
                        hash: {verify.data.log_hash}
                      </div>
                    )}
                  </div>
                </div>
              )}

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

function Cell({ label, value, warn }: { label: string; value: string; warn?: boolean }) {
  return (
    <div className="rounded-lg border border-rule p-3">
      <div className="mb-0.5 font-mono text-[10px] uppercase tracking-wider text-muted">{label}</div>
      <div className={cn("break-all text-[13px]", warn ? "text-crimson" : "text-bone")}>{value}</div>
    </div>
  );
}
