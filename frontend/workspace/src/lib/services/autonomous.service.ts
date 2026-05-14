/**
 * Autonomous Intelligence Service
 * Maps to: backend/apps/api/routers/autonomous.py
 *
 * Competitive advantage: ML cost prediction, intelligent routing,
 * quality protection, failure risk, self-improving workspace.
 *
 * This is the BRAIN of the killer feature:
 *   Cost Prediction → Quality Prediction → Failure Risk → Route Select → Run → Record Outcome
 *
 * FULL EXECUTION CHAIN (call in this order before every run):
 *   1. predictCost()
 *   2. predictQuality()
 *   3. predictFailureRisk()
 *   4. selectRoute()
 *   --- RUN ---
 *   5. recordRoutingOutcome()
 *   6. writeAuditTrail (handled by backend on run completion)
 */
import { api } from "@/lib/api";

// ─── Cost (ML layer) ─────────────────────────────────────────────────────────

export interface MLCostPredictRequest {
  operation_type: string;
  provider: string;
  model: string;
  input_tokens?: number;
  estimated_output_tokens?: number;
}

export interface MLCostPredictResponse {
  predicted_cost: string;
  confidence_lower: string;
  confidence_upper: string;
  is_ml_prediction: boolean;
  model_version: string;
  sample_count?: number; // how many runs powered this prediction
}

// ─── Routing ──────────────────────────────────────────────────────────────────

export interface RouteSelectResponse {
  selected_provider: string;
  routing_stats: {
    total_decisions?: number;
    avg_savings_pct?: number;
    avg_quality_score?: number;
    avg_latency_ms?: number;
  };
  reason?: string;
}

export interface RoutingStatsResponse {
  operation_type: string;
  total_decisions: number;
  most_selected_provider: string;
  avg_savings_vs_baseline_pct: number;
  avg_quality_score: number;
  avg_latency_ms: number;
  learned_outcomes: number;
}

// ─── Quality ──────────────────────────────────────────────────────────────────

export interface QualityPredictResponse {
  predicted_quality: number;
  confidence_lower: number;
  confidence_upper: number;
  is_ml_prediction: boolean;
  model_version: string;
}

export interface QualityOptimizeResponse {
  selected_provider: string;
  expected_quality: number;
  expected_cost: string;
  meets_threshold: boolean;
}

export interface FailureRiskResponse {
  failure_risk: number; // 0.0–1.0
  risk_factors?: string[];
  recommended_action?: "proceed" | "warn" | "block" | "reroute";
}

// ─── Training ─────────────────────────────────────────────────────────────────

export interface TrainRequest {
  min_samples?: number; // default 100
}

export interface TrainResponse {
  status: "started" | "skipped" | "insufficient_data";
  message: string;
  sample_count?: number;
  models_trained?: string[];
}

export const autonomousService = {
  // ─── ML Cost Prediction ───────────────────────────────────────────────────
  /**
   * POST /api/v1/autonomous/cost/predict
   * Workspace-specific ML cost prediction.
   * Layer on top of /cost/predict — shows "Workspace ML estimate".
   * If sample_count is low, show: "Learning mode — needs more runs".
   */
  predictCostML: (body: MLCostPredictRequest) =>
    api.post<MLCostPredictResponse>("/autonomous/cost/predict", body),

  // ─── Routing ──────────────────────────────────────────────────────────────
  /**
   * POST /api/v1/autonomous/routing/select
   * PRE-RUN: workspace ML picks the best provider.
   * Show: "Selected provider: Groq — lower projected cost, acceptable quality"
   * NOTE: current backend uses query params, not JSON body.
   */
  selectRoute: (params: { operation_type: string; available_providers: string[] }) =>
    api.post<RouteSelectResponse>("/autonomous/routing/select", null, { params }),

  /**
   * POST /api/v1/autonomous/routing/update
   * POST-RUN: close the learning loop — MUST call after every run.
   * Without this, routing is not learning. It is just routing.
   */
  recordRoutingOutcome: (params: {
    operation_type: string;
    provider: string;
    actual_cost: number;
    actual_quality: number;
    actual_latency_ms: number;
    baseline_cost: number;
  }) => api.post("/autonomous/routing/update", null, { params }),

  /**
   * GET /api/v1/autonomous/routing/stats
   * Powers: Savings dashboard, Provider comparison, Proof of optimization.
   * Show: most selected provider, savings vs baseline, avg latency, quality score,
   * number of learned outcomes.
   * DO NOT show "30–70% savings" unless this endpoint proves it.
   */
  getRoutingStats: (params: { operation_type?: string; workspace_id?: string }) =>
    api.get<RoutingStatsResponse>("/autonomous/routing/stats", { params }),

  // ─── Quality ──────────────────────────────────────────────────────────────
  /**
   * POST /api/v1/autonomous/quality/predict
   * PRE-RUN: "Will this route still be good enough?"
   * Show in Playground preflight: Predicted quality 87% (confidence 80–92%).
   */
  predictQuality: (params: { operation_type: string; provider: string; input_text?: string }) =>
    api.post<QualityPredictResponse>("/autonomous/quality/predict", null, { params }),

  /**
   * POST /api/v1/autonomous/quality/optimize
   * User sets minimum quality threshold (slider: 85%).
   * Veklom routes inside that constraint.
   * DO NOT let cost savings override user quality thresholds.
   */
  optimizeForQuality: (params: {
    operation_type: string;
    available_providers: string[];
    min_quality: number;
  }) => api.post<QualityOptimizeResponse>("/autonomous/quality/optimize", null, { params }),

  /**
   * POST /api/v1/autonomous/quality/failure-risk
   * PRE-RUN: "Don't waste money on doomed runs."
   * If risk > threshold: warn user or reroute.
   * Show: "Failure risk: 12%" — if high: "High failure risk. Try alternate provider."
   */
  predictFailureRisk: (params: { operation_type: string; provider: string; input_text?: string }) =>
    api.post<FailureRiskResponse>("/autonomous/quality/failure-risk", null, { params }),

  // ─── Training ─────────────────────────────────────────────────────────────
  /**
   * POST /api/v1/autonomous/train
   * Train workspace intelligence models.
   * Show button states: "Not enough samples" / "Ready to train" / "Training started" / "Last trained".
   * DO NOT trigger without min_samples check.
   */
  trainWorkspace: (body: TrainRequest) =>
    api.post<TrainResponse>("/autonomous/train", body),
};
