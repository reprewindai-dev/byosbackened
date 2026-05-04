import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  AlertCircle,
  CheckCircle2,
  FileDown,
  Globe2,
  Loader2,
  ShieldCheck,
} from "lucide-react";
import { api } from "@/lib/api";
import { cn } from "@/lib/cn";

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

interface ComplianceReport {
  report_id?: string;
  regulation_id?: string;
  generated_at?: string;
  [key: string]: unknown;
}

async function fetchRegulations(): Promise<Regulation[]> {
  const resp = await api.get<RegulationsResp>("/compliance/regulations");
  return resp.data.regulations ?? [];
}

async function runCheck(regulation_id: string): Promise<CheckResult> {
  const resp = await api.post<CheckResult>("/compliance/check", { regulation_id });
  return resp.data;
}

async function generateReport(regulation_id: string): Promise<ComplianceReport> {
  const end = new Date();
  const start = new Date(end);
  start.setDate(start.getDate() - 30);
  const resp = await api.post<ComplianceReport>("/compliance/report", {
    regulation_id,
    start_date: start.toISOString(),
    end_date: end.toISOString(),
  });
  return resp.data;
}

const REGION_COLOR: Record<string, string> = {
  EU: "v-chip-brass",
  US: "",
  UK: "",
  global: "v-chip-ok",
};

