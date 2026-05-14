/**
 * useInsights + useSuggestions — wires /api/v1/insights/* and /api/v1/suggestions/*
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export type WorkspaceInsight = {
  id: string;
  category: "cost" | "latency" | "reliability" | "compliance" | "growth" | "security";
  title: string;
  body: string;
  impact: "low" | "medium" | "high" | "critical";
  generated_at: string;
  read: boolean;
  dismissed: boolean;
  action_url: string | null;
};

export type WorkspaceSuggestion = {
  id: string;
  type: "model_swap" | "budget_cap" | "policy_tighten" | "team_invite" | "integration" | "upsell";
  title: string;
  rationale: string;
  estimated_saving_usd: number | null;
  priority: "low" | "medium" | "high";
  accepted: boolean | null;
  created_at: string;
};

export function useInsights() {
  return useQuery({
    queryKey: ["insights"],
    queryFn: async () =>
      (await api.get<WorkspaceInsight[]>("/insights")).data,
    refetchInterval: 60_000,
  });
}

export function useDismissInsight() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.patch(`/insights/${id}/dismiss`, {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["insights"] }),
  });
}

export function useMarkInsightRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.patch(`/insights/${id}/read`, {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["insights"] }),
  });
}

export function useSuggestions() {
  return useQuery({
    queryKey: ["suggestions"],
    queryFn: async () =>
      (await api.get<WorkspaceSuggestion[]>("/suggestions")).data,
    refetchInterval: 60_000,
  });
}

export function useRespondToSuggestion() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, accepted }: { id: string; accepted: boolean }) =>
      api.patch(`/suggestions/${id}/respond`, { accepted }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["suggestions"] }),
  });
}
