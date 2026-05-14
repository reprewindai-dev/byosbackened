/**
 * useAiHelpers — wires /api/v1/ai/* (generate, extract, classify)
 * useExec — wires /v1/exec (top-level unified prompt execution)
 */
import { useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api";

export type AiGeneratePayload = {
  prompt: string;
  system_prompt?: string;
  model?: string;
  provider?: string;
  max_tokens?: number;
  temperature?: number;
  workspace_id?: string;
};

export type AiGenerateResult = {
  text: string;
  model: string;
  provider: string;
  tokens_used: number;
  latency_ms: number;
  cost_usd: string;
};

export type AiExtractPayload = {
  text: string;
  schema: Record<string, string>;
  model?: string;
};

export type AiClassifyPayload = {
  text: string;
  labels: string[];
  model?: string;
  multi_label?: boolean;
};

export type AiClassifyResult = {
  label: string;
  confidence: number;
  all_scores: Record<string, number>;
};

export type ExecPayload = {
  prompt: string;
  system_prompt?: string;
  model?: string;
  provider?: string;
  memory?: boolean;
  governed?: boolean;
  workspace_id?: string;
  metadata?: Record<string, unknown>;
};

export type ExecResult = {
  output: string;
  model: string;
  provider: string;
  tokens_used: number;
  latency_ms: number;
  cost_usd: string;
  circuit_state: string;
  memory_used: boolean;
  policy_passed: boolean;
  trace_id: string;
};

/** POST /api/v1/ai/generate */
export function useAiGenerate() {
  return useMutation({
    mutationFn: (payload: AiGeneratePayload) =>
      api.post<AiGenerateResult>("/ai/generate", payload).then((r) => r.data),
  });
}

/** POST /api/v1/ai/extract */
export function useAiExtract() {
  return useMutation({
    mutationFn: (payload: AiExtractPayload) =>
      api.post<Record<string, unknown>>("/ai/extract", payload).then((r) => r.data),
  });
}

/** POST /api/v1/ai/classify */
export function useAiClassify() {
  return useMutation({
    mutationFn: (payload: AiClassifyPayload) =>
      api.post<AiClassifyResult>("/ai/classify", payload).then((r) => r.data),
  });
}

/**
 * POST /v1/exec — top-level unified execution (no /api prefix).
 * Uses memory + circuit breaker + policy in a single call.
 */
export function useExec() {
  return useMutation({
    mutationFn: (payload: ExecPayload) =>
      api.post<ExecResult>("/v1/exec", payload, { baseURL: "/" }).then((r) => r.data),
  });
}
