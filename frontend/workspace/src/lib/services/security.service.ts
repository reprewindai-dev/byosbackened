import { api } from "@/lib/api";

export const securityService = {
  // ─── Security Suite ──────────────────────────────────────
  /** GET /security/threats */
  listThreats: (params?: { status?: string; severity?: string; page?: number }) =>
    api.get("/security/threats", { params }),

  /** GET /security/threats/{threat_id} */
  getThreat: (threat_id: string) => api.get(`/security/threats/${threat_id}`),

  /** POST /security/threats/{threat_id}/resolve */
  resolveThreat: (threat_id: string, body?: { notes?: string }) =>
    api.post(`/security/threats/${threat_id}/resolve`, body),

  /** GET /security/policies */
  listPolicies: () => api.get("/security/policies"),

  /** POST /security/policies */
  createPolicy: (body: Record<string, unknown>) =>
    api.post("/security/policies", body),

  /** PATCH /security/policies/{policy_id} */
  updatePolicy: (policy_id: string, body: Record<string, unknown>) =>
    api.patch(`/security/policies/${policy_id}`, body),

  /** DELETE /security/policies/{policy_id} */
  deletePolicy: (policy_id: string) =>
    api.delete(`/security/policies/${policy_id}`),

  /** GET /security/score */
  getSecurityScore: () => api.get("/security/score"),

  /** GET /security/scan */
  runScan: () => api.post("/security/scan"),

  // ─── Content Safety ──────────────────────────────────────
  /** POST /content-safety/check */
  checkContent: (body: { content: string; categories?: string[] }) =>
    api.post("/content-safety/check", body),

  /** GET /content-safety/rules */
  listSafetyRules: () => api.get("/content-safety/rules"),

  /** POST /content-safety/rules */
  createSafetyRule: (body: Record<string, unknown>) =>
    api.post("/content-safety/rules", body),

  /** PATCH /content-safety/rules/{rule_id} */
  updateSafetyRule: (rule_id: string, body: Record<string, unknown>) =>
    api.patch(`/content-safety/rules/${rule_id}`, body),

  /** DELETE /content-safety/rules/{rule_id} */
  deleteSafetyRule: (rule_id: string) =>
    api.delete(`/content-safety/rules/${rule_id}`),

  // ─── Locker Security ─────────────────────────────────────
  /** GET /locker/security/status */
  getLockerStatus: () => api.get("/locker/security/status"),

  /** GET /locker/security/incidents */
  listLockerIncidents: (params?: { from?: string; to?: string }) =>
    api.get("/locker/security/incidents", { params }),

  /** POST /locker/security/lockdown */
  triggerLockdown: (body?: { reason?: string }) =>
    api.post("/locker/security/lockdown", body),

  /** POST /locker/security/unlock */
  releaseLockdown: () => api.post("/locker/security/unlock"),

  // ─── Compliance ──────────────────────────────────────────
  /** GET /compliance/status */
  getComplianceStatus: () => api.get("/compliance/status"),

  /** GET /compliance/reports */
  listComplianceReports: () => api.get("/compliance/reports"),

  /** POST /compliance/reports/generate */
  generateReport: (body: { type: string; from?: string; to?: string }) =>
    api.post("/compliance/reports/generate", body),

  // ─── Privacy ─────────────────────────────────────────────
  /** GET /privacy/settings */
  getPrivacySettings: () => api.get("/privacy/settings"),

  /** PATCH /privacy/settings */
  updatePrivacySettings: (body: Record<string, unknown>) =>
    api.patch("/privacy/settings", body),

  /** POST /privacy/data-request */
  submitDataRequest: (body: { type: "export" | "delete"; user_id?: string }) =>
    api.post("/privacy/data-request", body),

  /** GET /privacy/data-requests */
  listDataRequests: (params?: { status?: string }) =>
    api.get("/privacy/data-requests", { params }),
};
