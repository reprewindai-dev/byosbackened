/**
 * usePrivacy — wires /api/v1/privacy/* (PHI/PII redaction rules)
 * useContentSafety — wires /api/v1/content-safety/* (moderation rules)
 * useExplainability — wires /api/v1/explainability/* (per-decision traces)
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export type RedactionRule = {
  id: string;
  name: string;
  pattern_type: "regex" | "entity_type" | "keyword";
  pattern: string;
  entity_type: "PHI" | "PII" | "PCI" | "custom";
  replacement: string;
  enabled: boolean;
  created_at: string;
};

export type ContentSafetyRule = {
  id: string;
  name: string;
  category: "hate" | "violence" | "sexual" | "self_harm" | "harassment" | "custom";
  threshold: "low" | "medium" | "high";
  action: "block" | "flag" | "redact" | "log";
  enabled: boolean;
  triggered_count_7d: number;
};

export type DecisionTrace = {
  id: string;
  trace_id: string;
  operation: string;
  provider: string;
  model: string;
  policy_decision: "allow" | "block" | "redact" | "flag";
  rules_evaluated: string[];
  rules_triggered: string[];
  latency_ms: number;
  created_at: string;
  input_preview: string;
  output_preview: string | null;
};

// Privacy
export function useRedactionRules() {
  return useQuery({
    queryKey: ["privacy", "rules"],
    queryFn: async () => (await api.get<RedactionRule[]>("/privacy/rules")).data,
  });
}

export function useCreateRedactionRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: Omit<RedactionRule, "id" | "created_at">) =>
      api.post<RedactionRule>("/privacy/rules", payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["privacy"] }),
  });
}

export function useToggleRedactionRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) =>
      api.patch(`/privacy/rules/${id}`, { enabled }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["privacy"] }),
  });
}

export function useDeleteRedactionRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete(`/privacy/rules/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["privacy"] }),
  });
}

// Content Safety
export function useContentSafetyRules() {
  return useQuery({
    queryKey: ["content-safety", "rules"],
    queryFn: async () => (await api.get<ContentSafetyRule[]>("/content-safety/rules")).data,
  });
}

export function useUpdateContentSafetyRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...rest }: Partial<ContentSafetyRule> & { id: string }) =>
      api.patch(`/content-safety/rules/${id}`, rest),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["content-safety"] }),
  });
}

// Explainability
export function useDecisionTraces(filters?: { operation?: string; policy_decision?: string }) {
  return useQuery({
    queryKey: ["explainability", "traces", filters],
    queryFn: async () =>
      (await api.get<DecisionTrace[]>("/explainability/traces", { params: filters })).data,
    refetchInterval: 30_000,
  });
}

export function useDecisionTrace(traceId: string | null) {
  return useQuery({
    queryKey: ["explainability", "trace", traceId],
    queryFn: async () =>
      (await api.get<DecisionTrace>(`/explainability/traces/${traceId}`)).data,
    enabled: !!traceId,
  });
}
