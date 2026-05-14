/**
 * useRoutingStats
 *
 * Load routing intelligence stats for Overview / Savings dashboard.
 *
 * Rules:
 *   - Do NOT show "30–70% savings" unless this hook returns data proving it.
 *   - Show actual: most selected provider, savings vs baseline, avg latency,
 *     quality score, number of learned outcomes.
 */
import { useEffect, useState } from "react";
import { autonomousService, type RoutingStatsResponse } from "@/lib/services/autonomous.service";

export function useRoutingStats(operation_type?: string) {
  const [stats, setStats] = useState<RoutingStatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    autonomousService
      .getRoutingStats({ operation_type })
      .then(({ data }) => setStats(data))
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Failed to load routing stats");
      })
      .finally(() => setLoading(false));
  }, [operation_type]);

  return { stats, loading, error };
}
