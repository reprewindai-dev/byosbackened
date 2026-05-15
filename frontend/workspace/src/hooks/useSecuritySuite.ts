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
    queryFn: async () => {
      const resp = await api.get<{
        stats?: { open?: number; last_24h?: number; security_score?: number };
        controls?: { name: string; enabled: boolean }[];
      }>("/security/dashboard");
      const stats = resp.data.stats ?? {};
      const controls = resp.data.controls ?? [];
      const enabled = (name: string) => controls.some((control) => control.name === name && control.enabled);
      const score = stats.security_score ?? 0;
      return {
        overall: score >= 80 ? "secure" : score >= 50 ? "degraded" : "critical",
        mfa_enforced: enabled("mfa_available"),
        sso_enabled: enabled("zero_trust_auth"),
        api_key_rotation_days: 30,
        last_audit_at: new Date().toISOString(),
        open_threats: stats.open ?? 0,
        policy_violations_24h: stats.last_24h ?? 0,
        trust_score: score,
      } satisfies ZeroTrustStatus;
    },
    refetchInterval: 30_000,
  });
}

export function useThreatEvents() {
  return useQuery({
    queryKey: ["security", "threats"],
    queryFn: async () => {
      const resp = await api.get<Array<{
        id: string;
        security_level: ThreatEvent["severity"];
        event_type: string;
        description: string | null;
        ip_address: string | null;
        workspace_id: string;
        created_at: string;
        status: string;
        resolved_at: string | null;
      }>>("/security/events");
      return resp.data.map((event) => ({
        id: event.id,
        severity: event.security_level,
        event_type: event.event_type,
        description: event.description ?? event.event_type,
        source_ip: event.ip_address,
        user_id: null,
        workspace_id: event.workspace_id,
        detected_at: event.created_at,
        resolved: event.status === "resolved",
        mitigated_at: event.resolved_at,
      })) satisfies ThreatEvent[];
    },
    refetchInterval: 15_000,
  });
}

export function useResolveThreat() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      api.put(`/security/events/${id}/resolve`, null, {
        params: { resolution: "resolved from workspace security page" },
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["security"] }),
  });
}

export function useKillSwitchState() {
  return useQuery({
    queryKey: ["kill-switch"],
    queryFn: async () => {
      const resp = await api.get<{ killed: boolean; reason?: string | null; activated_by?: string | null; activated_at?: string | null }>(
        "/cost/kill-switch/status",
      );
      return {
        active: resp.data.killed,
        reason: resp.data.reason ?? null,
        activated_by: resp.data.activated_by ?? null,
        activated_at: resp.data.activated_at ?? null,
        affects: resp.data.killed ? ["ai_calls"] : [],
      } satisfies KillSwitchState;
    },
    refetchInterval: 10_000,
  });
}

export function useActivateKillSwitch() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (reason: string) =>
      api.post("/cost/kill-switch", { reason }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["kill-switch"] }),
  });
}

export function useDeactivateKillSwitch() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.delete("/cost/kill-switch"),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["kill-switch"] }),
  });
}
