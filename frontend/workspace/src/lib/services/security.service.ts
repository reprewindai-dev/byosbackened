import { api, noRoute } from "@/lib/api";

export const securityService = {
  // ─── Security Suite ──────────────────────────────────────
  /** GET /security/threats */
  listThreats: (params?: { status?: string; severity?: string; page?: number }) =>
    api.get("/security/threats", { params }),

  /** GET /security/events/{threat_id} */
  getThreat: (threat_id: string) => api.get(`/security/events/${threat_id}`),

  /** PUT /security/events/{threat_id}/resolve */
  resolveThreat: (threat_id: string, body?: { notes?: string }) =>
    api.put(`/security/events/${threat_id}/resolve`, body),

  /** GET /security/zero-trust/policies */
  listPolicies: () => api.get("/security/zero-trust/policies"),

  /** No route found: POST /security/zero-trust/policies */
  createPolicy: (body: Record<string, unknown>) =>
    noRoute("/security/zero-trust/policies", body),

  /** No route found: PATCH /security/zero-trust/policies/{policy_id} */
  updatePolicy: (policy_id: string, body: Record<string, unknown>) =>
    noRoute(`/security/zero-trust/policies/${policy_id}`, body),

  /** No route found: DELETE /security/zero-trust/policies/{policy_id} */
  deletePolicy: (policy_id: string) =>
    noRoute(`/security/zero-trust/policies/${policy_id}`),

  /** GET /security/stats */
  getSecurityScore: () => api.get("/security/stats"),

  /** No route found: POST /security/scan */
  runScan: () => noRoute("/security/scan"),

  // ─── Content Safety ──────────────────────────────────────
  /** POST /content-safety/test */
  checkContent: (body: { content: string; categories?: string[] }) =>
    api.post("/content-safety/test", body),

  /** No route found: GET /content-safety/rules */
  listSafetyRules: () => noRoute("/content-safety/rules"),

  /** No route found: POST /content-safety/rules */
  createSafetyRule: (body: Record<string, unknown>) =>
    noRoute("/content-safety/rules", body),

  /** No route found: PATCH /content-safety/rules/{rule_id} */
  updateSafetyRule: (rule_id: string, body: Record<string, unknown>) =>
    noRoute(`/content-safety/rules/${rule_id}`, body),

  /** No route found: DELETE /content-safety/rules/{rule_id} */
  deleteSafetyRule: (rule_id: string) =>
    noRoute(`/content-safety/rules/${rule_id}`),

  // ─── Locker Security ─────────────────────────────────────
  /** GET /security/locker */
  getLockerStatus: () => api.get("/security/locker"),

  /** GET /security/threats */
  listLockerIncidents: (params?: { from?: string; to?: string }) =>
    api.get("/security/threats", { params }),

  /** No route found: POST /locker/security/lockdown */
  triggerLockdown: (body?: { reason?: string }) =>
    noRoute("/locker/security/lockdown", body),

  /** No route found: POST /locker/security/unlock */
  releaseLockdown: () => noRoute("/locker/security/unlock"),

  // ─── Compliance ──────────────────────────────────────────
  /** No route found: GET /compliance/status */
  getComplianceStatus: () => noRoute("/compliance/status"),

  /** No route found: GET /compliance/reports */
  listComplianceReports: () => noRoute("/compliance/reports"),

  /** POST /compliance/report */
  generateReport: (body: { type: string; from?: string; to?: string }) =>
    api.post("/compliance/report", body),

  // ─── Privacy ─────────────────────────────────────────────
  /** No route found: GET /privacy/settings */
  getPrivacySettings: () => noRoute("/privacy/settings"),

  /** No route found: PATCH /privacy/settings */
  updatePrivacySettings: (body: Record<string, unknown>) =>
    noRoute("/privacy/settings", body),

  /** POST /privacy/export or POST /privacy/delete */
  submitDataRequest: (body: { type: "export" | "delete"; user_id?: string }) =>
    api.post(body.type === "delete" ? "/privacy/delete" : "/privacy/export", body),

  /** No route found: GET /privacy/data-requests */
  listDataRequests: (params?: { status?: string }) =>
    noRoute("/privacy/data-requests", params),
};
