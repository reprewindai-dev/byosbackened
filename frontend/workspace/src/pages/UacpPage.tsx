import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Archive,
  CheckCircle2,
  Download,
  FileJson,
  LockKeyhole,
  Play,
  ShieldCheck,
  Sparkles,
  Wallet,
} from "lucide-react";
import { api } from "@/lib/api";
import { actionUnavailableMessage } from "@/lib/errors";
import { ProofStrip, RunStatePanel, type FlowStatus } from "@/components/workspace/FlowPrimitives";

interface WorkspaceModel {
  slug: string;
  name: string;
  provider?: string;
  enabled: boolean;
  connected: boolean;
}

interface ModelsResp {
  models?: WorkspaceModel[];
  items?: WorkspaceModel[];
}

interface AICompleteResponse {
  response_text: string;
  model: string;
  provider: string;
  requested_provider?: string;
  requested_model?: string;
  fallback_triggered?: boolean;
  routing_reason?: string;
  request_id: string;
  audit_log_id: string;
  audit_hash: string;
  prompt_tokens: number;
  output_tokens: number;
  total_tokens: number;
  latency_ms: number;
  cost_usd: string;
  reserve_balance_usd: string;
  reserve_debited: number;
  billing_event_type: string;
  pricing_tier: string;
}

interface CurrentSubscription {
  plan: string;
  status: string;
}

type UacpEventType = "uacp_plan_compile" | "uacp_run_execution" | "uacp_artifact_generation";

const DEFAULT_INTENT = `Turn a regulated AI support workflow into a governed execution plan.

The workflow should intake a customer message, detect PII/PHI, route to the correct model/tool path, require evidence for risky outputs, preserve an audit trail, and define what must happen before deployment.`;

const PRICE_COPY: Record<UacpEventType, string> = {
  uacp_plan_compile: "$1.50 Founding / $2.00 Standard / $2.50 Regulated",
  uacp_run_execution: "$3.00 Founding / $4.00 Standard / $5.00 Regulated",
  uacp_artifact_generation: "$5.00 Founding / $7.00 Standard / $10.00 Regulated",
};

async function fetchModels(): Promise<WorkspaceModel[]> {
  const resp = await api.get<ModelsResp | WorkspaceModel[]>("/workspace/models");
  const raw = Array.isArray(resp.data) ? resp.data : resp.data.models ?? resp.data.items ?? [];
  return raw
    .map((row) => ({
      slug: String(row.slug ?? ""),
      name: String(row.name ?? row.slug ?? ""),
      provider: row.provider,
      enabled: row.enabled !== false,
      connected: row.connected !== false,
    }))
    .filter((row) => row.slug);
}

async function fetchCurrentSubscription(): Promise<CurrentSubscription> {
  return (await api.get<CurrentSubscription>("/subscriptions/current")).data;
}

function systemPromptFor(eventType: UacpEventType): string {
  const base = [
    "You are UACP inside Veklom Sovereign AI Hub.",
    "Return governed planning/execution content only. Do not present raw chatbot advice.",
    "Every output must include intent scope, policy gates, execution graph, risk controls, evidence requirements, reserve/billing posture, archive record, and next action.",
    "Use concise institutional language. Avoid marketing copy.",
  ].join("\n");
  if (eventType === "uacp_run_execution") {
    return `${base}\nThis is a governed execution event. Validate the existing plan, simulate the approved control path, and produce execution trace steps.`;
  }
  if (eventType === "uacp_artifact_generation") {
    return `${base}\nThis is an artifact generation event. Produce a JSON-ready artifact with plan_id, run_contract, nodes, policy_tags, evidence_manifest, risks, and archive_summary.`;
  }
  return `${base}\nThis is a governed plan compile event. Compile raw intent into a controlled plan before production work begins.`;
}

async function runUacpEvent({
  model,
  intent,
  eventType,
}: {
  model: WorkspaceModel;
  intent: string;
  eventType: UacpEventType;
}) {
  const started = performance.now();
  const resp = await api.post<AICompleteResponse>(
    "/ai/complete",
    {
      model: model.slug,
      prompt: intent,
      messages: [{ role: "user", content: intent }],
      system_prompt: systemPromptFor(eventType),
      temperature: 0.15,
      top_p: 0.9,
      stream: false,
      response_format: eventType === "uacp_artifact_generation" ? "json" : "text",
      session_tag: "SOC2",
      auto_redact: true,
      sign_audit_on_export: true,
      lock_to_on_prem: false,
      billing_event_type: eventType,
      max_tokens: eventType === "uacp_artifact_generation" ? 1400 : 1000,
    },
    { timeout: 120_000 },
  );
  return { ...resp.data, measured_latency_ms: Math.round(performance.now() - started) };
}

function statusFromMutation(isPending: boolean, data?: unknown, error?: unknown): FlowStatus {
  if (isPending) return "running";
  if (data) return "succeeded";
  if (error) return "failed";
  return "idle";
}

