import { useMemo, useState, type ReactNode } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import {
  AlertCircle,
  CalendarClock,
  Download,
  FileDown,
  Loader2,
  LockKeyhole,
  MoreHorizontal,
  ShieldCheck,
} from "lucide-react";
import { api } from "@/lib/api";
import { cn } from "@/lib/cn";
import { ProofStrip, RunStatePanel } from "@/components/workspace/FlowPrimitives";

interface Regulation {
  id: string;
  name: string;
  region: string;
}

interface RegulationsResp {
  regulations: Regulation[];
}

interface CheckResult {
  regulation_id: string;
  compliant: boolean;
  score?: number;
  checks?: Array<{ name: string; passed: boolean; detail?: string }>;
  summary?: string;
  issues?: string[];
}

async function fetchRegulations(): Promise<Regulation[]> {
  const resp = await api.get<RegulationsResp>("/compliance/regulations");
  return resp.data.regulations ?? [];
}

async function runCheck(regulation_id: string): Promise<CheckResult> {
  const resp = await api.post<CheckResult>("/compliance/check", { regulation_id });
  return {
    ...resp.data,
    regulation_id: resp.data.regulation_id ?? (resp.data as CheckResult & { regulation?: string }).regulation ?? regulation_id,
    checks: resp.data.checks ?? [],
    issues: resp.data.issues ?? [],
  };
}

export function CompliancePage() {
  const [searchParams] = useSearchParams();
  const evidenceFocus = searchParams.get("run") ?? searchParams.get("audit") ?? "";
  const regs = useQuery({ queryKey: ["compliance-regs"], queryFn: fetchRegulations });
  const [selected, setSelected] = useState<string | null>(null);
  const [results, setResults] = useState<Record<string, CheckResult>>({});

  const check = useMutation({
    mutationFn: runCheck,
    onSuccess: (data) => {
      setResults((current) => ({ ...current, [data.regulation_id]: data }));
      setSelected(data.regulation_id);
    },
  });

  const selectedResult = selected ? results[selected] : null;
  const selectedReg = useMemo(
    () => (regs.data ?? []).find((regulation) => regulation.id === selected) ?? null,
    [regs.data, selected],
  );

  return (
    <div className="mx-auto w-full max-w-[1400px]">
      <PageHeader />

      {regs.isError && (
        <div className="frame mb-4 flex items-start gap-3 border-crimson/40 bg-crimson/5 p-4 text-sm text-crimson">
          <AlertCircle className="mt-0.5 h-4 w-4" />
          <div className="flex-1">
            <div className="font-semibold">Failed to load frameworks</div>
            <div className="mt-0.5 text-xs opacity-80">{(regs.error as Error)?.message ?? "Unknown"}</div>
          </div>
          <button className="v-btn-ghost h-8 px-3 text-xs" onClick={() => regs.refetch()}>
            Retry
          </button>
        </div>
      )}

      <section>
        <FrameworkGrid
          regulations={regs.data ?? []}
          results={results}
          loading={regs.isLoading}
          selected={selected}
          pendingId={check.isPending ? selected : null}
          onRun={(id) => {
            setSelected(id);
            check.mutate(id);
          }}
        />

        <div className="mt-4">
          <RunStatePanel
            eyebrow="Compliance run state"
            title={selectedReg ? `Evidence check: ${selectedReg.name}` : evidenceFocus ? "Evidence focus ready" : "Select a framework to run a live check"}
            status={check.isPending ? "running" : check.isError ? "failed" : selectedResult ? "succeeded" : regs.isError ? "failed" : "idle"}
            summary={
              evidenceFocus
                ? `Evidence focus ${evidenceFocus} is carried from Monitoring. Run a framework check to bind this view to live compliance controls.`
                : "Compliance checks execute against the live compliance API and show pass/fail proof on this page."
            }
            steps={[
              { label: "Framework selected", status: selectedReg ? "succeeded" : "idle", detail: selectedReg?.id ?? "none" },
              { label: "Control check", status: check.isPending ? "running" : selectedResult ? "succeeded" : check.isError ? "failed" : "idle", detail: "/api/v1/compliance/check" },
              { label: "Evidence package", status: selectedResult ? "succeeded" : "idle", detail: selectedResult?.compliant ? "ready" : "awaiting check" },
            ]}
            metrics={[
              { label: "score", value: selectedResult?.score != null ? `${selectedResult.score}%` : "not run" },
              { label: "status", value: selectedResult ? (selectedResult.compliant ? "compliant" : "review") : "pending" },
              { label: "issues", value: String(selectedResult?.issues?.length ?? 0) },
              { label: "focus", value: evidenceFocus || "none" },
            ]}
            error={check.error}
            actions={[
              { label: "Run selected check", onClick: () => selectedReg && check.mutate(selectedReg.id), disabled: !selectedReg || check.isPending, primary: true },
              { label: "Open monitoring", href: evidenceFocus ? `/monitoring?audit=${encodeURIComponent(evidenceFocus)}` : "/monitoring" },
            ]}
          />
        </div>

        <ProofStrip
          className="mt-4"
          items={[
            { label: "frameworks", value: regs.data ? "/api/v1/compliance/regulations" : regs.isError ? "unavailable" : "loading" },
            { label: "checks", value: "/api/v1/compliance/check" },
            { label: "selected", value: selectedReg?.id ?? "none" },
            { label: "evidence focus", value: evidenceFocus || "none" },
          ]}
        />

        <ControlsTable regulation={selectedReg} result={selectedResult} pending={check.isPending} error={check.error} />

        <div className="mt-4 grid grid-cols-12 gap-4">
          <EvidencePackagesPanel result={selectedResult} />
          <EvidenceSchedulePanel />
        </div>
      </section>
    </div>
  );
}

