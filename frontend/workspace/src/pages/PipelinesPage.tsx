import { useMemo, useState, type ReactNode } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  AlertCircle,
  Box,
  BrainCircuit,
  Code2,
  Database,
  FileJson,
  GitBranch,
  Globe2,
  Layers3,
  LockKeyhole,
  Play,
  Plus,
  Route,
  Search,
  ShieldCheck,
  Sparkles,
  Split,
  TerminalSquare,
  Webhook,
  Workflow,
  X,
} from "lucide-react";
import { api } from "@/lib/api";
import { cn, relativeTime } from "@/lib/cn";
import { actionUnavailableMessage, isRouteUnavailable } from "@/lib/errors";

interface PipelineNode {
  id: string;
  type: "prompt" | "tool" | "condition" | "model" | "gate" | string;
  label?: string;
  model?: string;
  prompt?: string;
  tool?: string;
  policy?: string;
  config?: Record<string, unknown>;
}

interface PipelineEdge {
  from?: string;
  from_?: string;
  to: string;
}

interface PipelineGraph {
  nodes: PipelineNode[];
  edges: PipelineEdge[];
}

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

interface PipelineDetail extends PipelineSummary {
  graph?: PipelineGraph;
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

interface CreatePipelinePayload {
  name: string;
  description?: string;
  graph: PipelineGraph;
  policy_refs?: string[];
}

interface PipelineTemplate {
  key: string;
  name: string;
  description: string;
  policyRefs: string[];
  graph: PipelineGraph;
}

async function fetchPipelines(): Promise<PipelineSummary[]> {
  const r = await api.get<{ items: PipelineSummary[] }>("/pipelines", { params: { limit: 50 } });
  return r.data.items ?? [];
}

async function fetchPipelineDetail(id: string): Promise<PipelineDetail> {
  const r = await api.get<PipelineDetail>(`/pipelines/${encodeURIComponent(id)}`);
  return r.data;
}

async function fetchRecentRuns(): Promise<PipelineRun[]> {
  const r = await api.get<{ items: PipelineRun[] }>("/pipelines/runs/recent", { params: { limit: 20 } });
  return r.data.items ?? [];
}

const STARTER_GRAPH: PipelineGraph = {
  nodes: [
    { id: "input", type: "prompt", label: "Input", prompt: "{{input}}" },
    { id: "policy", type: "gate", label: "Policy gate", policy: "default" },
    { id: "llm", type: "model", label: "LLM step", model: "qwen2.5:3b" },
  ],
  edges: [
    { from: "input", to: "policy" },
    { from: "policy", to: "llm" },
  ],
};

const PIPELINE_TEMPLATES: PipelineTemplate[] = [
  {
    key: "phi-safe-summarization",
    name: "PHI-safe summarization",
    description: "Redact sensitive health data, enforce Hetzner-only routing, summarize, and sign the run.",
    policyRefs: ["hipaa-aware", "on-prem-only", "audit-export"],
    graph: {
      nodes: [
        { id: "input", type: "prompt", label: "Clinical document", prompt: "{{input}}" },
        { id: "redact", type: "tool", label: "PHI/PII redaction", tool: "pii-redactor" },
        { id: "policy", type: "gate", label: "HIPAA policy gate", policy: "hipaa-aware.onprem" },
        { id: "summary", type: "model", label: "Summarize", model: "qwen2.5:3b" },
        { id: "audit", type: "tool", label: "Signed manifest", tool: "audit-signer" },
      ],
      edges: [
        { from: "input", to: "redact" },
        { from: "redact", to: "policy" },
        { from: "policy", to: "summary" },
        { from: "summary", to: "audit" },
      ],
    },
  },
  {
    key: "multi-step-function-call",
    name: "Multi-step function call",
    description: "Validate input, choose a governed model, call an approved tool, and write a trace.",
    policyRefs: ["tool-allowlist", "cost-cap", "audit-required"],
    graph: {
      nodes: [
        { id: "input", type: "prompt", label: "Task input", prompt: "{{input}}" },
        { id: "policy", type: "gate", label: "Tool policy gate", policy: "tools.approved" },
        { id: "planner", type: "model", label: "Plan call", model: "llama-3.1-8b-instant" },
        { id: "tool", type: "tool", label: "HTTP tool", tool: "http-approved" },
        { id: "final", type: "model", label: "Final answer", model: "llama-3.1-8b-instant" },
      ],
      edges: [
        { from: "input", to: "policy" },
        { from: "policy", to: "planner" },
        { from: "planner", to: "tool" },
        { from: "tool", to: "final" },
      ],
    },
  },
  {
    key: "policy-bound-rewrite",
    name: "Policy-bound rewrite",
    description: "Rewrite content under compliance policy, redaction controls, and signed output capture.",
    policyRefs: ["outbound.public.v3", "pii-clean", "signed-output"],
    graph: {
      nodes: [
        { id: "draft", type: "prompt", label: "Draft content", prompt: "{{input}}" },
        { id: "policy", type: "gate", label: "Outbound policy", policy: "outbound.public.v3" },
        { id: "rewrite", type: "model", label: "Rewrite", model: "qwen2.5:3b" },
        { id: "redact", type: "tool", label: "Redaction pass", tool: "pii-redactor" },
        { id: "manifest", type: "tool", label: "Manifest", tool: "audit-signer" },
      ],
      edges: [
        { from: "draft", to: "policy" },
        { from: "policy", to: "rewrite" },
        { from: "rewrite", to: "redact" },
        { from: "redact", to: "manifest" },
      ],
    },
  },
  {
    key: "code-repair-fim",
    name: "Code repair (FIM)",
    description: "Route a code repair through policy, context validation, model execution, and audit capture.",
    policyRefs: ["repo-context", "secret-scan", "audit-required"],
    graph: {
      nodes: [
        { id: "code", type: "prompt", label: "Code context", prompt: "{{input}}" },
        { id: "scan", type: "tool", label: "Secret scan", tool: "secret-scanner" },
        { id: "policy", type: "gate", label: "Repo policy", policy: "repo-context.safe" },
        { id: "repair", type: "model", label: "FIM repair", model: "llama-3.3-70b-versatile" },
        { id: "audit", type: "tool", label: "Audit trace", tool: "audit-signer" },
      ],
      edges: [
        { from: "code", to: "scan" },
        { from: "scan", to: "policy" },
        { from: "policy", to: "repair" },
        { from: "repair", to: "audit" },
      ],
    },
  },
];

export function PipelinesPage() {
  const qc = useQueryClient();
  const [showNew, setShowNew] = useState(false);
  const [showTemplates, setShowTemplates] = useState(false);
  const [newName, setNewName] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [creating, setCreating] = useState<string | null>(null);
  const [deploying, setDeploying] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [nodeSearch, setNodeSearch] = useState("");
  const [actionError, setActionError] = useState<unknown>(null);

  const pipelines = useQuery({ queryKey: ["pipelines"], queryFn: fetchPipelines, refetchInterval: 30_000 });
  const runs = useQuery({ queryKey: ["pipelines-runs"], queryFn: fetchRecentRuns, refetchInterval: 15_000 });
  const pipelineRoutesUnavailable = isRouteUnavailable(pipelines.error) || isRouteUnavailable(runs.error);
  const selectedPipeline = useMemo(() => {
    const rows = pipelines.data ?? [];
    return rows.find((row) => row.id === selectedId) ?? rows[0] ?? null;
  }, [pipelines.data, selectedId]);
  const detail = useQuery({
    queryKey: ["pipeline-detail", selectedPipeline?.id],
    queryFn: () => fetchPipelineDetail(selectedPipeline!.id),
    enabled: Boolean(selectedPipeline?.id),
    refetchInterval: 30_000,
  });

  const createMut = useMutation({
    mutationFn: async (payload: CreatePipelinePayload) => {
      const r = await api.post<PipelineSummary>("/pipelines", payload);
      return r.data;
    },
    onSuccess: (created) => {
      qc.invalidateQueries({ queryKey: ["pipelines"] });
      setSelectedId(created.id);
      setShowNew(false);
      setShowTemplates(false);
      setNewName("");
      setNewDesc("");
      setActionError(null);
    },
    onError: (error) => setActionError(error),
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
    onError: (error) => setActionError(error),
  });

  const deployMut = useMutation({
    mutationFn: async ({ pipeline, graph }: { pipeline: PipelineSummary; graph?: PipelineGraph }) => {
      setDeploying(true);
      const modelNode = graph?.nodes.find((node) => node.type === "model" && node.model);
      const modelSlug = modelNode?.model ?? "qwen2.5:3b";
      const provider = modelSlug.includes("llama-3") ? "groq" : "ollama";
      const r = await api.post("/deployments", {
        name: `${pipeline.slug}-endpoint`,
        region: "hetzner-fsn1",
        service_type: "pipeline",
        model_slug: modelSlug,
        provider,
        version: `pipeline-v${pipeline.current_version}`,
        strategy: "direct",
        traffic_percent: 100,
      });
      return r.data;
    },
    onSuccess: () => {
      setActionError(null);
      qc.invalidateQueries({ queryKey: ["deployments"] });
    },
    onError: (error) => setActionError(error),
    onSettled: () => setDeploying(false),
  });

  const graph = detail.data?.graph ?? (!selectedPipeline ? STARTER_GRAPH : undefined);
  const visibleRuns = runs.data ?? [];
  const runCountByPipeline = useMemo(() => {
    const counts = new Map<string, number>();
    for (const run of visibleRuns) counts.set(run.pipeline_id, (counts.get(run.pipeline_id) ?? 0) + 1);
    return counts;
  }, [visibleRuns]);

  return (
    <div className="mx-auto w-full max-w-[1400px]">
      <PageHeader
        pipelineCount={pipelines.data?.length ?? 0}
        routeUnavailable={pipelineRoutesUnavailable}
        onNew={() => setShowNew(true)}
        onTemplates={() => setShowTemplates(true)}
      />

      {pipelineRoutesUnavailable && (
        <div className="frame mb-4 flex items-start gap-3 border-brass/40 bg-brass/5 p-4 text-sm text-brass-2">
          <AlertCircle className="mt-0.5 h-4 w-4" />
          <div>
            Pipeline write routes are currently unavailable from the live API. Existing data remains readable, and write
            controls re-enable automatically when the backend responds.
          </div>
        </div>
      )}

      {Boolean(actionError) && (
        <div className="frame mb-4 flex items-start gap-3 border-crimson/40 bg-crimson/5 p-4 text-sm text-crimson">
          <AlertCircle className="mt-0.5 h-4 w-4" />
          <div>{actionUnavailableMessage(actionError, "Pipeline action")}</div>
        </div>
      )}

      <section>
        <div className="grid grid-cols-12 gap-4">
          <BuilderPanel
            selected={selectedPipeline}
            graph={graph}
            loading={Boolean(selectedPipeline) && detail.isLoading}
            routeUnavailable={pipelineRoutesUnavailable}
            executing={creating === selectedPipeline?.id || executeMut.isPending}
            deploying={deploying || deployMut.isPending}
            onExecute={() => selectedPipeline && executeMut.mutate(selectedPipeline.id)}
            onDeploy={() => selectedPipeline && deployMut.mutate({ pipeline: selectedPipeline, graph })}
          />
          <NodePalette search={nodeSearch} onSearch={setNodeSearch} />
        </div>

        <PipelinesTable
          pipelines={pipelines.data ?? []}
          loading={pipelines.isLoading}
          selectedId={selectedPipeline?.id ?? null}
          runCounts={runCountByPipeline}
          routeUnavailable={pipelineRoutesUnavailable}
          executingId={creating}
          executing={executeMut.isPending}
          onSelect={setSelectedId}
          onNew={() => setShowNew(true)}
          onExecute={(id) => executeMut.mutate(id)}
        />

        <RecentRunsPanel runs={visibleRuns} loading={runs.isLoading} />
      </section>

      {showNew && (
        <CreatePipelineModal
          name={newName}
          description={newDesc}
          onName={setNewName}
          onDescription={setNewDesc}
          onClose={() => setShowNew(false)}
          onCreate={() =>
            createMut.mutate({
              name: newName,
              description: newDesc || undefined,
              graph: STARTER_GRAPH,
              policy_refs: ["default"],
            })
          }
          pending={createMut.isPending}
          error={createMut.error}
        />
      )}
      {showTemplates && (
        <TemplateModal
          templates={PIPELINE_TEMPLATES}
          pending={createMut.isPending}
          error={createMut.error}
          onClose={() => setShowTemplates(false)}
          onCreate={(template) =>
            createMut.mutate({
              name: template.name,
              description: template.description,
              graph: template.graph,
              policy_refs: template.policyRefs,
            })
          }
        />
      )}
    </div>
  );
}

function PageHeader({
  pipelineCount,
  routeUnavailable,
  onNew,
  onTemplates,
}: {
  pipelineCount: number;
  routeUnavailable: boolean;
  onNew: () => void;
  onTemplates: () => void;
}) {
  return (
    <header className="mb-5 flex flex-wrap items-start justify-between gap-4">
      <div>
        <div className="text-eyebrow">Pipelines</div>
        <h1 className="font-display mt-1 text-[30px] font-semibold tracking-tight text-bone">
          Visual builder for governed inference
        </h1>
        <p className="mt-2 max-w-3xl text-sm text-bone-2">
          Drag-and-drop graphs that chain models, retrieval, memory, tools, and routing - every node gated by your
          policy engine.
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          <Badge tone="ok" dot>
            live · <span className="font-mono">/api/v1/pipelines</span>
          </Badge>
          <Badge tone="primary">{pipelineCount} pipelines</Badge>
        </div>
      </div>
      <div className="flex flex-wrap gap-2">
        <button
          className="v-btn-ghost h-8 px-3 text-xs"
          disabled={routeUnavailable}
          onClick={onTemplates}
          title="Create a real persisted pipeline from a governed template."
        >
          <GitBranch className="h-3.5 w-3.5" /> Templates
        </button>
        <button className="v-btn-primary h-8 px-3 text-xs" disabled={routeUnavailable} onClick={onNew}>
          <Plus className="h-3.5 w-3.5" /> New pipeline
        </button>
      </div>
    </header>
  );
}

function BuilderPanel({
  selected,
  graph,
  loading,
  routeUnavailable,
  executing,
  deploying,
  onExecute,
  onDeploy,
}: {
  selected: PipelineSummary | null;
  graph?: PipelineGraph;
  loading: boolean;
  routeUnavailable: boolean;
  executing: boolean;
  deploying: boolean;
  onExecute: () => void;
  onDeploy: () => void;
}) {
  const nodeCount = graph?.nodes.length ?? selected?.latest_version?.node_count ?? 0;
  const edgeCount = graph?.edges.length ?? 0;

  return (
    <div className="frame col-span-12 overflow-hidden lg:col-span-8">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-rule/80 px-4 py-2.5">
        <div className="flex min-w-0 items-center gap-2">
          <Workflow className="h-4 w-4 shrink-0 text-brass-2" />
          <span className="font-display truncate text-[14px] font-semibold text-bone">
            {selected?.name ?? "starter-governed-pipeline"}
          </span>
          <Badge tone={selected?.status === "active" ? "ok" : "muted"}>
            v{selected?.current_version ?? 1} · {selected?.status ?? "draft"}
          </Badge>
        </div>
        <div className="flex items-center gap-2">
          <button
            className="v-btn-ghost h-7 px-2 text-xs"
            disabled={!selected || routeUnavailable || executing}
            onClick={onExecute}
          >
            <Play className="h-3.5 w-3.5" /> {executing ? "Running..." : "Test"}
          </button>
          <button
            className="v-btn-primary h-7 px-2 text-xs"
            disabled={!selected || routeUnavailable || deploying}
            onClick={onDeploy}
            title="Create a live deployment record for this pipeline."
          >
            <RocketIcon /> {deploying ? "Deploying..." : "Deploy as endpoint"}
          </button>
        </div>
      </div>
      <div className="relative h-[560px] overflow-hidden bg-[radial-gradient(circle_at_1px_1px,rgba(255,255,255,0.075)_1px,transparent_0)] bg-[length:20px_20px]">
        {loading && (
          <div className="absolute inset-0 z-10 grid place-items-center bg-ink/50 font-mono text-[12px] uppercase tracking-[0.16em] text-muted">
            loading graph...
          </div>
        )}
        {graph ? (
          <PipelineCanvas graph={graph} />
        ) : (
          <div className="absolute inset-0 grid place-items-center px-8 text-center text-sm text-bone-2">
            Select a pipeline to render its persisted graph.
          </div>
        )}
      </div>
      <div className="flex items-center justify-between border-t border-rule/80 px-4 py-2 text-[11px] text-muted">
        <span>
          <Badge tone="primary">POLICY ENGINE INLINE</Badge>
        </span>
        <span className="font-mono">
          {nodeCount} nodes · {edgeCount} edges · audit-gated execution
        </span>
      </div>
    </div>
  );
}

function PipelineCanvas({ graph }: { graph: PipelineGraph }) {
  const layout = layoutNodes(graph.nodes);
  const byId = new Map(layout.map((node) => [node.id, node]));

  return (
    <svg viewBox="0 0 1100 460" className="absolute inset-0 h-full w-full">
      <defs>
        <marker id="pipeline-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
          <path d="M0,0 L10,5 L0,10 z" fill="rgba(200,203,214,0.55)" />
        </marker>
      </defs>
      {graph.edges.map((edge, index) => {
        const from = byId.get(edge.from ?? edge.from_ ?? "");
        const to = byId.get(edge.to);
        if (!from || !to) return null;
        const mid = (from.x + to.x) / 2;
        return (
          <path
            key={`${edge.from ?? edge.from_}-${edge.to}-${index}`}
            d={`M${from.x + 70},${from.y} C${mid},${from.y} ${mid},${to.y} ${to.x},${to.y}`}
            fill="none"
            stroke="rgba(200,203,214,0.42)"
            strokeWidth="1.4"
            strokeDasharray="4 3"
            markerEnd="url(#pipeline-arrow)"
          />
        );
      })}
      {layout.map((node) => (
        <foreignObject key={node.id} x={node.x} y={node.y - 18} width="150" height="58">
          <div
            className={cn(
              "flex h-full items-center gap-2 rounded-md border bg-ink-2/95 px-2.5 shadow-md",
              nodeToneClass(node.type),
            )}
          >
            <div className={cn("grid h-6 w-6 place-items-center rounded-md", nodeIconToneClass(node.type))}>
              {nodeIcon(node.type)}
            </div>
            <div className="flex min-w-0 flex-col leading-tight">
              <span className="truncate text-[11.5px] text-bone">{node.label ?? node.model ?? node.tool ?? node.id}</span>
              <span className="truncate font-mono text-[9px] text-muted">{node.id}</span>
            </div>
          </div>
        </foreignObject>
      ))}
    </svg>
  );
}

function layoutNodes(nodes: PipelineNode[]): Array<PipelineNode & { x: number; y: number }> {
  if (nodes.length === 0) return [];
  const columns = Math.min(5, Math.max(1, nodes.length));
  return nodes.map((node, index) => {
    const col = columns === 1 ? 0 : index % columns;
    const row = Math.floor(index / columns);
    const x = 60 + col * (980 / Math.max(1, columns - 1));
    const y = 130 + row * 120 + (col % 2 ? 60 : 0);
    return { ...node, x: Math.min(1020, x), y: Math.min(390, y) };
  });
}

function NodePalette({ search, onSearch }: { search: string; onSearch: (value: string) => void }) {
  const groups = paletteGroups();
  const q = search.trim().toLowerCase();

  return (
    <aside className="frame col-span-12 overflow-hidden lg:col-span-4">
      <div className="border-b border-rule/80 px-4 py-2.5">
        <label className="flex items-center gap-2 rounded-md border border-rule bg-ink-1/70 px-2.5 py-1.5">
          <Search className="h-3.5 w-3.5 text-muted" />
          <input
            className="w-full bg-transparent text-[12px] text-bone outline-none placeholder:text-muted"
            placeholder="Search nodes..."
            value={search}
            onChange={(event) => onSearch(event.target.value)}
          />
        </label>
      </div>
      <div className="max-h-[520px] overflow-y-auto px-2 py-2">
        {groups.map((group) => {
          const items = group.items.filter((item) => !q || item.name.toLowerCase().includes(q));
          if (!items.length) return null;
          return (
            <div key={group.name} className="mb-3">
              <div className="px-2 pb-1 text-eyebrow">{group.name}</div>
              <div className="grid grid-cols-2 gap-1.5">
                {items.map((item) => (
                  <button
                    key={item.name}
                    className="hover-elevate flex cursor-not-allowed items-center gap-2 rounded-md border border-rule bg-ink-1/45 px-2 py-1.5 text-[11.5px] text-bone-2"
                    disabled
                    title="The visual composer is read-only until node persistence is wired."
                  >
                    <span className="grid h-5 w-5 place-items-center rounded bg-ink-3 text-muted">{item.icon}</span>
                    <span className="line-clamp-1">{item.name}</span>
                  </button>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </aside>
  );
}

function PipelinesTable({
  pipelines,
  loading,
  selectedId,
  runCounts,
  routeUnavailable,
  executingId,
  executing,
  onSelect,
  onNew,
  onExecute,
}: {
  pipelines: PipelineSummary[];
  loading: boolean;
  selectedId: string | null;
  runCounts: Map<string, number>;
  routeUnavailable: boolean;
  executingId: string | null;
  executing: boolean;
  onSelect: (id: string) => void;
  onNew: () => void;
  onExecute: (id: string) => void;
}) {
  return (
    <div className="frame mt-4 overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-rule/80 px-4 py-3">
        <div>
          <div className="text-eyebrow">Pipelines · deployed & draft</div>
          <div className="font-display text-[14px] text-bone">{pipelines.length} pipelines</div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone="primary">policy gated</Badge>
          <Badge tone="info">versioned</Badge>
          <Badge tone="info">auditable</Badge>
        </div>
      </div>

      {loading && <div className="px-5 py-8 text-center font-mono text-[12px] text-muted">loading...</div>}

      {!loading && pipelines.length === 0 && (
        <div className="flex flex-col items-center gap-3 px-5 py-12 text-center">
          <Workflow className="h-8 w-8 text-brass-2" />
          <div className="text-sm text-bone-2">No pipelines yet. Create one to get started.</div>
          <button className="v-btn-primary" disabled={routeUnavailable} onClick={onNew}>
            <Plus className="h-4 w-4" /> New pipeline
          </button>
        </div>
      )}

      {pipelines.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[860px] text-[12.5px]">
            <thead className="border-b border-rule/70 bg-ink-1/70 text-eyebrow">
              <tr>
                <th className="px-4 py-2 text-left">Name</th>
                <th className="px-4 py-2 text-left">Template</th>
                <th className="px-4 py-2 text-left">Policy refs</th>
                <th className="px-4 py-2 text-right">Nodes</th>
                <th className="px-4 py-2 text-right">Recent runs</th>
                <th className="px-4 py-2 text-left">Last run</th>
                <th className="px-4 py-2 text-left">Status</th>
                <th className="px-4 py-2 text-right" />
              </tr>
            </thead>
            <tbody>
              {pipelines.map((pipeline) => (
                <tr
                  key={pipeline.id}
                  className={cn(
                    "border-b border-rule/50 last:border-0 hover-elevate",
                    selectedId === pipeline.id && "bg-brass/5",
                  )}
                >
                  <td className="px-4 py-2">
                    <button className="text-left font-semibold text-bone hover:text-brass-2" onClick={() => onSelect(pipeline.id)}>
                      {pipeline.name}
                    </button>
                    <div className="font-mono text-[10.5px] text-muted">{pipeline.slug}</div>
                  </td>
                  <td className="px-4 py-2 text-muted">{pipeline.description || "workspace graph"}</td>
                  <td className="px-4 py-2">
                    <Badge tone="muted">{pipeline.latest_version?.policy_refs?.[0] ?? "default"}</Badge>
                  </td>
                  <td className="px-4 py-2 text-right font-mono">{pipeline.latest_version?.node_count ?? 0}</td>
                  <td className="px-4 py-2 text-right font-mono">{runCounts.get(pipeline.id) ?? 0}</td>
                  <td className="px-4 py-2 text-muted">{relativeTime(pipeline.updated_at)}</td>
                  <td className="px-4 py-2">
                    <Badge tone={pipeline.status === "active" ? "ok" : pipeline.status === "draft" ? "warn" : "muted"} dot>
                      {pipeline.status}
                    </Badge>
                  </td>
                  <td className="px-4 py-2 text-right">
                    <button
                      className="v-btn-ghost h-7 px-2"
                      disabled={routeUnavailable || executing}
                      onClick={() => onExecute(pipeline.id)}
                    >
                      {executingId === pipeline.id ? <Activity className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function RecentRunsPanel({ runs, loading }: { runs: PipelineRun[]; loading: boolean }) {
  return (
    <section className="frame mt-4 overflow-hidden">
      <header className="flex items-center justify-between border-b border-rule/80 px-5 py-3">
        <div>
          <div className="text-eyebrow">Recent runs</div>
          <h3 className="font-display mt-0.5 text-sm font-semibold text-bone">Cross-pipeline execution feed</h3>
        </div>
        <a href="#/monitoring" className="v-btn-ghost h-8 px-3 text-xs">
          <Activity className="h-4 w-4" /> Full audit trail
        </a>
      </header>
      <ul className="divide-y divide-rule/50">
        {loading && <li className="px-5 py-8 text-center font-mono text-[12px] text-muted">loading...</li>}
        {!loading && runs.length === 0 && (
          <li className="px-5 py-8 text-center font-mono text-[12px] text-muted">
            No runs yet. Execute a pipeline above to populate this feed.
          </li>
        )}
        {runs.map((run) => (
          <li key={run.id} className="flex items-start gap-3 px-5 py-3 font-mono text-[12px]">
            <div className={cn("mt-0.5 flex h-7 w-7 items-center justify-center rounded-md", runTone(run.status))}>
              <Sparkles className="h-3.5 w-3.5" />
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <Badge tone={run.status === "succeeded" ? "ok" : run.status === "failed" ? "warn" : "primary"}>{run.status}</Badge>
                <span className="text-bone-2">v{run.version}</span>
                <span className="text-muted">·</span>
                <span className="text-bone-2">{run.step_trace?.length ?? 0} steps</span>
                {run.total_latency_ms != null && <span className="text-muted">{run.total_latency_ms}ms</span>}
              </div>
              {run.error_message && <div className="mt-1 truncate text-crimson">{run.error_message}</div>}
            </div>
            <div className="shrink-0 text-right text-muted">
              <div>{relativeTime(run.created_at)}</div>
              {run.total_cost_usd != null && <div className="mt-0.5 text-bone">${run.total_cost_usd.toFixed(4)}</div>}
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}

function CreatePipelineModal({
  name,
  description,
  onName,
  onDescription,
  onClose,
  onCreate,
  pending,
  error,
}: {
  name: string;
  description: string;
  onName: (value: string) => void;
  onDescription: (value: string) => void;
  onClose: () => void;
  onCreate: () => void;
  pending: boolean;
  error: unknown;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/80 backdrop-blur-sm">
      <div className="frame w-full max-w-md p-5">
        <header className="mb-4 flex items-center justify-between">
          <h3 className="font-display text-lg font-semibold text-bone">New pipeline</h3>
          <button className="text-muted hover:text-bone" onClick={onClose}>
            <X className="h-4 w-4" />
          </button>
        </header>
        <div className="space-y-3">
          <label className="block">
            <div className="v-label">Name</div>
            <input className="v-input" value={name} onChange={(event) => onName(event.target.value)} placeholder="claims-triage" autoFocus />
          </label>
          <label className="block">
            <div className="v-label">Description</div>
            <textarea
              className="v-input"
              rows={2}
              value={description}
              onChange={(event) => onDescription(event.target.value)}
              placeholder="Optional summary"
            />
          </label>
          <div className="font-mono text-[10px] text-muted">
            Starter graph: input to policy gate to LLM. Add nodes later through{" "}
            <span className="text-bone">POST /pipelines/{"{id}"}/versions</span>.
          </div>
          {Boolean(error) && (
            <div className="text-[12px] text-crimson">{actionUnavailableMessage(error, "Pipeline creation")}</div>
          )}
          <div className="flex justify-end gap-2">
            <button className="v-btn-ghost" onClick={onClose}>
              Cancel
            </button>
            <button className="v-btn-primary" disabled={!name || pending} onClick={onCreate}>
              {pending ? "Creating..." : "Create"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function TemplateModal({
  templates,
  pending,
  error,
  onClose,
  onCreate,
}: {
  templates: PipelineTemplate[];
  pending: boolean;
  error: unknown;
  onClose: () => void;
  onCreate: (template: PipelineTemplate) => void;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/80 p-4 backdrop-blur-sm">
      <div className="frame w-full max-w-3xl p-5">
        <header className="mb-4 flex items-center justify-between gap-3">
          <div>
            <h3 className="font-display text-lg font-semibold text-bone">Install governed pipeline template</h3>
            <p className="mt-1 text-[12px] text-muted">
              Each template creates a real persisted pipeline with versioned graph and policy references.
            </p>
          </div>
          <button className="text-muted hover:text-bone" onClick={onClose}>
            <X className="h-4 w-4" />
          </button>
        </header>
        <div className="grid gap-3 md:grid-cols-2">
          {templates.map((template) => (
            <button
              key={template.key}
              className="rounded-lg border border-rule bg-ink-1/60 p-4 text-left transition hover:border-brass/50 hover:bg-brass/5 disabled:cursor-wait disabled:opacity-60"
              disabled={pending}
              onClick={() => onCreate(template)}
            >
              <div className="flex items-center justify-between gap-3">
                <div className="font-display text-[14px] font-semibold text-bone">{template.name}</div>
                <Badge tone="primary">{template.graph.nodes.length} nodes</Badge>
              </div>
              <p className="mt-2 min-h-10 text-[12px] leading-relaxed text-bone-2">{template.description}</p>
              <div className="mt-3 flex flex-wrap gap-1.5">
                {template.policyRefs.map((policy) => (
                  <Badge key={policy} tone="muted">
                    {policy}
                  </Badge>
                ))}
              </div>
            </button>
          ))}
        </div>
        {Boolean(error) && <div className="mt-3 text-[12px] text-crimson">{actionUnavailableMessage(error, "Template install")}</div>}
      </div>
    </div>
  );
}

function paletteGroups(): Array<{ name: string; items: Array<{ name: string; icon: ReactNode }> }> {
  return [
    {
      name: "Models",
      items: [
        { icon: <BrainCircuit className="h-3.5 w-3.5" />, name: "LLM (deployed)" },
        { icon: <Database className="h-3.5 w-3.5" />, name: "Embedding" },
        { icon: <Route className="h-3.5 w-3.5" />, name: "Reranker" },
      ],
    },
    {
      name: "Retrieval",
      items: [
        { icon: <Database className="h-3.5 w-3.5" />, name: "pgvector" },
        { icon: <Database className="h-3.5 w-3.5" />, name: "Qdrant" },
        { icon: <Database className="h-3.5 w-3.5" />, name: "Weaviate" },
        { icon: <FileJson className="h-3.5 w-3.5" />, name: "Document loader" },
      ],
    },
    {
      name: "Tools",
      items: [
        { icon: <Globe2 className="h-3.5 w-3.5" />, name: "HTTP" },
        { icon: <Database className="h-3.5 w-3.5" />, name: "SQL" },
        { icon: <TerminalSquare className="h-3.5 w-3.5" />, name: "Python" },
        { icon: <Code2 className="h-3.5 w-3.5" />, name: "File reader" },
      ],
    },
    {
      name: "Routing",
      items: [
        { icon: <ShieldCheck className="h-3.5 w-3.5" />, name: "Policy gate" },
        { icon: <Split className="h-3.5 w-3.5" />, name: "Semantic router" },
        { icon: <GitBranch className="h-3.5 w-3.5" />, name: "If / else" },
      ],
    },
    {
      name: "Output",
      items: [
        { icon: <FileJson className="h-3.5 w-3.5" />, name: "JSON formatter" },
        { icon: <Box className="h-3.5 w-3.5" />, name: "Markdown render" },
        { icon: <Webhook className="h-3.5 w-3.5" />, name: "Webhook" },
        { icon: <LockKeyhole className="h-3.5 w-3.5" />, name: "Audit signer" },
      ],
    },
  ];
}

function nodeIcon(type: string): ReactNode {
  if (type === "gate") return <ShieldCheck className="h-3.5 w-3.5" />;
  if (type === "model") return <BrainCircuit className="h-3.5 w-3.5" />;
  if (type === "tool") return <TerminalSquare className="h-3.5 w-3.5" />;
  if (type === "condition") return <Split className="h-3.5 w-3.5" />;
  return <FileJson className="h-3.5 w-3.5" />;
}

function nodeToneClass(type: string): string {
  if (type === "gate" || type === "model") return "border-brass/40";
  if (type === "condition") return "border-electric/35";
  if (type === "tool") return "border-moss/35";
  return "border-rule/80";
}

function nodeIconToneClass(type: string): string {
  if (type === "gate" || type === "model") return "bg-brass/15 text-brass-2";
  if (type === "condition") return "bg-electric/15 text-electric";
  if (type === "tool") return "bg-moss/15 text-moss";
  return "bg-ink-3 text-muted";
}

function runTone(status: PipelineRun["status"]): string {
  if (status === "succeeded") return "bg-moss/10 text-moss";
  if (status === "failed") return "bg-crimson/10 text-crimson";
  if (status === "blocked_policy") return "bg-brass/10 text-brass-2";
  return "bg-electric/10 text-electric";
}

function Badge({
  children,
  tone = "muted",
  dot,
}: {
  children: ReactNode;
  tone?: "muted" | "primary" | "ok" | "warn" | "info";
  dot?: boolean;
}) {
  return (
    <span
      className={cn(
        "chip",
        tone === "muted" && "border-rule bg-white/[0.02] text-bone-2",
        tone === "primary" && "border-brass/40 bg-brass/5 text-brass-2",
        tone === "ok" && "border-moss/30 bg-moss/5 text-moss",
        tone === "warn" && "border-amber/30 bg-amber/5 text-amber",
        tone === "info" && "border-electric/30 bg-electric/5 text-electric",
      )}
    >
      {dot && <span className="h-1.5 w-1.5 rounded-full bg-current" />}
      {children}
    </span>
  );
}

function RocketIcon() {
  return <Layers3 className="h-3.5 w-3.5" />;
}
