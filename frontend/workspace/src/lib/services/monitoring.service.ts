import { api, sseUrl } from "@/lib/api";

export const monitoringService = {
  // ─── Platform Pulse ──────────────────────────────────────
  /** GET /platform-pulse/health */
  getPlatformHealth: () => api.get("/platform-pulse/health"),

  /** GET /platform-pulse/metrics */
  getPlatformMetrics: (params?: { from?: string; to?: string }) =>
    api.get("/platform-pulse/metrics", { params }),

  /** GET /platform-pulse/providers */
  getProviderStatus: () => api.get("/platform-pulse/providers"),

  /** SSE /platform-pulse/stream */
  platformPulseStreamUrl: () => sseUrl("/platform-pulse/stream"),

  // ─── Monitoring Suite ────────────────────────────────────
  /** GET /monitoring/alerts */
  listAlerts: (params?: { status?: string; severity?: string; page?: number }) =>
    api.get("/monitoring/alerts", { params }),

  /** PATCH /monitoring/alerts/{alert_id}/acknowledge */
  acknowledgeAlert: (alert_id: string) =>
    api.patch(`/monitoring/alerts/${alert_id}/acknowledge`),

  /** GET /monitoring/anomalies */
  listAnomalies: (params?: { from?: string; to?: string }) =>
    api.get("/monitoring/anomalies", { params }),

  /** GET /monitoring/logs */
  getLogs: (params?: { level?: string; from?: string; to?: string; limit?: number }) =>
    api.get("/monitoring/logs", { params }),

  /** GET /monitoring/dashboards */
  listDashboards: () => api.get("/monitoring/dashboards"),

  /** POST /monitoring/dashboards */
  createDashboard: (body: Record<string, unknown>) =>
    api.post("/monitoring/dashboards", body),

  // ─── Locker Monitoring ───────────────────────────────────
  /** GET /locker/monitoring/events */
  getLockerEvents: (params?: { from?: string; to?: string; severity?: string }) =>
    api.get("/locker/monitoring/events", { params }),

  /** GET /locker/monitoring/summary */
  getLockerSummary: () => api.get("/locker/monitoring/summary"),

  // ─── Audit ───────────────────────────────────────────────
  /** GET /audit/logs */
  getAuditLogs: (params?: { from?: string; to?: string; actor?: string; action?: string; page?: number; limit?: number }) =>
    api.get("/audit/logs", { params }),

  /** GET /audit/logs/{log_id} */
  getAuditLog: (log_id: string) => api.get(`/audit/logs/${log_id}`),

  // ─── Telemetry ───────────────────────────────────────────
  /** POST /telemetry/event */
  sendEvent: (body: { event: string; properties?: Record<string, unknown> }) =>
    api.post("/telemetry/event", body),

  /** GET /telemetry/summary */
  getTelemetrySummary: () => api.get("/telemetry/summary"),

  // ─── Insights ────────────────────────────────────────────
  /** GET /insights */
  getInsights: (params?: { type?: string; from?: string; to?: string }) =>
    api.get("/insights", { params }),

  /** GET /insights/recommendations */
  getRecommendations: () => api.get("/insights/recommendations"),
};
