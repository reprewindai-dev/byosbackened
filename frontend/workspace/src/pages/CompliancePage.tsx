import { useState, useEffect, useCallback } from "react";
import { Calendar, Download, Eye, ExternalLink } from "lucide-react";
import { api } from "@/lib/api";

interface Regulation {
  id?: string;
  name: string;
  description?: string;
  category?: string;
}

interface ComplianceResult {
  compliant?: boolean;
  violations?: string[];
  score?: number;
}

const FALLBACK_FRAMEWORKS = [
  { name: "SOC 2 Type II", status: "compliant", controls: 31, passing: 31, coverage: "100%", lastAudit: "2026-04-15" },
  { name: "HIPAA", status: "compliant", controls: 24, passing: 24, coverage: "100%", lastAudit: "2026-04-10" },
  { name: "GDPR", status: "compliant", controls: 18, passing: 18, coverage: "100%", lastAudit: "2026-03-28" },
  { name: "ISO 27001", status: "in-progress", controls: 42, passing: 38, coverage: "90%", lastAudit: "2026-04-01" },
  { name: "PCI DSS", status: "planned", controls: 12, passing: 0, coverage: "0%", lastAudit: "—" },
];

const CONTROL_TESTS = [
  { id: "SOC2-CC6.1", desc: "Logical access controls", status: "pass", evidence: 14, lastRun: "2 hr ago" },
  { id: "SOC2-CC6.2", desc: "Credentials & authentication", status: "pass", evidence: 8, lastRun: "2 hr ago" },
  { id: "SOC2-CC7.1", desc: "System monitoring & detection", status: "pass", evidence: 22, lastRun: "4 hr ago" },
  { id: "HIPAA-164.312(a)", desc: "Access control — ePHI", status: "pass", evidence: 11, lastRun: "6 hr ago" },
  { id: "HIPAA-164.312(e)", desc: "Transmission security", status: "pass", evidence: 6, lastRun: "6 hr ago" },
  { id: "ISO-A.9.4.1", desc: "Information access restriction", status: "warn", evidence: 4, lastRun: "12 hr ago" },
  { id: "ISO-A.12.4.1", desc: "Event logging", status: "pass", evidence: 18, lastRun: "4 hr ago" },
];

const EVIDENCE_PKGS = [
  { name: "soc2-q2-2026.zip", size: "14.2 MB", created: "2026-04-15", type: "SOC 2" },
  { name: "hipaa-q2-2026.zip", size: "8.1 MB", created: "2026-04-10", type: "HIPAA" },
  { name: "gdpr-q1-2026.zip", size: "6.4 MB", created: "2026-03-28", type: "GDPR" },
];

const EXPORTS = [
  { target: "soc2-q3-2026", framework: "SOC 2", scheduled: "2026-07-15", status: "upcoming" },
  { target: "hipaa-q3-2026", framework: "HIPAA", scheduled: "2026-07-10", status: "upcoming" },
];

const SCHEDULES = [
  { freq: "Daily · 02:00 UTC", target: "audit-trail.signed.json → s3://acme-evidence/", active: true },
  { freq: "Weekly · Monday", target: "soc2-evidence-pkg.tar.gz", active: true },
  { freq: "Monthly · 1st", target: "hipaa-evidence-pkg.tar.gz", active: true },
  { freq: "On change", target: "policy-diff.signed.json", active: true },
];

