import { Calendar, Download, Eye, ExternalLink } from "lucide-react";

const FRAMEWORKS = [
  { name: "HIPAA", status: "Audit-Ready", statusColor: "v-badge-green", pct: 96, controls: 54, evidence: "1,428" },
  { name: "SOC 2 Type II", status: "Continuous", statusColor: "v-badge-green", pct: 92, controls: 67, evidence: "2,940" },
  { name: "PCI-DSS v4", status: "In-Progress", statusColor: "v-badge-amber", pct: 88, controls: 312, evidence: "5,120" },
  { name: "ISO 27001", status: "Audit-Ready", statusColor: "v-badge-green", pct: 94, controls: 114, evidence: "1,180" },
  { name: "GDPR", status: "Continuous", statusColor: "v-badge-electric", pct: 99, controls: 32, evidence: "600" },
  { name: "FedRAMP Moderate", status: "In-Progress", statusColor: "v-badge-amber", pct: 71, controls: 325, evidence: "—" },
];

const CONTROLS = [
  { id: "AC-2", name: "Account management", framework: "NIST AC", lastTest: "12 min", evidence: 14, status: "PASSING" },
  { id: "AU-3", name: "Audit log content", framework: "NIST AU", lastTest: "9 min", evidence: 8, status: "PASSING" },
  { id: "IA-2", name: "Identification & auth", framework: "NIST IA", lastTest: "1 hr", evidence: 12, status: "PASSING" },
  { id: "PHI-1", name: "PHI redaction at gateway", framework: "HIPAA", lastTest: "live", evidence: 38, status: "PASSING" },
  { id: "PCI-3.5", name: "Cardholder data masked", framework: "PCI-DSS v4", lastTest: "1 d", evidence: 4, status: "REVIEW" },
  { id: "SC-13", name: "Cryptographic protection", framework: "FedRAMP", lastTest: "3 hr", evidence: 6, status: "PASSING" },
  { id: "DPA-EU", name: "Data residency · EU only", framework: "GDPR", lastTest: "live", evidence: 22, status: "PASSING" },
];

const PACKAGES = [
  { name: "soc2-q2-2026-evidence.tar.gz", controls: 67, size: "284 MB", hash: "sha256 e6f7...2941" },
  { name: "hipaa-2026-mid-year.tar.gz", controls: 54, size: "142 MB", hash: "sha256 7b02...bf34" },
  { name: "pci-dss-v4-quarterly.tar.gz", controls: 312, size: "612 MB", hash: "sha256 0cf1...0eef" },
];

const SCHEDULES = [
  { freq: "Daily · 02:00 UTC", target: "audit-trail.signed.json → s3://acme-evidence/", active: true },
  { freq: "Weekly · Monday", target: "soc2-evidence-pkg.tar.gz", active: true },
  { freq: "Monthly · 1st", target: "hipaa-evidence-pkg.tar.gz", active: true },
  { freq: "On change", target: "policy-diff.signed.json", active: true },
];

export function CompliancePage() {
  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-start justify-between">
        <div>
          <p className="v-section-label">Compliance Center</p>
          <h1 className="mt-1 text-2xl font-bold text-bone">Operational evidence — not a marketing page</h1>
          <p className="mt-1 text-sm text-muted">
            Pre-wired control mappings across frameworks, continuous evidence collection, and signed auditor packages on demand.
          </p>
        </div>
        <div className="flex gap-2">
          <button className="v-btn-ghost text-xs"><Calendar className="h-3.5 w-3.5" /> Schedule export</button>
          <button className="v-btn-primary text-xs"><Download className="h-3.5 w-3.5" /> Export auditor pkg</button>
        </div>
      </div>

      {/* Framework cards */}
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {FRAMEWORKS.map((fw) => (
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
            <div className="mt-3 h-10 rounded bg-ink-3/50" />
            <div className="mt-3 flex items-center justify-between">
              <span className="font-mono text-[10px] text-muted">Evidence rows: {fw.evidence}</span>
              <button className="text-muted hover:text-bone"><Eye className="h-3.5 w-3.5" /></button>
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
              <th className="px-3 py-2 font-mono text-[9px] uppercase text-muted">Framework</th>
              <th className="px-3 py-2 font-mono text-[9px] uppercase text-muted">Last Test</th>
              <th className="px-3 py-2 font-mono text-[9px] uppercase text-muted">Evidence</th>
              <th className="px-3 py-2 font-mono text-[9px] uppercase text-muted">Status</th>
              <th className="w-8"></th>
            </tr>
          </thead>
          <tbody>
            {CONTROLS.map((c) => (
              <tr key={c.id} className="border-b border-rule/50 hover:bg-ink-3/40">
                <td className="px-4 py-2.5">
                  <span className="font-medium text-bone">{c.id}</span>
                  <span className="ml-1.5 text-muted">· {c.name}</span>
                </td>
                <td className="px-3 py-2.5 text-muted">{c.framework}</td>
                <td className="px-3 py-2.5 text-muted">{c.lastTest}</td>
                <td className="px-3 py-2.5 font-mono text-bone-2">{c.evidence}</td>
                <td className="px-3 py-2.5">
                  <span className={`v-badge ${c.status === "PASSING" ? "v-badge-green" : "v-badge-amber"}`}>● {c.status}</span>
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
            {PACKAGES.map((pkg) => (
              <div key={pkg.name} className="flex items-center justify-between rounded-md border border-rule/50 bg-ink-3/30 px-3 py-2.5">
                <div>
                  <p className="text-xs font-medium text-bone">{pkg.name}</p>
                  <p className="text-[10px] text-muted">{pkg.controls} controls · {pkg.size} · {pkg.hash}</p>
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
