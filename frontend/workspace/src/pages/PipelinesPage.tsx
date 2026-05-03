import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  CircuitBoard,
  GitBranch,
  Play,
  Plus,
  Sparkles,
  Workflow,
  X,
} from "lucide-react";
import { api } from "@/lib/api";
import { cn, relativeTime } from "@/lib/cn";
import { actionUnavailableMessage, isRouteUnavailable } from "@/lib/errors";

interface PipelineSummary {
  id: string;
  slug: string;
  name: string;
  description?: string | null;
  status: "draft" | "active" | "archived";
  current_version: number;
  created_at: string;
  updated_at: string;
  latest_version?: {
    version: number;
    created_at: string;
    node_count: number;
    policy_refs: string[];
  } | null;
}

interface PipelineRun {
  id: string;
  pipeline_id: string;
  version: number;
  status: "pending" | "running" | "succeeded" | "failed" | "blocked_policy";
  total_cost_usd: number | null;
  total_latency_ms: number | null;
  step_trace: Array<{ node_id: string; type: string; status: string; latency_ms: number; cost_usd: number }>;
  outputs: Record<string, unknown> | null;
  error_message?: string | null;
  finished_at?: string | null;
  created_at: string;
}

async function fetchPipelines(): Promise<PipelineSummary[]> {
  const r = await api.get<{ items: PipelineSummary[] }>("/pipelines", { params: { limit: 50 } });
  return r.data.items ?? [];
}

async function fetchRecentRuns(): Promise<PipelineRun[]> {
  const r = await api.get<{ items: PipelineRun[] }>("/pipelines/runs/recent", { params: { limit: 20 } });
  return r.data.items ?? [];
}

const STARTER_GRAPH = {
  nodes: [
    { id: "input", type: "prompt", label: "User input", prompt: "{{input}}" },
    { id: "policy", type: "gate", label: "Policy gate", policy: "default" },
    { id: "llm", type: "model", label: "LLM step", model: "qwen2.5:3b" },
  ],
  edges: [
    { from: "input", to: "policy" },
    { from: "policy", to: "llm" },
  ],
};

