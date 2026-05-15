import { api } from "@/lib/api";

export const monitoringService = {
  /** GET /monitoring/health */
  getHealth: () => api.get("/monitoring/health"),

  /** GET /monitoring/metrics */
  getMetrics: (params?: { start_date?: string; end_date?: string }) =>
    api.get("/monitoring/metrics", { params }),

  /** GET /monitoring/alerts */
  listAlerts: (params?: { status?: string; severity?: string; page?: number }) =>
    api.get("/monitoring/alerts", { params }),

  /** POST /monitoring/alerts */
  createAlert: (body: Record<string, unknown>) => api.post("/monitoring/alerts", body),

  /** GET /monitoring/logs */
  getLogs: (params?: { level?: string; from?: string; to?: string; limit?: number }) =>
    api.get("/monitoring/logs", { params }),

  /** GET /monitoring/overview */
  getOverview: () => api.get("/monitoring/overview"),
};
