import { useQuery } from "@tanstack/react-query";
import { ArrowUpRight, ExternalLink, LockKeyhole, ShieldCheck, Wallet } from "lucide-react";
import { Link } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuthStore } from "@/store/auth-store";

interface CurrentSubscription {
  plan: string;
  status: string;
}

const UACP_EVENT_PRICES = [
  ["GPC plan compile", "$1.50 Founding / $2.00 Standard / $2.50 Regulated"],
  ["Governed execution", "$3 Founding / $4 Standard / $5 Regulated"],
  ["Evidence artifact generation", "$5 Founding / $7 Standard / $10 Regulated"],
] as const;

async function fetchCurrentSubscription(): Promise<CurrentSubscription> {
  return (await api.get<CurrentSubscription>("/subscriptions/current")).data;
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
    subscription.data?.status === "active" && subscription.data?.plan && subscription.data.plan !== "free";
  const canOpenRuntime = isSuperuser || isPaidWorkspace;

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-5">
      <header className="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
        <div>
          <div className="text-eyebrow">Workspace / GPC</div>
          <h1 className="font-display mt-2 text-[34px] font-semibold tracking-tight text-bone">
            GPC governed plan compiler
          </h1>
          <p className="mt-3 max-w-3xl text-sm leading-6 text-bone-2">
            GPC is the buyer-facing compiler surface for the original UACPGemini control-plane runtime. The workspace
            shell handles tenant scope, activation state, and reserve posture; the embedded UACP/Gemini runtime remains
            the authoritative execution interface.
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <span className="v-chip v-chip-brass">
              <Wallet className="h-3 w-3" />
              no free GPC runs
            </span>
            <span className="v-chip v-chip-ok">
              <ShieldCheck className="h-3 w-3" />
              original UACPGemini runtime
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
            <div className="text-eyebrow">Wrapped runtime</div>
            <h2 className="font-display mt-1 text-base font-semibold text-bone">
              Original UACPGemini execution theater
            </h2>
          </div>
          <a className="v-btn-ghost h-8 px-3 text-xs" href="/uacp/" target="_blank" rel="noreferrer">
            Open runtime <ExternalLink className="h-3.5 w-3.5" />
          </a>
        </div>

        <div className="relative bg-black">
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
          <iframe
            title="Original UACPGemini wrapped runtime"
            src="/uacp/?surface=workspace"
            className="h-[min(820px,calc(100vh-15rem))] min-h-[620px] w-full border-0"
            allow="clipboard-write"
          />
        </div>
      </section>
    </div>
  );
}
