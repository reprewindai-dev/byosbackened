import { useQuery } from "@tanstack/react-query";
import { Activity, CircuitBoard, GitBranch, Sparkles, Workflow } from "lucide-react";
import { api } from "@/lib/api";
import { relativeTime } from "@/lib/cn";

interface AuditLog {
  id: string;
  operation_type: string;
  provider: string;
  model: string;
  cost: string;
  pii_detected: boolean;
  created_at: string;
  input_preview: string;
}

async function fetchRecent(): Promise<AuditLog[]> {
  const resp = await api.get<{ logs: AuditLog[] }>("/audit/logs", { params: { limit: 10, offset: 0 } });
  return resp.data.logs ?? [];
}

export function PipelinesPage() {
  const recent = useQuery({ queryKey: ["pipelines-recent"], queryFn: fetchRecent, refetchInterval: 30_000 });

  return (
    <div className="mx-auto w-full max-w-7xl space-y-6">
      <header>
        <div className="mb-1 font-mono text-[11px] uppercase tracking-[0.15em] text-muted">
          Workspace · Pipelines
        </div>
        <h1 className="text-3xl font-semibold tracking-tight">Governed execution pipelines</h1>
        <p className="mt-2 max-w-2xl text-sm text-bone-2">
          Multi-step, tool-calling workflows with policy enforcement at every gate. Each step writes to the audit
          ledger. Authoring UI lands next; inspection of recent pipeline runs is live now.
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          <span className="v-chip v-chip-ok">
            <span className="h-1.5 w-1.5 animate-pulse-soft rounded-full bg-moss" />
            recent runs live · <span className="font-mono">/api/v1/audit/logs</span>
          </span>
          <span className="v-chip v-chip-warn">authoring UI · shipping next</span>
        </div>
      </header>

      <section className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <PillarCard
          icon={<CircuitBoard className="h-5 w-5" />}
          title="Policy before execution"
          body="Every pipeline step is evaluated by the policy engine. Zero-trust, rate-limit, token-budget, and compliance gates run before the first token is generated."
        />
        <PillarCard
          icon={<Workflow className="h-5 w-5" />}
          title="Tool calling, sandboxed"
          body="Tools run in an ephemeral, tenant-scoped sandbox with explicit I/O contracts. No silent data exfiltration, no surprise API calls."
        />
        <PillarCard
          icon={<GitBranch className="h-5 w-5" />}
          title="Versioned &amp; replayable"
          body="Pipelines are versioned artifacts. Any run can be replayed against its original prompt, model, and policy for regression or audit."
        />
      </section>

      <section className="v-card p-0">
        <header className="flex items-center justify-between border-b border-rule px-5 py-3">
          <div>
            <div className="font-mono text-[11px] uppercase tracking-[0.12em] text-muted">
              Recent executions
            </div>
            <h3 className="mt-0.5 text-sm font-semibold">
              Every call, every tool, every decision — on the ledger
            </h3>
          </div>
          <a href="/monitoring" className="v-btn-ghost">
            <Activity className="h-4 w-4" /> Full audit trail →
          </a>
        </header>

        <ul className="divide-y divide-rule/50">
          {recent.isLoading && (
            <li className="px-5 py-8 text-center font-mono text-[12px] text-muted">loading…</li>
          )}
          {!recent.isLoading && (recent.data ?? []).length === 0 && (
            <li className="px-5 py-8 text-center font-mono text-[12px] text-muted">
              No executions yet. Run something from{" "}
              <a href="/playground" className="text-brass-2 hover:underline">
                Playground
              </a>{" "}
              to populate this feed.
            </li>
          )}
          {recent.data?.map((l) => (
            <li key={l.id} className="flex items-start gap-3 px-5 py-3 font-mono text-[12px]">
              <div className="mt-0.5 flex h-7 w-7 items-center justify-center rounded-md bg-brass/10 text-brass-2">
                <Sparkles className="h-3.5 w-3.5" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="v-chip font-mono">{l.operation_type}</span>
                  <span className="text-brass-2">{l.provider || "—"}</span>
                  <span className="text-muted">·</span>
                  <span className="text-bone-2">{l.model || "—"}</span>
                  {l.pii_detected && <span className="v-chip v-chip-warn">PII redacted</span>}
                </div>
                <div className="mt-1 truncate text-bone-2">{l.input_preview || "—"}</div>
              </div>
              <div className="shrink-0 text-right text-muted">
                <div>{relativeTime(l.created_at)}</div>
                <div className="mt-0.5 text-bone">${parseFloat(l.cost || "0").toFixed(4)}</div>
              </div>
            </li>
          ))}
        </ul>
      </section>

      <section className="v-card border-brass/30 bg-brass/[0.03] p-5">
        <div className="mb-3 flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.12em] text-brass-2">
          <Workflow className="h-3 w-3" /> Authoring UI roadmap
        </div>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <Milestone stage="Next" title="Visual DAG editor">
            Drag nodes (prompt, tool, condition, model), connect edges, set policy gates per node.
          </Milestone>
          <Milestone stage="After" title="Version control">
            Commit pipelines, diff versions, roll back. One-click replay against historical inputs.
          </Milestone>
          <Milestone stage="Then" title="Marketplace export">
            Ship pipelines as Marketplace listings with buyer license &amp; royalty metadata.
          </Milestone>
        </div>
        <div className="mt-4 font-mono text-[11px] text-muted">
          Endpoints consumed when this ships: <span className="text-bone">/api/v1/pipelines</span>{" "}
          (CRUD), <span className="text-bone">/api/v1/pipelines/{"{id}"}/execute</span>,{" "}
          <span className="text-bone">/api/v1/pipelines/{"{id}"}/versions</span>. Not yet implemented
          on backend — will be added in a paired PR.
        </div>
      </section>
    </div>
  );
}

function PillarCard({
  icon,
  title,
  body,
}: {
  icon: React.ReactNode;
  title: string;
  body: string;
}) {
  return (
    <div className="v-card p-5">
      <div className="mb-3 flex h-9 w-9 items-center justify-center rounded-md bg-brass/10 text-brass-2">
        {icon}
      </div>
      <h3 className="text-sm font-semibold text-bone">{title}</h3>
      <p className="mt-1.5 text-[13px] leading-relaxed text-bone-2">{body}</p>
    </div>
  );
}

function Milestone({
  stage,
  title,
  children,
}: {
  stage: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-lg border border-rule p-4">
      <div className="mb-1 font-mono text-[10px] uppercase tracking-wider text-brass-2">{stage}</div>
      <div className="text-[14px] font-semibold text-bone">{title}</div>
      <div className="mt-1.5 text-[12px] leading-relaxed text-bone-2">{children}</div>
    </div>
  );
}
