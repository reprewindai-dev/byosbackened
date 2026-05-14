/**
 * usePredictionAccuracy
 *
 * Load prediction accuracy stats from cost history.
 * Powers the "Prediction Accuracy" panel.
 *
 * Rules:
 *   - Do NOT claim "95% within 5%" globally unless this data proves it
 *     for that workspace/platform.
 *   - Display: predictions this period, % within confidence, avg error, proven savings.
 */
import { useEffect, useState } from "react";
import { costIntelligenceService, type CostHistoryEntry } from "@/lib/services/cost-intelligence.service";

export interface PredictionAccuracyStats {
  total_predictions: number;
  within_confidence_count: number;
  within_confidence_pct: number;
  average_error_pct: number;
  proven_savings: string;
  entries: CostHistoryEntry[];
}

export function usePredictionAccuracy(params?: { from?: string; to?: string }) {
  const [stats, setStats] = useState<PredictionAccuracyStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    costIntelligenceService
      .getHistory({ ...params, limit: 500 })
      .then(({ data }) => {
        const entries = data ?? [];
        const withActual = entries.filter((e) => e.actual_cost !== null);
        const withinConf = withActual.filter((e) => e.was_within_confidence === true);
        const totalError = withActual.reduce((sum, e) => sum + (e.prediction_error_percent ?? 0), 0);
        const provenSavings = withActual.reduce((sum, e) => {
          const predicted = parseFloat(e.predicted_cost ?? "0");
          const actual = parseFloat(e.actual_cost ?? "0");
          return sum + Math.max(0, predicted - actual);
        }, 0);

        setStats({
          total_predictions: entries.length,
          within_confidence_count: withinConf.length,
          within_confidence_pct:
            withActual.length > 0 ? Math.round((withinConf.length / withActual.length) * 100) : 0,
          average_error_pct:
            withActual.length > 0 ? parseFloat((totalError / withActual.length).toFixed(2)) : 0,
          proven_savings: `$${provenSavings.toFixed(4)}`,
          entries,
        });
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Failed to load prediction accuracy");
      })
      .finally(() => setLoading(false));
  }, [params?.from, params?.to]);

  return { stats, loading, error };
}
