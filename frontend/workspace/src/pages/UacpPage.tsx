import { useQueries, useQuery } from "@tanstack/react-query";
import { AlertCircle, ArrowUpRight, BrainCircuit, CheckCircle2, LockKeyhole, ShieldCheck, Wallet } from "lucide-react";
import { Link } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuthStore } from "@/store/auth-store";
import { internalService } from "@/lib/services/internal.service";

interface CurrentSubscription {
  plan: string;
  status: string;
}

interface InternalUacpSummary {
  source?: string;
  contract_version?: string;
  product_truth?: { workspace_count?: number };
  uacp_truth?: { healthy_workers?: number };
}

interface InternalOperatorsOverview {
  worker_count?: number;
  ready_workers?: number;
  minimum_live_ready?: number;
}

const UACP_EVENT_PRICES = [
  ["GPC plan compile", "$1.50 Founding / $2.00 Standard / $2.50 Regulated"],
  ["Governed execution", "$3 Founding / $4 Standard / $5 Regulated"],
  ["Evidence artifact generation", "$5 Founding / $7 Standard / $10 Regulated"],
] as const;

const UACP_ROUTE_SPINE = [
  { label: "v0 summary", path: "/uacp/v0", target: "/internal/uacp/summary" },
  { label: "v1 events", path: "/uacp/v1", target: "/internal/uacp/events" },
  { label: "v2 stream", path: "/uacp/v2", target: "/internal/uacp/event-stream" },
  { label: "v3 monitoring", path: "/uacp/v3", target: "/internal/uacp/monitoring" },
  { label: "v4 security", path: "/uacp/v4", target: "/internal/uacp/security" },
] as const;

async function fetchCurrentSubscription(): Promise<CurrentSubscription> {
  return (await api.get<CurrentSubscription>("/subscriptions/current")).data;
}

function routeErrorLabel(error: unknown): string {
  const status = (error as { response?: { status?: number } })?.response?.status;
  if (status === 404) return "No route found";
  if (status === 401 || status === 403) return "protected";
  return "unavailable";
}

function payloadSignal(data: unknown): string {
  if (!data || typeof data !== "object") return "response";
  const keys = Object.keys(data as Record<string, unknown>).slice(0, 3);
  return keys.length ? keys.join(" / ") : "response";
}

