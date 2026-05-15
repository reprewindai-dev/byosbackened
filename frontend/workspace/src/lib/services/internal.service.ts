import { api } from "@/lib/api";

/**
 * Internal operator + internal UACP bridge routes.
 * These are superuser/automation-key only and are customer-safe wrappers.
 */
export const internalService = {
  // ---------------------------------------------------------
  // Operators
  // ---------------------------------------------------------
  operatorOverview: () => api.get("/internal/operators/overview"),

  operatorDigest: () => api.get("/internal/operators/digest"),

  runOperatorWatch: () => api.post("/internal/operators/watch"),

  queueQstashJob: (body: Record<string, unknown>) =>
    api.post("/internal/operators/qstash/enqueue", body),

  triggerMaintenanceWorkflow: (body: Record<string, unknown>) =>
    api.post("/internal/operators/workflows/uacp-maintenance/trigger", body),

  listWorkers: (params?: { limit?: number }) => api.get("/internal/operators/workers", { params }),

  getWorkerRegistry: () => api.get("/internal/operators/registry"),

  getWorker: (workerId: string) => api.get(`/internal/operators/workers/${encodeURIComponent(workerId)}`),

  workerHeartbeat: (workerId: string, body: Record<string, unknown>) =>
    api.post(`/internal/operators/workers/${encodeURIComponent(workerId)}/heartbeat`, body),

  createWorkerRun: (body: Record<string, unknown>) =>
    api.post("/internal/operators/runs", body),

  listWorkerRuns: (params?: { limit?: number }) =>
    api.get("/internal/operators/runs", { params }),

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
