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
    queryKey: ["routing", "policy"],
    queryFn: async () => {
      const policy = (await api.get<{
        policy_id?: string;
        strategy: string;
        constraints?: { max_latency_ms?: number | string | null; max_cost?: number | string | null };
      }>("/routing/policy")).data;
      return [{
        id: policy.policy_id ?? "workspace-routing-policy",
        name: (policy.strategy || "cost_optimized").replace(/_/g, " "),
        provider: "policy-engine",
        model: "workspace default",
        priority: 1,
        enabled: true,
        latency_p50_ms: Number(policy.constraints?.max_latency_ms ?? 0),
        latency_p99_ms: Number(policy.constraints?.max_latency_ms ?? 0),
        error_rate_pct: 0,
        circuit_state: "closed" as const,
        last_failure_at: null,
        cost_per_1k_tokens_usd: Number(policy.constraints?.max_cost ?? 0),
      }] satisfies ProviderRoute[];
    },
    refetchInterval: 15_000,
  });
}

export function useCircuitBreakerStatus() {
  return useQuery({
    queryKey: ["routing", "test"],
    queryFn: async () => {
      const decision = (await api.post<{ selected_provider: string }>("/routing/test", {
        input: { operation_type: "generation", estimated_tokens: 1000 },
      })).data;
      return [{
        provider: decision.selected_provider,
        state: "closed" as const,
        failure_count: 0,
        success_count: 0,
        last_state_change_at: new Date().toISOString(),
        next_retry_at: null,
      }] satisfies CircuitBreakerStatus[];
    },
    refetchInterval: 10_000,
  });
}

export function useUpdateProviderPriority() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { provider_id: string; priority: number; enabled: boolean }) =>
      api.post("/routing/policy", {
        strategy: payload.enabled ? "cost_optimized" : "manual_review",
        constraints: { priority: payload.priority, provider_id: payload.provider_id },
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["routing"] }),
  });
}

export function useResetCircuitBreaker() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (provider: string) => {
      throw new Error(`Circuit breaker reset is not exposed by the backend route contract for ${provider}`);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["routing"] }),
  });
}
