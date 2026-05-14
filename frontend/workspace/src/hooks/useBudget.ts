/**
 * useBudget — wires /api/v1/budget/* (budget caps + alerts)
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export type BudgetCap = {
  id: string;
  scope: "workspace" | "model" | "user";
  scope_id: string;
  scope_label: string;
  period: "daily" | "weekly" | "monthly";
  limit_usd: number;
  spent_usd: number;
  utilization_pct: number;
  alert_threshold_pct: number;
  hard_stop: boolean;
  status: "ok" | "warning" | "exceeded" | "paused";
  resets_at: string;
};

export type BudgetAlert = {
  id: string;
  cap_id: string;
  scope_label: string;
  triggered_at: string;
  threshold_pct: number;
  spent_usd: number;
  limit_usd: number;
  resolved: boolean;
};

export function useBudgetCaps() {
  return useQuery({
    queryKey: ["budget", "caps"],
    queryFn: async () => (await api.get<BudgetCap[]>("/budget/caps")).data,
    refetchInterval: 30_000,
  });
}

export function useBudgetAlerts() {
  return useQuery({
    queryKey: ["budget", "alerts"],
    queryFn: async () => (await api.get<BudgetAlert[]>("/budget/alerts")).data,
    refetchInterval: 20_000,
  });
}

export function useCreateBudgetCap() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: Omit<BudgetCap, "id" | "spent_usd" | "utilization_pct" | "status" | "resets_at">) =>
      api.post<BudgetCap>("/budget/caps", payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["budget"] }),
  });
}

export function useUpdateBudgetCap() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...rest }: Partial<BudgetCap> & { id: string }) =>
      api.patch(`/budget/caps/${id}`, rest),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["budget"] }),
  });
}

export function useDeleteBudgetCap() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete(`/budget/caps/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["budget"] }),
  });
}
