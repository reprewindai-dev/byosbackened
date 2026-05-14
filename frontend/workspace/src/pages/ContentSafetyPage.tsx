import { useContentSafetyRules, useDecisionTraces, useUpdateContentSafetyRule } from "@/hooks/usePrivacyAndSafety";
import { cn } from "@/lib/cn";
import { Activity, AlertTriangle, Eye } from "lucide-react";
import { useState } from "react";

export function ContentSafetyPage() {
  const rulesQ = useContentSafetyRules();
  const tracesQ = useDecisionTraces();
  const updateRule = useUpdateContentSafetyRule();
  const [selectedTrace, setSelectedTrace] = useState<string | null>(null);

  return (
    <div>
      <header className="mb-6 border-b border-rule pb-6">
        <div className="text-eyebrow">Safety</div>
        <h1 className="mt-2 text-2xl font-semibold tracking-[-0.035em] text-bone">Content Safety & Explainability</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">
          Configure moderation rules and inspect per-decision traces for every AI operation.
        </p>
      </header>

      {/* Moderation Rules */}
      <section className="mb-8">
        <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-bone">
          <AlertTriangle className="h-4 w-4 text-brass" /> Moderation Rules
        </h2>
        {rulesQ.isLoading ? (
          <div className="space-y-2">{Array.from({ length: 4 }).map((_, i) => <div key={i} className="frame h-14 animate-pulse bg-white/[0.02]" />)}</div>
        ) : rulesQ.isError ? (
          <div className="frame border-crimson/30 bg-crimson/5 p-4 text-sm text-crimson">Could not load — /content-safety/rules may not be deployed yet.</div>
        ) : (
          <div className="frame overflow-hidden">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-rule bg-white/[0.02] text-eyebrow">
                <tr>{["Category", "Threshold", "Action", "Triggers (7d)", "Enabled"].map((h) => <th key={h} className="px-4 py-3">{h}</th>)}</tr>
              </thead>
              <tbody className="divide-y divide-rule">
                {(rulesQ.data ?? []).map((rule) => (
                  <tr key={rule.id} className="hover:bg-white/[0.02]">
                    <td className="px-4 py-3 font-medium capitalize text-bone">{rule.category.replace("_", " ")}</td>
                    <td className="px-4 py-3">
                      <select
                        value={rule.threshold}
                        onChange={(e) => updateRule.mutate({ id: rule.id, threshold: e.target.value as typeof rule.threshold })}
                        className="rounded border border-rule bg-transparent px-2 py-1 text-xs text-bone"
                      >
                        <option value="low">Low</option>
                        <option value="medium">Medium</option>
                        <option value="high">High</option>
                      </select>
                    </td>
                    <td className="px-4 py-3">
                      <select
                        value={rule.action}
                        onChange={(e) => updateRule.mutate({ id: rule.id, action: e.target.value as typeof rule.action })}
                        className="rounded border border-rule bg-transparent px-2 py-1 text-xs text-bone"
                      >
                        <option value="block">Block</option>
                        <option value="flag">Flag</option>
                        <option value="redact">Redact</option>
                        <option value="log">Log only</option>
                      </select>
                    </td>
                    <td className="px-4 py-3 font-mono text-bone-2">{rule.triggered_count_7d}</td>
                    <td className="px-4 py-3">
                      <button
                        type="button"
                        onClick={() => updateRule.mutate({ id: rule.id, enabled: !rule.enabled })}
                        className={cn("v-chip", rule.enabled ? "v-chip-ok" : "v-chip-warn")}
                      >
                        {rule.enabled ? "on" : "off"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Decision Traces */}
      <section>
        <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-bone">
          <Activity className="h-4 w-4 text-brass" /> Decision Traces
        </h2>
        {tracesQ.isLoading ? (
          <div className="space-y-2">{Array.from({ length: 5 }).map((_, i) => <div key={i} className="frame h-12 animate-pulse bg-white/[0.02]" />)}</div>
        ) : tracesQ.isError ? (
          <div className="frame border-crimson/30 bg-crimson/5 p-4 text-sm text-crimson">Could not load traces — /explainability/traces may not be deployed yet.</div>
        ) : (tracesQ.data ?? []).length === 0 ? (
          <div className="frame border-dashed p-6 text-center text-sm text-muted">No decision traces recorded yet.</div>
        ) : (
          <div className="frame overflow-hidden">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-rule bg-white/[0.02] text-eyebrow">
                <tr>{["Operation", "Provider / Model", "Decision", "Rules Triggered", "Latency", "At", "Inspect"].map((h) => <th key={h} className="px-4 py-3">{h}</th>)}</tr>
              </thead>
              <tbody className="divide-y divide-rule">
                {(tracesQ.data ?? []).map((trace) => (
                  <tr key={trace.id} className={cn("hover:bg-white/[0.02]", selectedTrace === trace.id && "bg-white/[0.02]")}>
                    <td className="px-4 py-3 font-mono text-xs text-bone-2">{trace.operation}</td>
                    <td className="px-4 py-3 text-muted">{trace.provider} / {trace.model}</td>
                    <td className="px-4 py-3"><DecisionChip decision={trace.policy_decision} /></td>
                    <td className="px-4 py-3 text-muted">{trace.rules_triggered.length > 0 ? trace.rules_triggered.join(", ") : "—"}</td>
                    <td className="px-4 py-3 font-mono text-bone-2">{trace.latency_ms}ms</td>
                    <td className="px-4 py-3 text-muted">{new Date(trace.created_at).toLocaleString()}</td>
                    <td className="px-4 py-3">
                      <button type="button" onClick={() => setSelectedTrace(selectedTrace === trace.id ? null : trace.id)} className="text-muted hover:text-bone">
                        <Eye className="h-4 w-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {selectedTrace && (() => {
              const trace = (tracesQ.data ?? []).find((t) => t.id === selectedTrace);
              if (!trace) return null;
              return (
                <div className="border-t border-rule bg-white/[0.015] p-4">
                  <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">Trace detail — {trace.trace_id}</div>
                  <div className="grid gap-3 text-xs md:grid-cols-2">
                    <div>
                      <div className="mb-1 text-muted">Input preview</div>
                      <div className="rounded-lg border border-rule bg-ink-2 p-2 font-mono text-bone-2">{trace.input_preview}</div>
                    </div>
                    <div>
                      <div className="mb-1 text-muted">Output preview</div>
                      <div className="rounded-lg border border-rule bg-ink-2 p-2 font-mono text-bone-2">{trace.output_preview ?? "blocked / no output"}</div>
                    </div>
                    <div>
                      <div className="mb-1 text-muted">Rules evaluated</div>
                      <div className="flex flex-wrap gap-1">{trace.rules_evaluated.map((r) => <span key={r} className="v-chip">{r}</span>)}</div>
                    </div>
                    <div>
                      <div className="mb-1 text-muted">Rules triggered</div>
                      <div className="flex flex-wrap gap-1">{trace.rules_triggered.length > 0 ? trace.rules_triggered.map((r) => <span key={r} className="v-chip v-chip-err">{r}</span>) : <span className="text-muted">none</span>}</div>
                    </div>
                  </div>
                </div>
              );
            })()}
          </div>
        )}
      </section>
    </div>
  );
}

function DecisionChip({ decision }: { decision: string }) {
  return (
    <span className={cn("v-chip",
      decision === "allow" && "v-chip-ok",
      decision === "block" && "v-chip-err",
      decision === "redact" && "v-chip-warn",
      decision === "flag" && "v-chip-brass",
    )}>{decision}</span>
  );
}
