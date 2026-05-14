import { useState } from "react";
import { AlertTriangle, CheckCircle, ShieldAlert, ShieldCheck, XCircle, Zap } from "lucide-react";
import { useActivateKillSwitch, useDeactivateKillSwitch, useKillSwitchState, useResolveThreat, useThreatEvents, useZeroTrustStatus } from "@/hooks/useSecuritySuite";
import { cn } from "@/lib/cn";

export function SecurityPage() {
  const ztQ = useZeroTrustStatus();
  const threatsQ = useThreatEvents();
  const ksQ = useKillSwitchState();
  const resolveThreat = useResolveThreat();
  const activateKS = useActivateKillSwitch();
  const deactivateKS = useDeactivateKillSwitch();
  const [killReason, setKillReason] = useState("");
  const [showKillForm, setShowKillForm] = useState(false);

  const openThreats = (threatsQ.data ?? []).filter((t) => !t.resolved);

  return (
    <div>
      <header className="mb-6 border-b border-rule pb-6">
        <div className="text-eyebrow">Security</div>
        <h1 className="mt-2 text-2xl font-semibold tracking-[-0.035em] text-bone">Security Suite</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">
          Zero-trust posture, live threat events, and emergency kill switch. Superuser access required for kill switch operations.
        </p>
      </header>

      {/* Kill Switch Banner */}
      {ksQ.data?.active && (
        <div className="frame mb-6 flex items-start justify-between gap-4 border-crimson/50 bg-crimson/10 p-4">
          <div className="flex items-start gap-3">
            <Zap className="mt-0.5 h-5 w-5 shrink-0 text-crimson" />
            <div>
              <div className="font-semibold text-crimson">KILL SWITCH ACTIVE</div>
              <div className="mt-1 text-sm text-muted">Reason: {ksQ.data.reason ?? "unspecified"} · Activated by: {ksQ.data.activated_by ?? "system"}</div>
              <div className="mt-1 text-xs text-muted">Affects: {(ksQ.data.affects ?? []).join(", ")}</div>
            </div>
          </div>
          <button type="button" onClick={() => deactivateKS.mutate()} disabled={deactivateKS.isPending} className="shrink-0 rounded-lg border border-crimson/40 px-4 py-2 text-sm text-crimson hover:bg-crimson/10 disabled:opacity-50">
            {deactivateKS.isPending ? "Deactivating…" : "Deactivate"}
          </button>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Zero Trust Score */}
        <section className="frame p-5">
          <h2 className="mb-4 flex items-center gap-2 text-sm font-semibold text-bone">
            <ShieldCheck className="h-4 w-4 text-brass" /> Zero Trust Posture
          </h2>
          {ztQ.isLoading ? <div className="h-32 animate-pulse rounded-lg bg-white/[0.02]" /> : ztQ.isError ? (
            <div className="text-sm text-crimson">Could not load — /security/zero-trust/status may not be deployed yet.</div>
          ) : (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted">Trust Score</span>
                <span className={cn("text-2xl font-mono font-bold",
                  (ztQ.data?.trust_score ?? 0) >= 80 ? "text-moss" :
                  (ztQ.data?.trust_score ?? 0) >= 50 ? "text-brass-2" : "text-crimson"
                )}>{ztQ.data?.trust_score ?? 0}</span>
              </div>
              <div className="h-1.5 overflow-hidden rounded-full bg-white/[0.06]">
                <div className={cn("h-full rounded-full", (ztQ.data?.trust_score ?? 0) >= 80 ? "bg-moss" : (ztQ.data?.trust_score ?? 0) >= 50 ? "bg-brass" : "bg-crimson")} style={{ width: `${ztQ.data?.trust_score ?? 0}%` }} />
              </div>
              {[
                { label: "MFA enforced", value: ztQ.data?.mfa_enforced },
                { label: "SSO enabled", value: ztQ.data?.sso_enabled },
                { label: "Open threats", value: ztQ.data?.open_threats === 0, display: String(ztQ.data?.open_threats ?? "?") },
                { label: "Policy violations (24h)", value: (ztQ.data?.policy_violations_24h ?? 1) === 0, display: String(ztQ.data?.policy_violations_24h ?? "?") },
              ].map(({ label, value, display }) => (
                <div key={label} className="flex items-center justify-between text-sm">
                  <span className="text-muted">{label}</span>
                  <span className={cn("flex items-center gap-1 font-medium", value ? "text-moss" : "text-crimson")}>
                    {value ? <CheckCircle className="h-3.5 w-3.5" /> : <XCircle className="h-3.5 w-3.5" />}
                    {display ?? (value ? "yes" : "no")}
                  </span>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Threat Events */}
        <section className="frame col-span-2 overflow-hidden">
          <div className="flex items-center justify-between p-4">
            <h2 className="flex items-center gap-2 text-sm font-semibold text-bone">
              <ShieldAlert className="h-4 w-4 text-crimson" />
              Threat Events
              {openThreats.length > 0 && <span className="v-chip v-chip-err">{openThreats.length} open</span>}
            </h2>
          </div>
          {threatsQ.isLoading ? <div className="h-32 animate-pulse bg-white/[0.01]" /> : threatsQ.isError ? (
            <div className="p-4 text-sm text-crimson">Could not load threat events — /security/threats may not be deployed yet.</div>
          ) : (threatsQ.data ?? []).length === 0 ? (
            <div className="px-4 pb-8 pt-4 text-center text-sm text-muted">No threat events detected.</div>
          ) : (
            <table className="w-full text-left text-sm">
              <thead className="border-y border-rule bg-white/[0.02] text-eyebrow">
                <tr>{["Severity", "Type", "Description", "Detected", "Actions"].map((h) => <th key={h} className="px-4 py-3">{h}</th>)}</tr>
              </thead>
              <tbody className="divide-y divide-rule">
                {(threatsQ.data ?? []).map((t) => (
                  <tr key={t.id} className="hover:bg-white/[0.02]">
                    <td className="px-4 py-3"><SeverityChip sev={t.severity} /></td>
                    <td className="px-4 py-3 font-mono text-xs text-bone-2">{t.event_type}</td>
                    <td className="max-w-[280px] truncate px-4 py-3 text-muted">{t.description}</td>
                    <td className="px-4 py-3 text-muted">{new Date(t.detected_at).toLocaleString()}</td>
                    <td className="px-4 py-3">
                      {!t.resolved && (
                        <button type="button" onClick={() => resolveThreat.mutate(t.id)} className="rounded-lg border border-rule px-2.5 py-1 text-xs text-bone hover:bg-white/[0.04]">Resolve</button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      </div>

      {/* Kill Switch Control */}
      {!ksQ.data?.active && (
        <section className="mt-6 frame border-crimson/20 p-5">
          <h2 className="mb-2 flex items-center gap-2 text-sm font-semibold text-bone">
            <Zap className="h-4 w-4 text-crimson" /> Emergency Kill Switch
          </h2>
          <p className="mb-4 text-xs text-muted">Immediately halts all AI execution and governed runs workspace-wide. Requires superuser confirmation.</p>
          {!showKillForm ? (
            <button type="button" onClick={() => setShowKillForm(true)} className="rounded-lg border border-crimson/40 px-4 py-2 text-sm text-crimson hover:bg-crimson/10">
              Activate Kill Switch
            </button>
          ) : (
            <div className="flex items-center gap-3">
              <input
                value={killReason}
                onChange={(e) => setKillReason(e.target.value)}
                placeholder="Reason for activation (required)"
                className="v-input flex-1"
              />
              <button
                type="button"
                disabled={!killReason.trim() || activateKS.isPending}
                onClick={async () => { await activateKS.mutateAsync(killReason); setShowKillForm(false); setKillReason(""); }}
                className="rounded-lg bg-crimson px-4 py-2 text-sm font-semibold text-white hover:bg-crimson/90 disabled:opacity-50"
              >
                {activateKS.isPending ? "Activating…" : "Confirm"}
              </button>
              <button type="button" onClick={() => setShowKillForm(false)} className="v-btn text-sm">Cancel</button>
            </div>
          )}
        </section>
      )}
    </div>
  );
}

function SeverityChip({ sev }: { sev: string }) {
  return (
    <span className={cn("v-chip",
      sev === "critical" && "v-chip-err",
      sev === "high" && "v-chip-err",
      sev === "medium" && "v-chip-warn",
      sev === "low" && "v-chip-ok",
      sev === "info" && "v-chip-brass",
    )}>{sev}</span>
  );
}