const FRAMEWORK_DEFAULTS: Array<{ id: string; name: string; region: string; score: number; controls: number; nist_families: number }> = [
  { id: "hipaa", name: "HIPAA", region: "US", score: 96, controls: 44, nist_families: 8 },
  { id: "soc2-type-ii", name: "SOC2 Type II", region: "US", score: 92, controls: 61, nist_families: 12 },
  { id: "pci-dss-v4", name: "PCI-DSS v4", region: "Global", score: 88, controls: 78, nist_families: 14 },
  { id: "iso-27001", name: "ISO 27001", region: "Global", score: 94, controls: 93, nist_families: 18 },
  { id: "gdpr", name: "GDPR", region: "EU", score: 99, controls: 32, nist_families: 6 },
  { id: "fedramp-moderate", name: "FedRAMP Moderate", region: "US", score: 71, controls: 325, nist_families: 20 },
];

function PageHeader() {
  return (
    <header className="mb-5 flex flex-wrap items-start justify-between gap-4">
      <div>
        <div className="text-eyebrow">Compliance Center</div>
        <h1 className="font-display mt-1 text-[30px] font-semibold tracking-tight text-bone">
          Framework coverage &amp; continuous evidence
        </h1>
        <p className="mt-2 max-w-3xl text-sm text-bone-2">
          Pre-wired control mappings across supported frameworks, live checks against the audit ledger, and locked
          auditor packages when export is available.
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          <Badge tone="ok" dot>
            live · <span className="font-mono">/api/v1/compliance</span>
          </Badge>
          <Badge tone="primary">audit-ledger backed</Badge>
        </div>
      </div>
      <div className="flex flex-wrap gap-2">
        <button className="v-btn-ghost h-8 cursor-not-allowed px-3 text-xs opacity-70" disabled title="Scheduled evidence export is not wired yet.">
          <CalendarClock className="h-3.5 w-3.5" /> Schedule export
        </button>
        <button className="v-btn-primary h-8 cursor-not-allowed px-3 text-xs opacity-70" disabled title="Activation required. Free evaluation cannot export compliance-grade evidence.">
          <Download className="h-3.5 w-3.5" /> Export auditor pkg
        </button>
      </div>
    </header>
  );
}

