/**
 * useBudget — wires /api/v1/budget/* (budget caps + alerts)
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, noRoute } from "@/lib/api";

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
    queryFn: async () => {
      const { data } = await api.get<Array<{
        id: string;
        budget_type: string;
        amount: string;
        current_spend: string;
        percent_used: number;
        period_end: string;
      }>>("/budget");
      return data.map((budget) => ({
        id: budget.id,
        scope: "workspace",
        scope_id: "self",
        scope_label: budget.budget_type,
        period: budget.budget_type === "daily" ? "daily" : budget.budget_type === "weekly" ? "weekly" : "monthly",
        limit_usd: Number(budget.amount),
        spent_usd: Number(budget.current_spend),
        utilization_pct: budget.percent_used,
        alert_threshold_pct: 80,
        hard_stop: false,
        status: budget.percent_used >= 100 ? "exceeded" : budget.percent_used >= 80 ? "warning" : "ok",
        resets_at: budget.period_end,
      })) satisfies BudgetCap[];
    },
    refetchInterval: 30_000,
  });
}

export function useBudgetAlerts() {
  return useQuery({
    queryKey: ["budget", "alerts"],
    queryFn: async () => noRoute<BudgetAlert[]>("/budget/alerts"),
    refetchInterval: 20_000,
  });
}

export function useCreateBudgetCap() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: Omit<BudgetCap, "id" | "spent_usd" | "utilization_pct" | "status" | "resets_at">) =>
      api.post<BudgetCap>("/budget", {
        budget_type: payload.period,
        amount: payload.limit_usd,
        alert_thresholds: [payload.alert_threshold_pct],
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["budget"] }),
  });
}

export function useUpdateBudgetCap() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: Partial<BudgetCap> & { id: string }) =>
      noRoute(`/budget/caps/${payload.id}`, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["budget"] }),
  });
}

export function useDeleteBudgetCap() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => noRoute(`/budget/caps/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["budget"] }),
  });
}