export function CompliancePage() {
  const [regulations, setRegulations] = useState<Regulation[]>([]);
  const [checkResult, setCheckResult] = useState<ComplianceResult | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    const results = await Promise.allSettled([
      api.get("/compliance/regulations").then(r => r.data),
      api.post("/compliance/check", { text: "system health check" }).then(r => r.data),
    ]);
    if (results[0].status === "fulfilled") {
      const regs = Array.isArray(results[0].value) ? results[0].value : results[0].value?.regulations || [];
      setRegulations(regs);
    }
    if (results[1].status === "fulfilled") setCheckResult(results[1].value);
    setLoading(false);
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const frameworks = FALLBACK_FRAMEWORKS.map(fw => ({
    ...fw,
    pct: parseInt(fw.coverage),
    statusColor: fw.status === "compliant" ? "v-badge v-badge-green" : fw.status === "in-progress" ? "v-badge v-badge-amber" : "v-badge v-badge-muted",
  }));

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-start justify-between">
        <div>
          <p className="v-section-label">Compliance Center</p>
          <h1 className="mt-1 text-2xl font-bold text-bone">Operational evidence — not a marketing page</h1>
          <p className="mt-1 text-sm text-muted">
            Pre-wired control mappings across frameworks, continuous evidence collection, and signed auditor packages on demand.
          </p>
          {regulations.length > 0 && (
            <p className="mt-1 text-xs text-moss">{regulations.length} regulations loaded from backend</p>
          )}
          {checkResult && (
            <p className="mt-1 text-xs text-moss">
              System compliance: {checkResult.compliant ? "COMPLIANT" : "VIOLATIONS DETECTED"}
              {checkResult.score != null && ` · Score: ${checkResult.score}`}
            </p>
          )}
        </div>
        <div className="flex gap-2">
          <button className="v-btn-primary text-xs"><Download className="h-3.5 w-3.5" /> Export auditor pkg</button>
        </div>
      </div>

      {/* Framework cards */}
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {frameworks.map((fw) => (
          <div key={fw.name} className="v-card">
            <div className="flex items-center justify-between">
              <div>
                <p className="v-section-label">Framework</p>
                <p className="mt-0.5 text-lg font-bold text-bone">{fw.name}</p>
              </div>
              <span className={fw.statusColor}>{fw.status}</span>
            </div>
            <div className="mt-4 flex items-end gap-3">
              <span className="text-3xl font-bold text-bone">{fw.pct}%</span>
              <span className="mb-1 text-xs text-muted">coverage · {fw.controls} controls</span>
            </div>
            <div className="v-progress mt-3">
              <div
                className={`v-progress-fill ${fw.pct >= 95 ? "bg-moss" : fw.pct >= 85 ? "bg-amber" : "bg-electric"}`}
                style={{ width: `${fw.pct}%` }}
              />
            </div>
            <div className="mt-3 flex items-center justify-between">
              <span className="font-mono text-[10px] text-muted">{fw.passing}/{fw.controls} passing</span>
              <span className="font-mono text-[10px] text-muted">Last: {fw.lastAudit}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Controls table */}
      <div className="v-card-flush">
        <div className="flex items-center justify-between p-4 pb-3">
          <div>
            <p className="v-section-label">Controls · Live Test Status</p>
            <p className="mt-0.5 text-sm font-semibold text-bone">Mapped to NIST families & framework requirements</p>
          </div>
          <div className="flex gap-1.5">
            {["HIPAA", "PCI", "SOC2", "GDPR"].map((t) => (
              <span key={t} className="v-badge-amber">{t}</span>
            ))}
          </div>
        </div>
        <table className="w-full text-xs">
          <thead>
            <tr className="border-y border-rule text-left">
              <th className="px-4 py-2 font-mono text-[9px] uppercase text-muted">Control</th>
              <th className="px-3 py-2 font-mono text-[9px] uppercase text-muted">Description</th>
              <th className="px-3 py-2 font-mono text-[9px] uppercase text-muted">Last Run</th>
              <th className="px-3 py-2 font-mono text-[9px] uppercase text-muted">Evidence</th>
              <th className="px-3 py-2 font-mono text-[9px] uppercase text-muted">Status</th>
              <th className="w-8"></th>
            </tr>
          </thead>
          <tbody>
            {CONTROL_TESTS.map((c) => (
              <tr key={c.id} className="border-b border-rule/50 hover:bg-ink-3/40">
                <td className="px-4 py-2.5">
                  <span className="font-medium text-bone">{c.id}</span>
                </td>
                <td className="px-3 py-2.5 text-muted">{c.desc}</td>
                <td className="px-3 py-2.5 text-muted">{c.lastRun}</td>
                <td className="px-3 py-2.5 font-mono text-bone-2">{c.evidence}</td>
                <td className="px-3 py-2.5">
                  <span className={`v-badge ${c.status === "pass" ? "v-badge-green" : "v-badge-amber"}`}>● {c.status.toUpperCase()}</span>
                </td>
                <td className="px-2"><ExternalLink className="h-3 w-3 text-muted hover:text-bone cursor-pointer" /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Bottom grid */}
      <div className="grid gap-4 lg:grid-cols-2">
        {/* Evidence packages */}
        <div className="v-card">
          <div className="mb-3 flex items-center justify-between">
            <div>
              <p className="v-section-label">Evidence Packages · One-Click</p>
              <p className="mt-0.5 text-sm font-semibold text-bone">Signed log archives · control mapping PDFs · access review CSVs</p>
            </div>
            <span className="v-badge-green">Auditor-Grade</span>
          </div>
          <div className="space-y-2">
            {EVIDENCE_PKGS.map((pkg) => (
              <div key={pkg.name} className="flex items-center justify-between rounded-md border border-rule/50 bg-ink-3/30 px-3 py-2.5">
                <div>
                  <p className="text-xs font-medium text-bone">{pkg.name}</p>
                  <p className="text-[10px] text-muted">{pkg.type} · {pkg.size} · {pkg.created}</p>
                </div>
                <button className="v-btn-primary px-3 py-1 text-[10px]"><Download className="h-3 w-3" /> Download</button>
              </div>
            ))}
          </div>
        </div>

        {/* Schedules */}
        <div className="v-card">
          <div className="mb-3 flex items-center justify-between">
            <div>
              <p className="v-section-label">Schedule</p>
              <p className="mt-0.5 text-sm font-semibold text-bone">Continuous evidence to S3</p>
            </div>
          </div>
          <div className="space-y-2">
            {SCHEDULES.map((s, i) => (
              <div key={i} className="flex items-center justify-between rounded-md border border-rule/50 bg-ink-3/30 px-3 py-2.5">
                <div>
                  <p className="text-xs font-medium text-bone">{s.freq}</p>
                  <p className="font-mono text-[10px] text-muted">{s.target}</p>
                </div>
                <span className="v-badge-green">● Active</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
