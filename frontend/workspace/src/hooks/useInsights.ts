/**
 * useInsights + useSuggestions — wires /api/v1/insights/* and /api/v1/suggestions/*
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, noRoute } from "@/lib/api";

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
    queryFn: async () => {
      const { data } = await api.get<{
        savings?: { total?: string; percent?: number; projected_next_month?: string };
        performance?: { latency_reduction_ms?: number; cache_hit_rate_improvement?: number };
        operations?: { count?: number };
      }>("/insights/summary");
      return [
        {
          id: "insights-summary",
          category: "cost",
          title: "Savings intelligence",
          body: `Saved ${data.savings?.total ?? "0"} (${data.savings?.percent ?? 0}%). Projected next month: ${data.savings?.projected_next_month ?? "0"}.`,
          impact: "high",
          generated_at: new Date().toISOString(),
          read: false,
          dismissed: false,
          action_url: "/billing",
        },
        {
          id: "performance-summary",
          category: "latency",
          title: "Performance improvement",
          body: `${data.performance?.latency_reduction_ms ?? 0} ms latency reduction across ${data.operations?.count ?? 0} operations.`,
          impact: "medium",
          generated_at: new Date().toISOString(),
          read: false,
          dismissed: false,
          action_url: "/monitoring",
        },
      ] satisfies WorkspaceInsight[];
    },
    refetchInterval: 60_000,
  });
}

export function useDismissInsight() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => noRoute(`/insights/${id}/dismiss`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["insights"] }),
  });
}

export function useMarkInsightRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => noRoute(`/insights/${id}/read`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["insights"] }),
  });
}

export function useSuggestions() {
  return useQuery({
    queryKey: ["suggestions"],
    queryFn: async () => {
      const { data } = await api.get<{
        suggestions: Array<{ type: string; title: string; description: string; impact: string; priority: number }>;
      }>("/suggestions");
      const rows: WorkspaceSuggestion[] = (data.suggestions ?? []).map((s, index) => ({
        id: `${s.type}-${index}`,
        type: s.type as WorkspaceSuggestion["type"],
        title: s.title,
        rationale: s.description,
        estimated_saving_usd: null,
        priority: s.impact === "high" ? "high" : s.impact === "medium" ? "medium" : "low",
        accepted: null,
        created_at: new Date().toISOString(),
      }));
      return rows;
    },
    refetchInterval: 60_000,
  });
}

export function useRespondToSuggestion() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, accepted }: { id: string; accepted: boolean }) =>
      noRoute(`/suggestions/${id}/respond`, accepted),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["suggestions"] }),
  });
}
