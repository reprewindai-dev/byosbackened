import { useDismissInsight, useInsights, useMarkInsightRead, useRespondToSuggestion, useSuggestions } from "@/hooks/useInsights";
import { cn } from "@/lib/cn";
import { CheckCircle, Lightbulb, Sparkles, TrendingUp, X } from "lucide-react";

export function InsightsPage() {
  const insightsQ = useInsights();
  const suggestionsQ = useSuggestions();
  const dismissInsight = useDismissInsight();
  const markRead = useMarkInsightRead();
  const respond = useRespondToSuggestion();

  const unread = (insightsQ.data ?? []).filter((i) => !i.read && !i.dismissed);
  const active = (insightsQ.data ?? []).filter((i) => !i.dismissed);
  const pending = (suggestionsQ.data ?? []).filter((s) => s.accepted === null);

  return (
    <div>
      <header className="mb-6 border-b border-rule pb-6">
        <div className="text-eyebrow">Intelligence</div>
        <h1 className="mt-2 text-2xl font-semibold tracking-[-0.035em] text-bone">Insights & Suggestions</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">
          AI-generated workspace intelligence — cost signals, latency anomalies, compliance drift, and actionable suggestions.
        </p>
        <div className="mt-4 flex gap-2">
          {unread.length > 0 && <span className="v-chip v-chip-err">{unread.length} unread</span>}
          {pending.length > 0 && <span className="v-chip v-chip-warn">{pending.length} suggestions pending</span>}
        </div>
      </header>

      {/* Insights */}
      <section className="mb-8">
        <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-bone">
          <Lightbulb className="h-4 w-4 text-brass" /> Workspace Insights
        </h2>
        {insightsQ.isLoading ? (
          <div className="space-y-2">{Array.from({ length: 4 }).map((_, i) => <div key={i} className="frame h-20 animate-pulse bg-white/[0.02]" />)}</div>
        ) : insightsQ.isError ? (
          <div className="frame border-crimson/30 bg-crimson/5 p-4 text-sm text-crimson">Could not load insights — /insights may not be deployed yet.</div>
        ) : active.length === 0 ? (
          <div className="frame border-dashed p-8 text-center text-sm text-muted">
            <Sparkles className="mx-auto mb-3 h-7 w-7 text-muted" />
            No active insights. Keep running — intelligence accumulates over time.
          </div>
        ) : (
          <div className="space-y-2">
            {active.map((insight) => (
              <div
                key={insight.id}
                className={cn("frame p-4", !insight.read && "border-brass/30")}
                onClick={() => { if (!insight.read) markRead.mutate(insight.id); }}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <ImpactChip impact={insight.impact} />
                      <span className="v-chip capitalize">{insight.category}</span>
                      {!insight.read && <span className="h-1.5 w-1.5 rounded-full bg-brass" />}
                    </div>
                    <div className="mt-2 font-semibold text-bone">{insight.title}</div>
                    <div className="mt-1 text-sm text-muted">{insight.body}</div>
                    {insight.action_url && (
                      <a href={insight.action_url} className="mt-2 inline-flex items-center gap-1 text-xs text-brass-2 hover:underline">Take action →</a>
                    )}
                  </div>
                  <button type="button" onClick={(e) => { e.stopPropagation(); dismissInsight.mutate(insight.id); }} aria-label="Dismiss insight" className="shrink-0 text-muted hover:text-crimson">
                    <X className="h-4 w-4" />
                  </button>
                </div>
                <div className="mt-2 text-xs text-muted">{new Date(insight.generated_at).toLocaleString()}</div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Suggestions */}
      <section>
        <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-bone">
          <TrendingUp className="h-4 w-4 text-brass" /> Actionable Suggestions
        </h2>
        {suggestionsQ.isLoading ? (
          <div className="space-y-2">{Array.from({ length: 3 }).map((_, i) => <div key={i} className="frame h-16 animate-pulse bg-white/[0.02]" />)}</div>
        ) : suggestionsQ.isError ? (
          <div className="frame border-crimson/30 bg-crimson/5 p-4 text-sm text-crimson">Could not load suggestions — /suggestions may not be deployed yet.</div>
        ) : (suggestionsQ.data ?? []).length === 0 ? (
          <div className="frame border-dashed p-6 text-center text-sm text-muted">No suggestions generated yet.</div>
        ) : (
          <div className="space-y-2">
            {(suggestionsQ.data ?? []).map((s) => (
              <div key={s.id} className="frame p-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <PriorityChip priority={s.priority} />
                      <span className="v-chip capitalize">{s.type.replace("_", " ")}</span>
                    </div>
                    <div className="mt-2 font-semibold text-bone">{s.title}</div>
                    <div className="mt-1 text-sm text-muted">{s.rationale}</div>
                    {s.estimated_saving_usd != null && (
                      <div className="mt-1 text-xs text-moss">Estimated saving: ${s.estimated_saving_usd.toFixed(2)}</div>
                    )}
                  </div>
                  <div className="flex shrink-0 flex-col items-end gap-2">
                    {s.accepted === null ? (
                      <div className="flex gap-2">
                        <button type="button" onClick={() => respond.mutate({ id: s.id, accepted: true })} className="flex items-center gap-1 rounded-lg border border-moss/40 px-3 py-1.5 text-xs text-moss hover:bg-moss/10">
                          <CheckCircle className="h-3 w-3" /> Accept
                        </button>
                        <button type="button" onClick={() => respond.mutate({ id: s.id, accepted: false })} className="flex items-center gap-1 rounded-lg border border-rule px-3 py-1.5 text-xs text-muted hover:bg-white/[0.04]">
                          <X className="h-3 w-3" /> Dismiss
                        </button>
                      </div>
                    ) : (
                      <span className={cn("v-chip", s.accepted ? "v-chip-ok" : "v-chip-warn")}>{s.accepted ? "accepted" : "dismissed"}</span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function ImpactChip({ impact }: { impact: string }) {
  return <span className={cn("v-chip", impact === "critical" && "v-chip-err", impact === "high" && "v-chip-err", impact === "medium" && "v-chip-warn", impact === "low" && "v-chip-ok")}>{impact}</span>;
}
function PriorityChip({ priority }: { priority: string }) {
  return <span className={cn("v-chip", priority === "high" && "v-chip-err", priority === "medium" && "v-chip-warn", priority === "low" && "v-chip-ok")}>{priority}</span>;
}
