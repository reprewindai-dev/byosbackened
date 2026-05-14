/**
 * useSecuritySuite — wires /api/v1/security/* (zero-trust status + threat events)
 * useKillSwitch — wires /api/v1/kill-switch/*
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export type ZeroTrustStatus = {
  overall: "secure" | "degraded" | "critical";
  mfa_enforced: boolean;
  sso_enabled: boolean;
  api_key_rotation_days: number;
  last_audit_at: string;
  open_threats: number;
  policy_violations_24h: number;
  trust_score: number;
};

export type ThreatEvent = {
  id: string;
  severity: "info" | "low" | "medium" | "high" | "critical";
  event_type: string;
  description: string;
  source_ip: string | null;
  user_id: string | null;
  workspace_id: string;
  detected_at: string;
  resolved: boolean;
  mitigated_at: string | null;
};

export type KillSwitchState = {
  active: boolean;
  reason: string | null;
  activated_by: string | null;
  activated_at: string | null;
  affects: string[];
};

export function useZeroTrustStatus() {
  return useQuery({
    queryKey: ["security", "zero-trust"],
    queryFn: async () =>
      (await api.get<ZeroTrustStatus>("/security/zero-trust/status")).data,
    refetchInterval: 30_000,
  });
}

export function useThreatEvents() {
  return useQuery({
    queryKey: ["security", "threats"],
    queryFn: async () =>
      (await api.get<ThreatEvent[]>("/security/threats")).data,
    refetchInterval: 15_000,
  });
}

export function useResolveThreat() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.patch(`/security/threats/${id}/resolve`, {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["security"] }),
  });
}

export function useKillSwitchState() {
  return useQuery({
    queryKey: ["kill-switch"],
    queryFn: async () =>
      (await api.get<KillSwitchState>("/kill-switch/state")).data,
    refetchInterval: 10_000,
  });
}

export function useActivateKillSwitch() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (reason: string) =>
      api.post("/kill-switch/activate", { reason }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["kill-switch"] }),
  });
}

export function useDeactivateKillSwitch() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post("/kill-switch/deactivate", {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["kill-switch"] }),
  });
}