export function UacpPage() {
  const queryClient = useQueryClient();
  const [intent, setIntent] = useState(DEFAULT_INTENT);
  const [selectedModelSlug, setSelectedModelSlug] = useState<string>("");
  const [lastEventType, setLastEventType] = useState<UacpEventType>("uacp_plan_compile");

  const models = useQuery({ queryKey: ["workspace-models"], queryFn: fetchModels, staleTime: 60_000 });
  const subscription = useQuery({ queryKey: ["subscription-current"], queryFn: fetchCurrentSubscription, staleTime: 60_000 });

  const connectedModels = useMemo(
    () => (models.data ?? []).filter((model) => model.enabled && model.connected),
    [models.data],
  );
  const selectedModel = useMemo(() => {
    return connectedModels.find((model) => model.slug === selectedModelSlug) ?? connectedModels[0] ?? null;
  }, [connectedModels, selectedModelSlug]);
  const isFreeEvaluation = !subscription.isLoading && (subscription.data?.plan === "free" || subscription.data?.status !== "active");

  const runMut = useMutation({
    mutationFn: (eventType: UacpEventType) => {
      if (!selectedModel) throw new Error("No connected model is available for UACP.");
      setLastEventType(eventType);
      return runUacpEvent({ model: selectedModel, intent: intent.trim(), eventType });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["wallet-balance"] });
      void queryClient.invalidateQueries({ queryKey: ["wallet-txns"] });
    },
  });

  const latest = runMut.data;
  const currentStatus = statusFromMutation(runMut.isPending, runMut.data, runMut.error);
  const canRun = Boolean(selectedModel && intent.trim()) && !runMut.isPending;

  const downloadArtifact = () => {
    if (!latest) return;
    const blob = new Blob([
      JSON.stringify(
        {
          feature: "uacp",
          billing_event_type: latest.billing_event_type,
          request_id: latest.request_id,
          audit_log_id: latest.audit_log_id,
          audit_hash: latest.audit_hash,
          provider: latest.provider,
          model: latest.model,
          cost_usd: latest.cost_usd,
          generated_at: new Date().toISOString(),
          artifact: latest.response_text,
        },
        null,
        2,
      ),
    ], { type: "application/json" });
    const href = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = href;
    anchor.download = `veklom-uacp-artifact-${latest.request_id}.json`;
    anchor.click();
    URL.revokeObjectURL(href);
  };

  return (
    <div className="mx-auto w-full max-w-7xl space-y-6">
      <header className="grid gap-4 lg:grid-cols-[1.4fr_0.8fr]">
        <div>
          <div className="text-eyebrow">Workspace · UACP</div>
          <h1 className="font-display mt-2 text-[34px] font-semibold tracking-tight text-bone">
            UACP governed planning chamber
          </h1>
          <p className="mt-3 max-w-3xl text-sm leading-6 text-bone-2">
            Compile raw AI/business intent into a governed execution plan before it becomes a pipeline. UACP is a paid
            institutional surface: compile, run, and artifact generation all debit operating reserve and write audit proof.
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <span className="v-chip v-chip-brass">
              <Wallet className="h-3 w-3" />
              no free UACP runs
            </span>
            <span className="v-chip v-chip-ok">
              <ShieldCheck className="h-3 w-3" />
              reserve + audit gated
            </span>
            <span className="v-chip">
              <LockKeyhole className="h-3 w-3" />
              tenant scoped
            </span>
          </div>
        </div>
        <div className="frame p-4">
          <div className="text-eyebrow">Billable UACP events</div>
          <div className="mt-3 space-y-3 text-sm">
            {Object.entries(PRICE_COPY).map(([key, price]) => (
              <div key={key} className="flex items-start justify-between gap-3 border-b border-rule/70 pb-2 last:border-0 last:pb-0">
                <span className="capitalize text-bone-2">{key.replace(/_/g, " ")}</span>
                <span className="max-w-[210px] text-right font-mono text-[11px] text-brass-2">{price}</span>
              </div>
            ))}
          </div>
        </div>
      </header>

      {isFreeEvaluation && (
        <section className="rounded-xl border border-brass/35 bg-brass/[0.055] p-4 text-sm text-brass-2">
          UACP is not included in Free Evaluation. Activate the workspace and fund operating reserve before compiling
          plans, executing UACP runs, or generating artifacts.
        </section>
      )}

      <section className="grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
        <div className="frame overflow-hidden">
          <div className="border-b border-rule/80 bg-ink-1/60 px-4 py-3">
            <div className="text-eyebrow">Intent input</div>
            <h2 className="font-display mt-1 text-lg font-semibold text-bone">What should UACP govern?</h2>
          </div>
          <div className="space-y-4 p-4">
            <textarea
              className="min-h-[280px] w-full resize-y rounded-xl border border-rule bg-black/25 p-4 text-sm leading-6 text-bone outline-none transition focus:border-brass/50"
              value={intent}
              maxLength={8000}
              onChange={(event) => setIntent(event.target.value)}
              placeholder="Describe the AI workflow, business process, policy boundary, toolchain, deployment path, or regulated operation you want governed before production."
            />
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="text-[11px] text-muted">
                {intent.length.toLocaleString()} / 8,000 · paid compile/run/artifact surface
              </div>
              <select
                className="rounded-md border border-rule bg-ink-1 px-3 py-2 text-xs text-bone"
                value={selectedModel?.slug ?? ""}
                onChange={(event) => setSelectedModelSlug(event.target.value)}
              >
                {connectedModels.length === 0 && <option value="">No connected models</option>}
                {connectedModels.map((model) => (
                  <option key={model.slug} value={model.slug}>
                    {model.name} · {model.provider ?? "provider"}
                  </option>
                ))}
              </select>
            </div>

            <div className="grid gap-2 md:grid-cols-3">
              <button className="v-btn-primary h-10" disabled={!canRun} onClick={() => runMut.mutate("uacp_plan_compile")}>
                <Sparkles className="h-4 w-4" />
                Compile plan
              </button>
              <button className="v-btn-ghost h-10" disabled={!canRun} onClick={() => runMut.mutate("uacp_run_execution")}>
                <Play className="h-4 w-4" />
                Run UACP
              </button>
              <button className="v-btn-ghost h-10" disabled={!canRun} onClick={() => runMut.mutate("uacp_artifact_generation")}>
                <FileJson className="h-4 w-4" />
                Generate artifact
              </button>
            </div>

            {runMut.isError && (
              <div className="rounded-md border border-crimson/35 bg-crimson/5 p-3 text-[12px] text-crimson">
                {actionUnavailableMessage(runMut.error, "UACP paid action")}
              </div>
            )}
          </div>
        </div>

        <div className="space-y-4">
          <RunStatePanel
            eyebrow="UACP execution state"
            title="Paid governed planning event"
            status={currentStatus}
            summary="This is not a free Playground run. The action gates reserve, model route, policy posture, audit, and evidence before returning output."
            steps={[
              {
                label: "Reserve gate",
                status: runMut.isPending ? "running" : latest ? "succeeded" : runMut.isError ? "failed" : "idle",
                detail: latest ? `${latest.billing_event_type.replace(/_/g, " ")} · ${latest.cost_usd}` : PRICE_COPY[lastEventType],
              },
              {
                label: "Policy and route",
                status: runMut.isPending ? "running" : latest ? "succeeded" : runMut.isError ? "failed" : "idle",
                detail: latest ? `${latest.provider} · ${latest.model}` : selectedModel?.slug ?? "waiting for model",
              },
              {
                label: "Archive proof",
                status: runMut.isPending ? "idle" : latest ? "succeeded" : runMut.isError ? "failed" : "idle",
                detail: latest?.audit_hash ? `audit ${latest.audit_hash.slice(0, 12)}` : "signed evidence required",
              },
            ]}
            metrics={[
              { label: "Event", value: latest?.billing_event_type?.replace(/_/g, " ") ?? lastEventType.replace(/_/g, " ") },
              { label: "Latency", value: latest ? `${latest.latency_ms} ms` : "-" },
              { label: "Reserve", value: latest ? `$${latest.cost_usd}` : "paid only" },
              { label: "Tokens", value: latest ? String(latest.total_tokens) : "-" },
            ]}
            result={latest ? <UacpResult response={latest.response_text} /> : undefined}
            actions={[
              { label: "Open Pipelines", to: "/pipelines", primary: true, disabled: !latest },
              { label: "Open Billing", to: "/billing" },
              { label: "Download artifact", onClick: downloadArtifact, disabled: !latest },
            ]}
          />

          <ProofStrip
            items={[
              { label: "Billing rule", value: "No free UACP events" },
              { label: "Audit", value: latest?.audit_log_id ?? "pending" },
              { label: "Reserve balance", value: latest ? `$${latest.reserve_balance_usd}` : "requires paid reserve" },
              { label: "Pricing tier", value: latest?.pricing_tier?.replace(/_/g, " ") ?? "activation required" },
            ]}
          />
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-4">
        {[
          ["Intent-scope", "Define what the institution is trying to do before execution starts."],
          ["Policy-review", "Resolve controls, route constraints, approval gates, and evidence obligations."],
          ["Run-contract", "State what must be true before a plan becomes deployable work."],
          ["Archives", "Attach audit hash, lineage, and replay material to the governed artifact."],
        ].map(([title, copy]) => (
          <div key={title} className="frame p-4">
            <div className="flex items-center gap-2 text-eyebrow">
              <CheckCircle2 className="h-3 w-3 text-moss" />
              {title}
            </div>
            <p className="mt-3 text-sm leading-6 text-bone-2">{copy}</p>
          </div>
        ))}
      </section>
    </div>
  );
}

function UacpResult({ response }: { response: string }) {
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.16em] text-moss">
        <Archive className="h-3.5 w-3.5" />
        Compiled output
      </div>
      <pre className="max-h-[360px] overflow-auto whitespace-pre-wrap rounded-lg border border-rule/70 bg-black/35 p-4 text-[12px] leading-6 text-bone-2">
        {response}
      </pre>
      <div className="flex items-center gap-2 text-[11px] text-muted">
        <Download className="h-3.5 w-3.5" />
        Download uses the already generated paid artifact from this audited run.
      </div>
    </div>
  );
}
