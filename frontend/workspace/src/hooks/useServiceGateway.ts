/**
 * useServiceGateway — hooks for /api/v1/services/* (BYOS internal service registry)
 *
 * Manages BYOS's own internal services: AI providers (Ollama, Groq),
 * workspace gateway, billing engine, security suite, monitoring, etc.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export type ServiceType = "ai_provider" | "core" | "integration" | "monitoring" | "billing";
export type ServiceStatus = "healthy" | "degraded" | "unhealthy" | "unknown";

export type RegisteredService = {
  service_id: string;
  name: string;
  service_type: ServiceType;
  base_url: string;
  status: ServiceStatus;
  enabled: boolean;
  last_health_check: number | null;
  metadata: Record<string, unknown>;
};

export type ServiceTopologyLayer = {
  id: string;
  name: string;
  url: string;
  status: ServiceStatus;
  enabled: boolean;
};

export type WiringEdge = {
  from: string;
  to: string;
  protocol: string;
  description: string;
};

export type ServiceTopology = {
  platform: string;
  version: string;
  layers: {
    ai_providers: ServiceTopologyLayer[];
    core: ServiceTopologyLayer[];
    integrations: ServiceTopologyLayer[];
    monitoring: ServiceTopologyLayer[];
    billing: ServiceTopologyLayer[];
  };
  wiring: WiringEdge[];
  timestamp: number;
};

export function useServiceRegistry(serviceType?: ServiceType) {
  return useQuery({
    queryKey: ["services", "registry", serviceType],
    queryFn: async () => {
      const params = serviceType ? `?service_type=${serviceType}` : "";
      const res = await api.get<{
        services: RegisteredService[];
        total: number;
        source: string;
        timestamp: number;
      }>(`/services/registry${params}`);
      return res.data;
    },
    refetchInterval: 30_000,
  });
}

export function useServiceDetail(serviceId: string) {
  return useQuery({
    queryKey: ["services", "detail", serviceId],
    queryFn: async () => (await api.get<RegisteredService>(`/services/registry/${serviceId}`)).data,
    enabled: !!serviceId,
  });
}

export function useServiceTopology() {
  return useQuery({
    queryKey: ["services", "topology"],
    queryFn: async () => (await api.get<ServiceTopology>("/services/topology")).data,
    refetchInterval: 60_000,
  });
}

export function useServiceProviders() {
  return useQuery({
    queryKey: ["services", "providers"],
    queryFn: async () => (await api.get("/services/providers")).data,
    refetchInterval: 15_000,
  });
}

export function useServiceCircuitBreaker() {
  return useQuery({
    queryKey: ["services", "circuit-breaker"],
    queryFn: async () => (await api.get("/services/circuit-breaker/status")).data,
    refetchInterval: 10_000,
  });
}

export function useRegisterService() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: {
      service_id: string;
      name: string;
      service_type: ServiceType;
      base_url?: string;
      metadata?: Record<string, unknown>;
    }) => api.post("/services/register", payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["services"] }),
  });
}

export function useUpdateService() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: {
      service_id: string;
      base_url?: string;
      enabled?: boolean;
      metadata?: Record<string, unknown>;
    }) => {
      const { service_id, ...body } = payload;
      return api.patch(`/services/registry/${service_id}`, body);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["services"] }),
  });
}

export function useReportServiceHealth() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: {
      service_id: string;
      status: ServiceStatus;
      details?: Record<string, unknown>;
    }) => api.post("/services/health-report", payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["services"] }),
  });
}
