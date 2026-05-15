/**
 * usePreflightCheck
 *
 * Runs the full pre-run execution chain before every model/pipeline/tool run.
 *
 * Chain (in order):
 *   1. POST /cost/predict                      → predicted cost + alternatives
 *   2. POST /autonomous/cost/predict           → workspace ML cost estimate
 *   3. POST /autonomous/quality/predict        → predicted quality score
 *   4. POST /autonomous/quality/failure-risk   → failure risk score
 *   5. POST /autonomous/routing/select         → best provider selection
 *
 * After run completes, caller MUST call:
 *   recordOutcome() → POST /autonomous/routing/update
 *
 * This hook is the product spine. Wire it into:
 *   - Playground run panel
 *   - Marketplace listing preflight
 *   - Pipeline run preview
 *   - Deployment test preview
 */
import { useState, useCallback } from "react";
import { costIntelligenceService } from "@/lib/services/cost-intelligence.service";
import { autonomousService } from "@/lib/services/autonomous.service";

export interface PreflightInput {
  operation_type: string;
  provider?: string; // optional — routing/select will pick if omitted
  available_providers?: string[];
  model: string;
  input_text?: string;
  input_tokens?: number;
  estimated_output_tokens?: number;
  min_quality?: number;
}

export interface PreflightResult {
  // Cost
  predicted_cost: string;
  cost_confidence_lower: string;
  cost_confidence_upper: string;
  alternative_providers: Array<{ provider: string; model?: string; predicted_cost: string }>;
  prediction_id: string;

  // ML cost (workspace layer)
  ml_predicted_cost: string | null;
  ml_confidence_lower: string | null;
  ml_confidence_upper: string | null;
  is_ml_active: boolean;
  ml_sample_count: number;

  // Quality
  predicted_quality: number;
  quality_confidence_lower: number;
  quality_confidence_upper: number;

  // Failure risk
  failure_risk: number;
  risk_factors: string[];
  recommended_action: "proceed" | "warn" | "block" | "reroute";

  // Route
  selected_provider: string;
  routing_reason: string;
}

export interface PreflightState {
  loading: boolean;
  error: string | null;
  result: PreflightResult | null;
  /** Call this after run completes to close the learning loop */
  recordOutcome: (params: {
    actual_cost: number;
    actual_quality: number;
    actual_latency_ms: number;
    baseline_cost: number;
  }) => Promise<void>;
}

export function usePreflightCheck(): [
  (input: PreflightInput) => Promise<PreflightResult | null>,
  PreflightState
] {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<PreflightResult | null>(null);

  const runPreflight = useCallback(async (input: PreflightInput): Promise<PreflightResult | null> => {
    setLoading(true);
    setError(null);

    try {
      const providers = input.available_providers ?? [input.provider ?? "ollama"];
      const firstProvider = providers[0];

      // Run all predictions in parallel — don't block on each other
      const [
        costRes,
        mlCostRes,
        qualityRes,
        failureRes,
        routeRes,
      ] = await Promise.allSettled([
        // 1. Standard cost prediction
        costIntelligenceService.predictCost({
          operation_type: input.operation_type,
          provider: firstProvider,
          model: input.model,
          input_text: input.input_text,
          input_tokens: input.input_tokens,
          estimated_output_tokens: input.estimated_output_tokens,
        }),

        // 2. Workspace ML cost prediction
        autonomousService.predictCostML({
          operation_type: input.operation_type,
          provider: firstProvider,
          model: input.model,
          input_tokens: input.input_tokens,
          estimated_output_tokens: input.estimated_output_tokens,
        }),

        // 3. Quality prediction
        autonomousService.predictQuality({
          operation_type: input.operation_type,
          provider: firstProvider,
          input_text: input.input_text,
        }),

        // 4. Failure risk
        autonomousService.predictFailureRisk({
          operation_type: input.operation_type,
          provider: firstProvider,
          input_text: input.input_text,
        }),

        // 5. Route selection
        autonomousService.selectRoute({
          operation_type: input.operation_type,
          available_providers: providers,
        }),
      ]);

      const cost = costRes.status === "fulfilled" ? costRes.value.data : null;
      const mlCost = mlCostRes.status === "fulfilled" ? mlCostRes.value.data : null;
      const quality = qualityRes.status === "fulfilled" ? qualityRes.value.data : null;
      const failure = failureRes.status === "fulfilled" ? failureRes.value.data : null;
      const route = routeRes.status === "fulfilled" ? routeRes.value.data : null;

      const preflight: PreflightResult = {
        // Cost
        predicted_cost: cost?.predicted_cost ?? "unknown",
        cost_confidence_lower: cost?.confidence_lower ?? "0",
        cost_confidence_upper: cost?.confidence_upper ?? "0",
        alternative_providers: cost?.alternative_providers ?? [],
        prediction_id: cost?.prediction_id ?? "",

        // ML cost
        ml_predicted_cost: mlCost?.predicted_cost ?? null,
        ml_confidence_lower: mlCost?.confidence_lower ?? null,
        ml_confidence_upper: mlCost?.confidence_upper ?? null,
        is_ml_active: mlCost?.is_ml_prediction ?? false,
        ml_sample_count: mlCost?.sample_count ?? 0,

        // Quality
        predicted_quality: quality?.predicted_quality ?? 0,
        quality_confidence_lower: quality?.confidence_lower ?? 0,
        quality_confidence_upper: quality?.confidence_upper ?? 0,

        // Failure risk
        failure_risk: failure?.failure_risk ?? 0,
        risk_factors: failure?.risk_factors ?? [],
        recommended_action: failure?.recommended_action ?? "proceed",

        // Route
        selected_provider: route?.selected_provider ?? firstProvider,
        routing_reason: route?.routing_stats ? JSON.stringify(route.routing_stats) : "",
      };

      setResult(preflight);
      return preflight;
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Preflight check failed";
      setError(msg);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const recordOutcome = useCallback(async (params: {
    actual_cost: number;
    actual_quality: number;
    actual_latency_ms: number;
    baseline_cost: number;
  }) => {
    if (!result) return;
    await autonomousService.recordRoutingOutcome({
      operation_type: "generation",
      provider: result.selected_provider,
      ...params,
    });
  }, [result]);

  return [
    runPreflight,
    { loading, error, result, recordOutcome },
  ];
}
