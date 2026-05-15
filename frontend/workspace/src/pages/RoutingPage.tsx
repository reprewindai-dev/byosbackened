import { useState } from "react";
import { Activity, AlertTriangle, RefreshCw, Route, Shield, ToggleLeft, ToggleRight } from "lucide-react";
import { useCircuitBreakerStatus, useProviderRoutes, useResetCircuitBreaker, useUpdateProviderPriority } from "@/hooks/useRouting";
import { cn } from "@/lib/cn";

export function RoutingPage() {
  const routesQ = useProviderRoutes();
  const circuitQ = useCircuitBreakerStatus();
  const updatePriority = useUpdateProviderPriority();
  const resetCB = useResetCircuitBreaker();
  const [resetting, setResetting] = useState<string | null>(null);

  async function handleReset(provider: string) {
    setResetting(provider);
    try { await resetCB.mutateAsync(provider); }
    finally { setResetting(null); }
  }

  return (
    <div>
      <header className="mb-6 border-b border-rule pb-6">
        <div className="text-eyebrow">Infrastructure</div>
        <h1 className="mt-2 text-2xl font-semibold tracking-[-0.035em] text-bone">Provider Routing</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">
          Configure AI provider routing priority, toggle providers on/off, and monitor circuit breaker state in real time.
        </p>
      </header>

      {/* Provider Fleet */}
      <section className="mb-6">
        <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-bone">
          <Route className="h-4 w-4 text-brass" /> Provider Fleet
        </h2>
        {routesQ.isLoading ? (
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="frame h-40 animate-pulse bg-white/[0.02]" />
            ))}
          </div>
        ) : routesQ.isError ? (
          <ErrorBanner message="Could not load routing policy. Backend route is /routing/rules." />
        ) : (
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {(routesQ.data ?? []).map((route) => (
              <div key={route.id} className="frame p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="font-semibold text-bone">{route.name}</div>
                    <div className="mt-0.5 text-xs text-muted">{route.provider} / {route.model}</div>
                  </div>
                  <button
                    type="button"
                    onClick={() => updatePriority.mutate({ provider_id: route.id, priority: route.priority, enabled: !route.enabled })}
                    className="text-muted hover:text-bone"
                    aria-label={route.enabled ? "Disable provider" : "Enable provider"}
                  >
                    {route.enabled ? <ToggleRight className="h-5 w-5 text-moss" /> : <ToggleLeft className="h-5 w-5" />}
                  </button>
                </div>
                <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
                  <Stat label="P50 latency" value={`${route.latency_p50_ms}ms`} />
                  <Stat label="P99 latency" value={`${route.latency_p99_ms}ms`} />
                  <Stat label="Error rate" value={`${route.error_rate_pct.toFixed(1)}%`} tone={route.error_rate_pct > 5 ? "warn" : "ok"} />
                  <Stat label="$/1k tokens" value={`$${route.cost_per_1k_tokens_usd.toFixed(4)}`} />
                </div>
                <div className="mt-3">
                  <CircuitBadge state={route.circuit_state} />
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Circuit Breaker Status */}
      <section>
        <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-bone">
          <Shield className="h-4 w-4 text-brass" /> Circuit Breaker State
        </h2>
        {circuitQ.isLoading ? (
          <div className="frame h-24 animate-pulse bg-white/[0.02]" />
        ) : circuitQ.isError ? (
          <ErrorBanner message="Could not load circuit breaker status." />
        ) : (
          <div className="frame overflow-hidden">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-rule bg-white/[0.02] text-eyebrow">
                <tr>
                  {["Provider", "State", "Failures", "Successes", "Last Change", "Next Retry", "Actions"].map((h) => (
                    <th key={h} className="px-4 py-3">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-rule">
                {(circuitQ.data ?? []).map((cb) => (
                  <tr key={cb.provider} className="hover:bg-white/[0.02]">
                    <td className="px-4 py-3 font-medium text-bone">{cb.provider}</td>
                    <td className="px-4 py-3"><CircuitBadge state={cb.state} /></td>
                    <td className="px-4 py-3 font-mono text-bone-2">{cb.failure_count}</td>
                    <td className="px-4 py-3 font-mono text-bone-2">{cb.success_count}</td>
                    <td className="px-4 py-3 text-muted">{new Date(cb.last_state_change_at).toLocaleString()}</td>
                    <td className="px-4 py-3 text-muted">{cb.next_retry_at ? new Date(cb.next_retry_at).toLocaleString() : "—"}</td>
                    <td className="px-4 py-3">
                      {cb.state !== "closed" && (
                        <button
                          type="button"
                          disabled={resetting === cb.provider}
                          onClick={() => handleReset(cb.provider)}
                          className="flex items-center gap-1.5 rounded-lg border border-rule px-3 py-1.5 text-xs text-bone hover:bg-white/[0.04] disabled:opacity-50"
                        >
                          <RefreshCw className={cn("h-3 w-3", resetting === cb.provider && "animate-spin")} />
                          Reset
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

function CircuitBadge({ state }: { state: string }) {
  return (
    <span className={cn(
      "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide",
      state === "closed" && "bg-moss/15 text-moss",
      state === "open" && "bg-crimson/15 text-crimson",
      state === "half_open" && "bg-brass/15 text-brass-2",
    )}>
      <Activity className="h-2.5 w-2.5" />
      {state.replace("_", " ")}
    </span>
  );
}

function Stat({ label, value, tone }: { label: string; value: string; tone?: "ok" | "warn" }) {
  return (
    <div className="rounded-lg border border-rule bg-ink-1 px-2 py-1.5">
      <div className="text-[9px] uppercase tracking-wide text-muted">{label}</div>
      <div className={cn("mt-0.5 font-mono text-xs font-semibold", tone === "warn" ? "text-brass-2" : "text-bone")}>{value}</div>
    </div>
  );
}

function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="frame flex items-start gap-3 border-crimson/30 bg-crimson/5 p-4 text-sm text-crimson">
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
      <span>{message}</span>
    </div>
  );
}
