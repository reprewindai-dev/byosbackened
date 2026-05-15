import { api } from "@/lib/api";

/**
 * Internal operator + internal UACP bridge routes.
 * These are superuser/automation-key only and are customer-safe wrappers.
 */
export const internalService = {
  // ---------------------------------------------------------
  // Operators
  // ---------------------------------------------------------
  operatorOverview: () => api.get("/operators"),

  operatorDigest: () => api.get("/operators/digest"),

  runOperatorWatch: () => api.post("/operators/watch"),

  queueQstashJob: (body: Record<string, unknown>) =>
    api.post("/operators/qstash/enqueue", body),

  triggerMaintenanceWorkflow: (body: Record<string, unknown>) =>
    api.post("/operators/workflows/uacp-maintenance/trigger", body),

  listWorkers: (params?: { limit?: number }) => api.get("/operators/workers", { params }),

  getWorkerRegistry: () => api.get("/operators/registry"),

  getWorker: (workerId: string) => api.get(`/operators/workers/${encodeURIComponent(workerId)}`),

  workerHeartbeat: (workerId: string, body: Record<string, unknown>) =>
    api.post(`/operators/workers/${encodeURIComponent(workerId)}/heartbeat`, body),

  createWorkerRun: (body: Record<string, unknown>) =>
    api.post("/operators/runs", body),

  listWorkerRuns: (params?: { limit?: number }) =>
    api.get("/operators/runs", { params }),

  // ---------------------------------------------------------
  // Internal UACP bridge
  // ---------------------------------------------------------
  getUacpSummary: () => api.get("/internal/uacp/summary"),

  getUacpEvents: (params?: { limit?: number }) =>
    api.get("/internal/uacp/events", { params }),

  getUacpEventStream: (params?: { limit?: number }) =>
    api.get("/internal/uacp/event-stream", { params }),

  getEvaluationSurgeon: (params?: { limit?: number }) =>
    api.get("/internal/uacp/evaluation-surgeon", { params }),

  getGrowthOpportunities: (params?: { limit?: number }) =>
    api.get("/internal/uacp/growth-opportunities", { params }),

  listUacpWorkspaces: (params?: { limit?: number }) =>
    api.get("/internal/uacp/workspaces", { params }),

  listUacpRuns: (params?: { limit?: number }) =>
    api.get("/internal/uacp/runs", { params }),

  searchUacp: (params: { query: string; limit?: number; filter?: string; reranking?: boolean; semantic_weight?: number; input_enrichment?: boolean }) =>
    api.get("/internal/uacp/search", { params }),

  listDeployments: (params?: { limit?: number }) =>
    api.get("/internal/uacp/deployments", { params }),

  getBilling: (params?: { limit?: number }) =>
    api.get("/internal/uacp/billing", { params }),

  listEvidence: (params?: { limit?: number }) =>
    api.get("/internal/uacp/evidence", { params }),

  getUacpMonitoring: () => api.get("/internal/uacp/monitoring"),

  listSecurityEvents: (params?: { limit?: number }) =>
    api.get("/internal/uacp/security", { params }),
};
