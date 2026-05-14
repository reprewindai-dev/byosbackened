// =============================================================================
// usePreflightCheck
// =============================================================================
// Runs the three pre-flight prediction endpoints in parallel:
//   POST /cost/predict
//   POST /autonomous/quality/predict   (GET with params)
//   POST /autonomous/quality/failure-risk (GET with params)
//
// After a run completes, call recordOutcome() to close the learning loop —
// this posts actual observed latency, token count, and a quality flag back
// to /autonomous/quality/outcome so the ML models improve over time.
//
// Usage:
//   const { preflight, runPreflight, recordOutcome } = usePreflightCheck();
//   await runPreflight({ provider, modelId, prompt, maxTokens });
//   // ... execute run ...
//   await recordOutcome({ provider, modelId, prompt, actualLatencyMs,
//                         actualTokens, success });
// =============================================================================

import { useCallback, useState } from "react";
import { api } from "@/lib/api";
import { responseDetail } from "@/lib/errors";

const PREFLIGHT_TIMEOUT_MS = 25_000;

export interface PreflightState {
  predicted_cost?: number;
  cost_confidence_lower?: number;
  cost_confidence_upper?: number;
  alternatives?: { provider: string; cost: string; savings_percent: number }[];
  predicted_quality?: number;
  failure_risk?: number;
  loading?: boolean;
  error?: string;
}

export interface PreflightInput {
  provider: string;
  modelId: string;
  prompt: string;
  maxTokens?: number;
}

export interface OutcomeInput {
  provider: string;
  modelId: string;
  prompt: string;
  actualLatencyMs: number;
  actualTokens: number;
  success: boolean;
  costUsd?: string;
  billingEventType?: string;
}

export function usePreflightCheck() {
  const [preflight, setPreflight] = useState<PreflightState>({});

  const runPreflight = useCallback(async (input: PreflightInput) => {
    if (!input.prompt.trim()) return;
    setPreflight({ loading: true });

    const params = {
      operation_type: "generation",
      provider: input.provider,
      input_text: input.prompt.slice(0, 2000),
    };

    try {
      // Run all three predictions concurrently — failures are non-fatal.
      const [costResult, qualityResult, riskResult] = await Promise.allSettled([
        api.post(
          "/cost/predict",
          {
            operation_type: "generation",
            provider: input.provider,
            input_text: input.prompt.slice(0, 4000),
            model: input.modelId,
          },
          { timeout: PREFLIGHT_TIMEOUT_MS },
        ),
        api.post("/autonomous/quality/predict", null, {
          params,
          timeout: PREFLIGHT_TIMEOUT_MS,
        }),
        api.post("/autonomous/quality/failure-risk", null, {
          params,
          timeout: PREFLIGHT_TIMEOUT_MS,
        }),
      ]);

      const next: PreflightState = { loading: false };

      if (costResult.status === "fulfilled") {
        const cost = costResult.value.data as {
          predicted_cost?: string;
          confidence_lower?: string;
          confidence_upper?: string;
          alternative_providers?: { provider: string; cost: string; savings_percent: number }[];
        };
        if (cost.predicted_cost != null) next.predicted_cost = parseFloat(cost.predicted_cost);
        if (cost.confidence_lower != null) next.cost_confidence_lower = parseFloat(cost.confidence_lower);
        if (cost.confidence_upper != null) next.cost_confidence_upper = parseFloat(cost.confidence_upper);
        if (cost.alternative_providers) next.alternatives = cost.alternative_providers;
      }

      if (qualityResult.status === "fulfilled") {
        const q = qualityResult.value.data as { predicted_quality?: number };
        if (q?.predicted_quality != null) next.predicted_quality = q.predicted_quality;
      }

      if (riskResult.status === "fulfilled") {
        const r = riskResult.value.data as { failure_risk?: number; risk?: number };
        const risk = r?.failure_risk ?? r?.risk;
        if (risk != null) next.failure_risk = risk;
      }

      // Surface an error only if the cost prediction (the primary signal) failed.
      if (costResult.status === "rejected") {
        const msg = responseDetail(costResult.reason);
        next.error = /timeout|network|ERR_NETWORK|ECONN/i.test(msg)
          ? "Pre-flight timed out reaching predictors. Run still works; retry in a moment."
          : msg;
      }

      setPreflight(next);
    } catch (err) {
      const msg = responseDetail(err);
      setPreflight({
        loading: false,
        error: /timeout|network|ERR_NETWORK|ECONN/i.test(msg)
          ? "Pre-flight timed out reaching predictors. Run still works; retry in a moment."
          : msg,
      });
    }
  }, []);

  // ---------------------------------------------------------------------------
  // recordOutcome — closes the ML learning loop.
  // Call this after every run completes (success or failure).
  // Best-effort: errors are swallowed so they never block the UI.
  // ---------------------------------------------------------------------------
  const recordOutcome = useCallback(async (input: OutcomeInput) => {
    try {
      await api.post(
        "/autonomous/quality/outcome",
        {
          operation_type: "generation",
          provider: input.provider,
          model: input.modelId,
          input_text: input.prompt.slice(0, 2000),
          actual_latency_ms: input.actualLatencyMs,
          actual_tokens: input.actualTokens,
          success: input.success,
          cost_usd: input.costUsd,
          billing_event_type: input.billingEventType,
        },
        { timeout: 10_000 },
      );
    } catch {
      // Best-effort — never surface outcome recording errors to the user.
    }
  }, []);

  const resetPreflight = useCallback(() => setPreflight({}), []);

  return { preflight, runPreflight, recordOutcome, resetPreflight, setPreflight };
}