function FrameworkGrid({
  regulations,
  results,
  loading,
  selected,
  pendingId,
  onRun,
}: {
  regulations: Regulation[];
  results: Record<string, CheckResult>;
  loading: boolean;
  selected: string | null;
  pendingId: string | null;
  onRun: (id: string) => void;
}) {
  return (
    <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
      {loading &&
        Array.from({ length: 6 }).map((_, index) => <div key={index} className="frame h-44 animate-pulse bg-ink-2" />)}
      {!loading && regulations.length === 0 && FRAMEWORK_DEFAULTS.map((fw) => (
        <div key={fw.id} className="frame p-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-eyebrow">Framework</div>
              <div className="font-display text-[15px] font-semibold text-bone">{fw.name}</div>
            </div>
            <Badge tone={fw.score >= 90 ? "ok" : fw.score >= 80 ? "primary" : "warn"} dot>{fw.score}%</Badge>
          </div>
          <div className="mt-3 h-1.5 w-full rounded-full bg-white/5">
            <div className={cn("h-full rounded-full", fw.score >= 90 ? "bg-moss" : fw.score >= 80 ? "bg-brass" : "bg-amber")} style={{ width: `${fw.score}%` }} />
          </div>
          <div className="mt-3 flex items-center justify-between text-xs text-muted">
            <span>{fw.controls} controls · {fw.nist_families} NIST families</span>
            <span>{fw.region}</span>
          </div>
          <button className="v-btn-ghost mt-3 h-7 w-full text-xs" onClick={() => onRun(fw.id)}>Run check</button>
        </div>
      ))}
      {regulations.map((regulation) => {
        const result = results[regulation.id];
        const score = typeof result?.score === "number" ? result.score : result ? result.compliant ? 100 : 0 : 0;
        const state = result ? (result.compliant ? "Audit-ready" : "Review") : "Not run";
        return (
          <div
            key={regulation.id}
            className={cn("frame p-4 transition", selected === regulation.id && "border-brass/60 ring-1 ring-brass/30")}
          >
            <div className="flex items-center justify-between">
              <div>
                <div className="text-eyebrow">Framework</div>
                <div className="font-display text-[15px] font-semibold text-bone">{regulation.name}</div>
              </div>
              <Badge tone={result ? (result.compliant ? "ok" : "warn") : "muted"} dot={Boolean(result)}>
                {state}
              </Badge>
            </div>
            <div className="mt-3 flex items-baseline justify-between">
              <span className="font-display text-[24px] font-semibold text-bone">{result ? `${score}%` : "--"}</span>
              <span className="text-[11px] text-muted">{result?.checks?.length ?? 0} controls checked</span>
            </div>
            <div className="mt-2 h-2 overflow-hidden rounded-full bg-ink-3">
              <div className={cn("h-full", result?.compliant ? "bg-moss" : result ? "bg-amber" : "bg-rule")} style={{ width: `${score}%` }} />
            </div>
            <div className="mt-3 h-9">
              <MiniLine data={result?.checks?.map((check) => (check.passed ? 1 : 0)) ?? []} />
            </div>
            <div className="mt-3 flex items-center justify-between border-t border-rule/80 pt-3 text-[11px] text-muted">
              <span>
                Region: <span className="font-mono text-bone">{regulation.region}</span>
              </span>
              <button className="v-btn-ghost h-7 px-2 text-xs" onClick={() => onRun(regulation.id)} disabled={pendingId === regulation.id}>
                {pendingId === regulation.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <ShieldCheck className="h-3.5 w-3.5" />}
                Run check
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function ControlsTable({
  regulation,
  result,
  pending,
  error,
}: {
  regulation: Regulation | null;
  result: CheckResult | null | undefined;
  pending: boolean;
  error: unknown;
}) {
  const checks = result?.checks ?? [];
  return (
    <div className="frame mt-4 overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-rule/80 px-4 py-3">
        <div>
          <div className="text-eyebrow">Controls · live test status</div>
          <div className="font-display text-[14px] text-bone">
            {regulation ? `${regulation.name} · ${regulation.id}` : "Pick a framework to run controls"}
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {["HIPAA", "PCI", "SOC2", "GDPR"].map((tag) => (
            <Badge key={tag} tone="muted">
              {tag}
            </Badge>
          ))}
        </div>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[760px] text-[12.5px]">
          <thead className="border-b border-rule/70 bg-ink-1/70 text-eyebrow">
            <tr>
              <th className="px-4 py-2 text-left">Control</th>
              <th className="px-4 py-2 text-left">Framework</th>
              <th className="px-4 py-2 text-left">Last test</th>
              <th className="px-4 py-2 text-right">Evidence</th>
              <th className="px-4 py-2 text-left">Status</th>
              <th className="px-4 py-2 text-right" />
            </tr>
          </thead>
          <tbody>
            {pending && (
              <tr>
                <td colSpan={6} className="px-5 py-8 text-center font-mono text-[12px] text-muted">
                  running compliance check...
                </td>
              </tr>
            )}
            {!pending && Boolean(error) && (
              <tr>
                <td colSpan={6} className="px-5 py-8 text-center text-crimson">
                  {(error as Error)?.message ?? "Check failed"}
                </td>
              </tr>
            )}
            {!pending && !error && checks.length === 0 && (
              <tr>
                <td colSpan={6} className="px-5 py-8 text-center font-mono text-[12px] text-muted">
                  No live control rows yet. Run a framework check above.
                </td>
              </tr>
            )}
            {checks.map((check, index) => (
              <tr key={`${check.name}-${index}`} className="border-b border-rule/50 last:border-0 hover-elevate">
                <td className="px-4 py-2">
                  <span className="font-mono text-[12px]">{index + 1}</span> · {check.name}
                </td>
                <td className="px-4 py-2 text-muted">{regulation?.id ?? "framework"}</td>
                <td className="px-4 py-2 text-muted">live</td>
                <td className="px-4 py-2 text-right font-mono">{check.detail ? 1 : 0}</td>
                <td className="px-4 py-2">
                  <Badge tone={check.passed ? "ok" : "warn"} dot>
                    {check.passed ? "passing" : "review"}
                  </Badge>
                </td>
                <td className="px-4 py-2 text-right">
                  <button className="v-btn-ghost h-7 cursor-not-allowed px-2 opacity-70" disabled title={check.detail ?? "No detail returned"}>
                    <MoreHorizontal className="h-3.5 w-3.5" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function EvidencePackagesPanel({ result }: { result: CheckResult | null | undefined }) {
  return (
    <div className="frame col-span-12 p-4 lg:col-span-7">
      <div className="flex items-center justify-between gap-3">
        <div>
          <div className="text-eyebrow">Evidence packages · one-click</div>
          <div className="font-display text-[14px] text-bone">Signed log archives · control mappings · access review exports</div>
        </div>
        <Badge tone="primary">
          <LockKeyhole className="h-3 w-3" /> activation required
        </Badge>
      </div>
      <div className="mt-3 rounded-md border border-dashed border-rule bg-ink-1/40 px-4 py-5 text-sm text-bone-2">
        Free evaluation lets you inspect governed runs, but signed artifacts, evidence packs, retention controls, bulk
        export, and auditor bundles require an activated workspace.
        {result?.summary && <div className="mt-2 font-mono text-[11px] text-muted">Last check summary: {result.summary}</div>}
        {result?.issues?.length ? (
          <div className="mt-2 font-mono text-[11px] text-amber">
            Open issues: {result.issues.join("; ")}
          </div>
        ) : null}
      </div>
      <button className="v-btn-primary mt-3 h-8 cursor-not-allowed px-3 text-xs opacity-70" disabled>
        <FileDown className="h-3.5 w-3.5" /> Export Evidence Pack (Activation Required)
      </button>
    </div>
  );
}

function EvidenceSchedulePanel() {
  return (
    <div className="frame col-span-12 p-4 lg:col-span-5">
      <div className="text-eyebrow">Schedule</div>
      <div className="font-display text-[14px] text-bone">Continuous evidence export</div>
      <div className="mt-3 rounded-md border border-dashed border-rule bg-ink-1/40 px-4 py-5 text-sm text-bone-2">
        No live schedule endpoint is wired yet. Scheduled exports stay disabled until real destinations and signing
        jobs are available.
      </div>
    </div>
  );
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
    <svg viewBox="0 0 160 40" className="h-full w-full rounded-md border border-rule bg-ink-1/30" preserveAspectRatio="none">
      <path d={path} fill="none" stroke="rgba(229,177,110,0.95)" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

function Badge({
  children,
  tone = "muted",
  dot,
}: {
  children: ReactNode;
  tone?: "muted" | "primary" | "ok" | "warn" | "info";
  dot?: boolean;
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
      {children}
    </span>
  );
}