export function CompliancePage() {
  const regs = useQuery({ queryKey: ["compliance-regs"], queryFn: fetchRegulations });
  const [selected, setSelected] = useState<string | null>(null);
  const [result, setResult] = useState<CheckResult | null>(null);
  const [evidenceNotice, setEvidenceNotice] = useState<string | null>(null);

  const check = useMutation({
    mutationFn: runCheck,
    onSuccess: (data) => {
      setResult(data);
      setEvidenceNotice(null);
    },
  });

  const report = useMutation({
    mutationFn: generateReport,
    onSuccess: (data) => {
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const href = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = href;
      a.download = `veklom-compliance-${selected ?? "report"}-${new Date().toISOString()}.json`;
      a.click();
      URL.revokeObjectURL(href);
      setEvidenceNotice("Evidence bundle generated and downloaded.");
    },
    onError: (err) => {
      setEvidenceNotice((err as Error)?.message ?? "Failed to generate evidence bundle.");
    },
  });

  return (
    <div className="mx-auto w-full max-w-7xl space-y-6">
      <header>
        <div className="mb-1 font-mono text-[11px] uppercase tracking-[0.15em] text-muted">
          Workspace · Compliance
        </div>
        <h1 className="text-3xl font-semibold tracking-tight">Framework coverage &amp; evidence</h1>
        <p className="mt-2 max-w-2xl text-sm text-bone-2">
          Run live compliance checks against supported frameworks. Every decision is already hashed and
          auditable — generate regulator-ready evidence bundles from the same ledger.
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          <span className="v-chip v-chip-ok">
            <span className="h-1.5 w-1.5 animate-pulse-soft rounded-full bg-moss" />
            live · <span className="font-mono">/api/v1/compliance</span>
          </span>
        </div>
      </header>

      {regs.isError && (
        <div className="v-card flex items-start gap-3 border-crimson/40 bg-crimson/5 p-4 text-sm text-crimson">
          <AlertCircle className="mt-0.5 h-4 w-4" />
          <div className="flex-1">
            <div className="font-semibold">Failed to load frameworks</div>
            <div className="mt-0.5 text-xs opacity-80">{(regs.error as Error)?.message ?? "Unknown"}</div>
          </div>
          <button className="v-btn-ghost" onClick={() => regs.refetch()}>
            Retry
          </button>
        </div>
      )}

      <section>
        <h2 className="mb-3 text-sm font-semibold text-bone-2">Supported frameworks</h2>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
          {regs.isLoading &&
            Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="v-card h-32 animate-pulse bg-ink-2" />
            ))}
          {(regs.data ?? []).map((r) => (
            <button
              key={r.id}
              onClick={() => {
                setSelected(r.id);
                setResult(null);
                check.mutate(r.id);
              }}
              className={cn(
                "v-card flex flex-col gap-3 p-4 text-left transition hover:border-brass/40",
                selected === r.id && "border-brass/60 ring-1 ring-brass/40",
              )}
            >
              <div className="flex items-start justify-between">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-brass/10 text-brass-2">
                  <ShieldCheck className="h-5 w-5" />
                </div>
                <span className={cn("v-chip font-mono", REGION_COLOR[r.region] ?? "")}>
                  <Globe2 className="h-3 w-3" /> {r.region}
                </span>
              </div>
              <div>
                <div className="text-[15px] font-semibold text-bone">{r.name}</div>
                <div className="mt-0.5 font-mono text-[11px] text-muted">{r.id}</div>
              </div>
              <div className="mt-auto text-[12px] text-bone-2">
                Click to run a live compliance check →
              </div>
            </button>
          ))}
        </div>
      </section>

      <section className="v-card p-5">
        <header className="mb-3 flex items-center justify-between">
          <div>
            <div className="font-mono text-[11px] uppercase tracking-[0.12em] text-muted">
              Check result
            </div>
            <h3 className="mt-0.5 text-sm font-semibold">
              {selected ? `Framework: ${selected}` : "Pick a framework above"}
            </h3>
          </div>
          <button
            className="v-btn-ghost"
            disabled={!selected || report.isPending}
            onClick={() => selected && report.mutate(selected)}
          >
            <FileDown className="h-4 w-4" /> Evidence bundle
          </button>
        </header>
        {evidenceNotice && (
          <div className="mb-3 rounded-md border border-moss/30 bg-moss/5 px-3 py-2 text-[12px] text-moss">
            {evidenceNotice}
          </div>
        )}

        {check.isPending && (
          <div className="flex items-center justify-center gap-2 py-6 font-mono text-[12px] text-muted">
            <Loader2 className="h-4 w-4 animate-spin" /> Running compliance check…
          </div>
        )}

        {check.isError && (
          <div className="flex items-start gap-2 rounded-md border border-crimson/40 bg-crimson/5 p-3 text-[12px] text-crimson">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            {(check.error as Error)?.message ?? "Check failed"}
          </div>
        )}

        {!check.isPending && !result && !check.isError && (
          <div className="py-6 text-center font-mono text-[12px] text-muted">
            No check run yet.
          </div>
        )}

        {result && (
          <div className="space-y-4">
            <div
              className={cn(
                "flex items-center gap-3 rounded-lg border p-4",
                result.compliant
                  ? "border-moss/40 bg-moss/5 text-moss"
                  : "border-crimson/40 bg-crimson/5 text-crimson",
              )}
            >
              {result.compliant ? (
                <CheckCircle2 className="h-5 w-5" />
              ) : (
                <AlertCircle className="h-5 w-5" />
              )}
              <div className="flex-1">
                <div className="text-[15px] font-semibold">
                  {result.compliant ? "Compliant" : "Gaps detected"}
                </div>
                {result.summary && <div className="mt-0.5 text-[12px] opacity-80">{result.summary}</div>}
              </div>
              {typeof result.score === "number" && (
                <div className="text-right font-mono">
                  <div className="text-[10px] uppercase tracking-wider opacity-60">score</div>
                  <div className="text-xl font-semibold">{result.score}%</div>
                </div>
              )}
            </div>

            {result.checks && result.checks.length > 0 && (
              <div>
                <div className="mb-2 font-mono text-[11px] uppercase tracking-[0.12em] text-muted">
                  Individual checks
                </div>
                <ul className="space-y-1.5">
                  {result.checks.map((c, i) => (
                    <li
                      key={i}
                      className="flex items-start gap-2 rounded-md border border-rule px-3 py-2 font-mono text-[12px]"
                    >
                      {c.passed ? (
                        <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-moss" />
                      ) : (
                        <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-crimson" />
                      )}
                      <div className="flex-1">
                        <div className="text-bone">{c.name}</div>
                        {c.detail && <div className="mt-0.5 text-muted">{c.detail}</div>}
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {result.issues && result.issues.length > 0 && (
              <div>
                <div className="mb-2 font-mono text-[11px] uppercase tracking-[0.12em] text-muted">
                  Issues
                </div>
                <ul className="space-y-1 font-mono text-[12px] text-crimson">
                  {result.issues.map((i, idx) => (
                    <li key={idx} className="flex items-start gap-2">
                      <span className="mt-0.5">•</span>
                      {i}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </section>
    </div>
  );
}