export function UacpPage() {
  const user = useAuthStore((state) => state.user);
  const subscription = useQuery({
    queryKey: ["subscription-current"],
    queryFn: fetchCurrentSubscription,
    staleTime: 60_000,
  });

  const isSuperuser = Boolean(user?.is_superuser);
  const isPaidWorkspace =
    subscription.data?.status === "active" && Boolean(subscription.data?.plan) && subscription.data.plan !== "free";
  const canOpenRuntime = isSuperuser || isPaidWorkspace;
  const operatorOverview = useQuery({
    queryKey: ["internal-operators-overview"],
    queryFn: async () => (await internalService.operatorOverview()).data as InternalOperatorsOverview,
    enabled: isSuperuser,
    retry: false,
  });
  const uacpSummary = useQuery({
    queryKey: ["internal-uacp-summary"],
    queryFn: async () => (await internalService.getUacpSummary()).data as InternalUacpSummary,
    enabled: isSuperuser,
    retry: false,
  });
  const uacpSpine = useQueries({
    queries: UACP_ROUTE_SPINE.map((route) => ({
      queryKey: ["gpc-uacp-spine", route.path],
      queryFn: async () => (await api.get(route.path)).data,
      enabled: canOpenRuntime,
      retry: false,
      staleTime: 30_000,
    })),
  });

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-5">
      <header className="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
        <div>
          <div className="text-eyebrow">Workspace / GPC</div>
          <h1 className="font-display mt-2 text-[34px] font-semibold tracking-tight text-bone">
            GPC governed plan compiler
          </h1>
          <p className="mt-3 max-w-3xl text-sm leading-6 text-bone-2">
            GPC is the buyer-facing compiler surface for the UACPGemini v2 control-plane spine. The workspace shell
            handles tenant scope, activation state, and reserve posture; backend UACP routes remain the authoritative
            execution interface.
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <span className="v-chip v-chip-brass">
              <Wallet className="h-3 w-3" />
              no free GPC runs
            </span>
            <span className="v-chip v-chip-ok">
              <ShieldCheck className="h-3 w-3" />
              UACPGemini v2 spine
            </span>
            <span className="v-chip">
              <LockKeyhole className="h-3 w-3" />
              tenant scoped wrapper
            </span>
          </div>
        </div>

        <aside className="frame p-4">
          <div className="text-eyebrow">Billable GPC events</div>
          <div className="mt-3 space-y-3 text-sm">
            {UACP_EVENT_PRICES.map(([label, price]) => (
              <div
                key={label}
                className="flex items-start justify-between gap-3 border-b border-rule/70 pb-2 last:border-0 last:pb-0"
              >
                <span className="text-bone-2">{label}</span>
                <span className="max-w-[220px] text-right font-mono text-[11px] text-brass-2">{price}</span>
              </div>
            ))}
          </div>
        </aside>
        {isSuperuser && (
          <aside className="frame p-4">
            <div className="text-eyebrow">Internal spine status</div>
            <div className="mt-3 space-y-2 text-xs">
              <div className="flex justify-between gap-3">
                <span className="text-bone-2">Operators</span>
                <span className="font-mono">
                  {operatorOverview.data?.ready_workers ?? 0} / {operatorOverview.data?.worker_count ?? 0} ready
                </span>
              </div>
              <div className="flex justify-between gap-3">
                <span className="text-bone-2">Minimum live</span>
                <span className="font-mono">{operatorOverview.data?.minimum_live_ready ?? 0}</span>
              </div>
              <div className="flex justify-between gap-3">
                <span className="text-bone-2">UACP source</span>
                <span className="font-mono">{uacpSummary.data?.source ?? "veklom_internal"}</span>
              </div>
              <div className="flex justify-between gap-3">
                <span className="text-bone-2">Healthy workers</span>
                <span className="font-mono">{uacpSummary.data?.uacp_truth?.healthy_workers ?? 0}</span>
              </div>
              <div className="flex justify-between gap-3">
                <span className="text-bone-2">Contract</span>
                <span className="font-mono">{uacpSummary.data?.contract_version ?? "v1"}</span>
              </div>
              {(operatorOverview.isError || uacpSummary.isError) && (
                <div className="rounded-md border border-crimson/35 bg-crimson/8 px-2 py-2 text-[10px] text-crimson">
                  Internal route unavailable. You are probably not authorized or endpoint is not live.
                </div>
              )}
            </div>
          </aside>
        )}
      </header>

      {!canOpenRuntime && (
        <section className="rounded-xl border border-brass/35 bg-brass/[0.055] p-4 text-sm leading-6 text-brass-2">
          GPC is not included in Free Evaluation. Activate the workspace and fund operating reserve before compiling
          plans, executing governed runs, or generating artifacts.
          <div className="mt-4 flex flex-wrap gap-2">
            <Link className="v-btn-primary h-9 px-3 text-xs" to="/billing">
              Activate workspace <ArrowUpRight className="h-3.5 w-3.5" />
            </Link>
            <Link className="v-btn-ghost h-9 px-3 text-xs" to="/overview">
              Back to overview
            </Link>
          </div>
        </section>
      )}

      <section className="frame overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-rule/80 bg-ink-1/60 px-4 py-3">
          <div>
            <div className="text-eyebrow">Backend route spine</div>
            <h2 className="font-display mt-1 text-base font-semibold text-bone">
              UACP/GPC execution interface
            </h2>
          </div>
          <span className="v-chip v-chip-ok">
            <BrainCircuit className="h-3 w-3" />
            5 live API layers
          </span>
        </div>

        <div className="relative bg-black/40 p-4">
          {!canOpenRuntime && (
            <div className="absolute inset-0 z-10 grid place-items-center bg-black/70 p-6 backdrop-blur-sm">
              <div className="max-w-lg rounded-xl border border-brass/30 bg-ink/95 p-5 text-center shadow-2xl">
                <div className="text-eyebrow text-brass-2">Activation required</div>
                <p className="mt-3 text-sm leading-6 text-bone-2">
                  The GPC/UACP runtime is loaded behind the paid gate. Free Evaluation can browse the hub, but GPC
                  compile/run/artifact events require an activated reserve-backed workspace.
                </p>
              </div>
            </div>
          )}
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
            {UACP_ROUTE_SPINE.map((route, index) => {
              const probe = uacpSpine[index];
              const ok = Boolean(probe?.isSuccess);
              const error = Boolean(probe?.isError);
              return (
                <div key={route.path} className="rounded-lg border border-rule bg-ink-1/80 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="text-eyebrow">{route.label}</div>
                      <div className="mt-2 font-mono text-xs text-bone">{route.path}</div>
                    </div>
                    {ok ? (
                      <CheckCircle2 className="h-4 w-4 text-mint" />
                    ) : (
                      <AlertCircle className="h-4 w-4 text-brass-2" />
                    )}
                  </div>
                  <div className="mt-4 rounded-md border border-rule/80 bg-black/30 px-3 py-2">
                    <div className="text-[10px] uppercase tracking-[0.16em] text-bone-3">Target</div>
                    <div className="mt-1 break-all font-mono text-[11px] text-bone-2">{route.target}</div>
                  </div>
                  <div className="mt-3 text-xs text-bone-2">
                    {!canOpenRuntime && "locked by subscription"}
                    {canOpenRuntime && probe?.isLoading && "checking route"}
                    {ok && `route live: ${payloadSignal(probe.data)}`}
                    {error && routeErrorLabel(probe.error)}
                  </div>
                </div>
              );
            })}
          </div>

          <div className="mt-4 rounded-lg border border-brass/25 bg-brass/[0.055] p-4">
            <div className="text-eyebrow text-brass-2">Embedded artifact</div>
            <div className="mt-2 text-sm text-bone">
              No route found: /uacp/ static runtime artifact
            </div>
            <p className="mt-2 text-xs leading-5 text-bone-2">
              The workspace no longer embeds a separate clean-path UACP site. Clean /uacp and /gpc redirect to
              /login/#/gpc, and this page calls the backend UACP/GPC API spine directly.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