export function PipelinesPage() {
  const qc = useQueryClient();
  const [showNew, setShowNew] = useState(false);
  const [newName, setNewName] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [creating, setCreating] = useState<string | null>(null);

  const pipelines = useQuery({ queryKey: ["pipelines"], queryFn: fetchPipelines, refetchInterval: 30_000 });
  const runs = useQuery({ queryKey: ["pipelines-runs"], queryFn: fetchRecentRuns, refetchInterval: 15_000 });
  const pipelineRoutesUnavailable = isRouteUnavailable(pipelines.error) || isRouteUnavailable(runs.error);

  const createMut = useMutation({
    mutationFn: async (payload: { name: string; description?: string }) => {
      const r = await api.post<PipelineSummary>("/pipelines", {
        name: payload.name,
        description: payload.description,
        graph: STARTER_GRAPH,
      });
      return r.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["pipelines"] });
      setShowNew(false);
      setNewName("");
      setNewDesc("");
    },
  });

  const executeMut = useMutation({
    mutationFn: async (id: string) => {
      setCreating(id);
      const r = await api.post<PipelineRun>(`/pipelines/${id}/execute`, { inputs: {} });
      return r.data;
    },
    onSettled: () => {
      setCreating(null);
      qc.invalidateQueries({ queryKey: ["pipelines-runs"] });
    },
  });

  return (
    <div className="mx-auto w-full max-w-7xl space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="mb-1 font-mono text-[11px] uppercase tracking-[0.15em] text-muted">
            Workspace · Pipelines
          </div>
          <h1 className="text-3xl font-semibold tracking-tight">Governed execution pipelines</h1>
          <p className="mt-2 max-w-2xl text-sm text-bone-2">
            Multi-step, tool-calling workflows with policy enforcement at every gate. Each step writes
            to the audit ledger. Versioned, replayable, and exportable to the Marketplace.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <span className="v-chip v-chip-ok">
              <span className="h-1.5 w-1.5 animate-pulse-soft rounded-full bg-moss" />
              live · <span className="font-mono">/api/v1/pipelines</span>
            </span>
            <span className="v-chip v-chip-brass">
              {pipelines.data?.length ?? 0} pipelines
            </span>
          </div>
        </div>
        <button className="v-btn-primary" disabled={pipelineRoutesUnavailable} onClick={() => setShowNew(true)}>
          <Plus className="h-4 w-4" /> New pipeline
        </button>
      </header>

      {pipelineRoutesUnavailable && (
        <div className="v-card border-brass/40 bg-brass/5 p-4 text-sm text-brass-2">
          Pipeline creation is disabled because the live backend is not serving the pipeline write routes yet.
          Existing pipeline data will appear here automatically once the backend route is available.
        </div>
      )}

      <section className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <PillarCard icon={<CircuitBoard className="h-5 w-5" />} title="Policy before execution"
          body="Every pipeline step is evaluated by the policy engine. Zero-trust, rate-limit, token-budget, and compliance gates run before the first token is generated." />
        <PillarCard icon={<Workflow className="h-5 w-5" />} title="Tool calling, sandboxed"
          body="Tools run in an ephemeral, tenant-scoped sandbox with explicit I/O contracts. No silent data exfiltration, no surprise API calls." />
        <PillarCard icon={<GitBranch className="h-5 w-5" />} title="Versioned & replayable"
          body="Pipelines are versioned artifacts. Any run can be replayed against its original prompt, model, and policy for regression or audit." />
      </section>

      {/* Pipelines list */}
      <section className="v-card p-0">
        <header className="flex items-center justify-between border-b border-rule px-5 py-3">
          <div>
            <div className="font-mono text-[11px] uppercase tracking-[0.12em] text-muted">Pipelines</div>
            <h3 className="mt-0.5 text-sm font-semibold">Your governed workflows</h3>
          </div>
        </header>
        {pipelines.isLoading && (
          <div className="px-5 py-8 text-center font-mono text-[12px] text-muted">loading…</div>
        )}
        {!pipelines.isLoading && (pipelines.data ?? []).length === 0 && (
          <div className="flex flex-col items-center gap-3 px-5 py-12 text-center">
            <Workflow className="h-8 w-8 text-brass-2" />
            <div className="text-sm text-bone-2">No pipelines yet. Create one to get started.</div>
            <button className="v-btn-primary" disabled={pipelineRoutesUnavailable} onClick={() => setShowNew(true)}>
              <Plus className="h-4 w-4" /> New pipeline
            </button>
          </div>
        )}
        <ul className="divide-y divide-rule/50">
          {pipelines.data?.map((p) => (
            <li key={p.id} className="flex items-center gap-4 px-5 py-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-md bg-brass/10 text-brass-2">
                <Sparkles className="h-4 w-4" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-[14px] font-semibold text-bone">{p.name}</span>
                  <span className={cn(
                    "v-chip font-mono text-[10px]",
                    p.status === "active" ? "v-chip-ok" : p.status === "draft" ? "v-chip-warn" : "",
                  )}>{p.status}</span>
                  <span className="font-mono text-[10px] text-muted">v{p.current_version}</span>
                  {p.latest_version && (
                    <span className="font-mono text-[10px] text-muted">
                      · {p.latest_version.node_count} nodes
                    </span>
                  )}
                </div>
                <div className="font-mono text-[11px] text-muted">
                  {p.slug} · updated {relativeTime(p.updated_at)}
                </div>
              </div>
              <button
                className="v-btn-ghost"
                disabled={creating === p.id || executeMut.isPending}
                onClick={() => executeMut.mutate(p.id)}
              >
                <Play className="h-3.5 w-3.5" />
                {creating === p.id ? "Running…" : "Execute"}
              </button>
            </li>
          ))}
        </ul>
      </section>

      {/* Recent runs */}
      <section className="v-card p-0">
        <header className="flex items-center justify-between border-b border-rule px-5 py-3">
          <div>
            <div className="font-mono text-[11px] uppercase tracking-[0.12em] text-muted">Recent runs</div>
            <h3 className="mt-0.5 text-sm font-semibold">Cross-pipeline execution feed</h3>
          </div>
          <a href="#/monitoring" className="v-btn-ghost"><Activity className="h-4 w-4" /> Full audit trail →</a>
        </header>
        <ul className="divide-y divide-rule/50">
          {runs.isLoading && (
            <li className="px-5 py-8 text-center font-mono text-[12px] text-muted">loading…</li>
          )}
          {!runs.isLoading && (runs.data ?? []).length === 0 && (
            <li className="px-5 py-8 text-center font-mono text-[12px] text-muted">
              No runs yet. Execute a pipeline above to populate this feed.
            </li>
          )}
          {runs.data?.map((r) => (
            <li key={r.id} className="flex items-start gap-3 px-5 py-3 font-mono text-[12px]">
              <div className={cn(
                "mt-0.5 flex h-7 w-7 items-center justify-center rounded-md",
                r.status === "succeeded" ? "bg-moss/10 text-moss"
                  : r.status === "failed" ? "bg-crimson/10 text-crimson"
                  : r.status === "blocked_policy" ? "bg-brass/10 text-brass-2"
                  : "bg-electric/10 text-electric"
              )}>
                <Sparkles className="h-3.5 w-3.5" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className={cn(
                    "v-chip font-mono",
                    r.status === "succeeded" ? "v-chip-ok"
                      : r.status === "failed" ? "v-chip-warn"
                      : r.status === "blocked_policy" ? "v-chip-brass"
                      : "",
                  )}>{r.status}</span>
                  <span className="text-bone-2">v{r.version}</span>
                  <span className="text-muted">·</span>
                  <span className="text-bone-2">{r.step_trace?.length ?? 0} steps</span>
                  {r.total_latency_ms != null && (
                    <span className="text-muted">{r.total_latency_ms}ms</span>
                  )}
                </div>
                {r.error_message && (
                  <div className="mt-1 truncate text-crimson">{r.error_message}</div>
                )}
              </div>
              <div className="shrink-0 text-right text-muted">
                <div>{relativeTime(r.created_at)}</div>
                {r.total_cost_usd != null && (
                  <div className="mt-0.5 text-bone">${(r.total_cost_usd ?? 0).toFixed(4)}</div>
                )}
              </div>
            </li>
          ))}
        </ul>
      </section>

      {/* Create modal */}
      {showNew && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/80 backdrop-blur-sm">
          <div className="v-card w-full max-w-md p-5">
            <header className="mb-4 flex items-center justify-between">
              <h3 className="text-lg font-semibold">New pipeline</h3>
              <button className="text-muted hover:text-bone" onClick={() => setShowNew(false)}>
                <X className="h-4 w-4" />
              </button>
            </header>
            <div className="space-y-3">
              <label className="block">
                <div className="mb-1 font-mono text-[10px] uppercase tracking-wider text-muted">Name</div>
                <input
                  className="v-input w-full"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="claims-triage"
                  autoFocus
                />
              </label>
              <label className="block">
                <div className="mb-1 font-mono text-[10px] uppercase tracking-wider text-muted">Description</div>
                <textarea
                  className="v-input w-full"
                  rows={2}
                  value={newDesc}
                  onChange={(e) => setNewDesc(e.target.value)}
                  placeholder="Optional summary"
                />
              </label>
              <div className="font-mono text-[10px] text-muted">
                Starter graph: input → policy gate → LLM. You can add nodes via{" "}
                <span className="text-bone">POST /pipelines/{`{id}`}/versions</span>.
              </div>
              {createMut.isError && (
                <div className="text-[12px] text-crimson">
                  {actionUnavailableMessage(createMut.error, "Pipeline creation")}
                </div>
              )}
              <div className="flex justify-end gap-2">
                <button className="v-btn-ghost" onClick={() => setShowNew(false)}>Cancel</button>
                <button
                  className="v-btn-primary"
                  disabled={!newName || createMut.isPending}
                  onClick={() => createMut.mutate({ name: newName, description: newDesc || undefined })}
                >
                  {createMut.isPending ? "Creating…" : "Create"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function PillarCard({ icon, title, body }: { icon: React.ReactNode; title: string; body: string }) {
  return (
    <div className="v-card p-5">
      <div className="mb-3 flex h-9 w-9 items-center justify-center rounded-md bg-brass/10 text-brass-2">{icon}</div>
      <h3 className="text-sm font-semibold text-bone">{title}</h3>
      <p className="mt-1.5 text-[13px] leading-relaxed text-bone-2">{body}</p>
    </div>
  );
}
