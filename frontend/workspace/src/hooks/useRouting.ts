/**
 * useRouting — wires /api/v1/routing/* (provider routing config + circuit breaker state)
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export type ProviderRoute = {
  id: string;
  name: string;
  provider: string;
  model: string;
  priority: number;
  enabled: boolean;
  latency_p50_ms: number;
  latency_p99_ms: number;
  error_rate_pct: number;
  circuit_state: "closed" | "open" | "half_open";
  last_failure_at: string | null;
  cost_per_1k_tokens_usd: number;
};

export type CircuitBreakerStatus = {
  provider: string;
  state: "closed" | "open" | "half_open";
  failure_count: number;
  success_count: number;
  last_state_change_at: string;
  next_retry_at: string | null;
};

export function useProviderRoutes() {
  return useQuery({
    queryKey: ["routing", "providers"],
    queryFn: async () => (await api.get<ProviderRoute[]>("/routing/providers")).data,
    refetchInterval: 15_000,
  });
}

export function useCircuitBreakerStatus() {
  return useQuery({
    queryKey: ["routing", "circuit-breaker"],
    queryFn: async () =>
      (await api.get<CircuitBreakerStatus[]>("/routing/circuit-breaker/status")).data,
    refetchInterval: 10_000,
  });
}

export function useUpdateProviderPriority() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { provider_id: string; priority: number; enabled: boolean }) =>
      api.patch(`/routing/providers/${payload.provider_id}`, {
        priority: payload.priority,
        enabled: payload.enabled,
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["routing"] }),
  });
}

export function useResetCircuitBreaker() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (provider: string) =>
      api.post(`/routing/circuit-breaker/${provider}/reset`, {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["routing"] }),
  });
}
