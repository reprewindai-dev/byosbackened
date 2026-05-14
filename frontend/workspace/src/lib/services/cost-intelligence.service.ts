/**
 * Cost Intelligence Engine
 * Maps to: backend/apps/api/routers/cost.py
 *
 * Competitive advantage: Know cost BEFORE running.
 * Source claim: Cost Prediction + Intelligent Routing + Audit Trail = killer feature.
 *
 * Usage rule:
 *   Call predictCost() BEFORE every run in Playground, Marketplace preflight,
 *   Pipeline preview, Deployment test. Never after. Never hardcode prices in UI.
 */
import { api } from "@/lib/api";

export interface CostPredictRequest {
  operation_type: "generation" | "embedding" | "classification" | "transcription" | string;
  provider: string;
  model: string;
  input_text?: string;
  input_tokens?: number;
  estimated_output_tokens?: number;
}

export interface CostPredictResponse {
  predicted_cost: string;
  confidence_lower: string;
  confidence_upper: string;
  accuracy_score: number;
  alternative_providers: Array<{
    provider: string;
    model?: string;
    predicted_cost: string;
  }>;
  input_tokens: number;
  estimated_output_tokens: number;
  prediction_id: string;
}

export interface CostHistoryEntry {
  id: string;
  operation_type: string;
  provider: string;
  model: string;
  predicted_cost: string;
  actual_cost: string | null;
  prediction_error_percent: number | null;
  was_within_confidence: boolean | null;
  created_at: string;
}

export interface CostBreakdown {
  period_total: string;
  by_provider: Record<string, string>;
  by_model: Record<string, string>;
  by_operation: Record<string, string>;
  savings_vs_baseline: string;
}

export const costIntelligenceService = {
  /**
   * POST /api/v1/cost/predict
   * Pre-flight: call before EVERY run.
   * Shows user: Predicted cost, confidence band, cheaper alternatives.
   */
  predictCost: (body: CostPredictRequest) =>
    api.post<CostPredictResponse>("/cost/predict", body),

  /**
   * GET /api/v1/cost/history
   * Powers "Prediction Accuracy" panel.
   * Shows: predictions this period, % within confidence, avg error, proven savings.
   */
  getHistory: (params?: { page?: number; limit?: number; provider?: string; from?: string; to?: string }) =>
    api.get<CostHistoryEntry[]>("/cost/history", { params }),

  /**
   * GET /api/v1/cost/breakdown
   * Powers Billing overview and cost allocation panels.
   */
  getBreakdown: (params?: { from?: string; to?: string; provider?: string }) =>
    api.get<CostBreakdown>("/cost/breakdown", { params }),

  /**
   * GET /api/v1/cost/estimate
   * Quick estimate by model/token count without full prediction pipeline.
   */
  getEstimate: (params: { model: string; tokens: number; provider?: string }) =>
    api.get("/cost/estimate", { params }),

  /**
   * GET /api/v1/budget
   * Budget cap state — show risk level on Overview.
   */
  getBudget: () => api.get("/budget"),

  /**
   * POST /api/v1/budget
   */
  setBudget: (body: { monthly_limit: number; alert_threshold?: number }) =>
    api.post("/budget", body),

  /**
   * PATCH /api/v1/budget
   */
  updateBudget: (body: { monthly_limit?: number; alert_threshold?: number }) =>
    api.patch("/budget", body),
};
