/**
 * Compliance & Audit Service
 * Maps to:
 *   backend/apps/api/routers/audit.py
 *   backend/apps/api/routers/compliance.py
 *   backend/apps/api/routers/privacy.py
 *
 * Competitive advantage: Cryptographically verifiable, immutable audit trail.
 * Source claim: Audit Trail is part of the killer feature.
 *
 * UI rule: Never show "compliant" with no evidence.
 * Show: "Evidence check passed" / "Evidence gap detected" / "Audit hash verified".
 */
import { api, noRoute } from "@/lib/api";

export interface AuditLogEntry {
  id: string;
  actor: string;
  action: string;
  resource?: string;
  provider?: string;
  model?: string;
  cost?: string;
  hash: string;
  hash_prefix: string;
  verified: boolean;
  created_at: string;
  context?: Record<string, unknown>;
}

export interface AuditVerifyResult {
  id: string;
  verified: boolean;
  hash_match: boolean;
  tamper_detected: boolean;
  verified_at: string;
}

export interface ComplianceEvidenceBundle {
  id: string;
  type: string;
  period_from: string;
  period_to: string;
  audit_entry_count: number;
  passed_checks: string[];
  failed_checks: string[];
  generated_at: string;
  download_url?: string;
}

export const complianceService = {
  // ─── Audit Logs ───────────────────────────────────────────────────────────

  /**
   * GET /api/v1/audit/logs
   * Monitoring page: show all audit rows with hash prefix and verify button.
   */
  getLogs: (params?: {
    from?: string;
    to?: string;
    actor?: string;
    action?: string;
    provider?: string;
    page?: number;
    limit?: number;
  }) => api.get<AuditLogEntry[]>("/audit/logs", { params }),

  /**
   * No route found: GET /api/v1/audit/logs/{log_id}
   */
  getLog: (log_id: string) => noRoute(`/audit/logs/${log_id}`),

  /**
   * GET /api/v1/audit/verify/{id}
   * Verify button in Monitoring UI.
   * Show: "Evidence check passed" / "Audit hash verified" / "Tamper detected".
   */
  verifyLog: (log_id: string) =>
    api.get<AuditVerifyResult>(`/audit/verify/${log_id}`),

  // ─── Compliance Evidence ──────────────────────────────────────────────────

  /**
   * No route found: GET /api/v1/compliance/status
   * Compliance Center overview.
   */
  getStatus: () => noRoute("/compliance/status"),

  /**
   * POST /api/v1/compliance/check
   */
  runCheck: (body: Record<string, unknown>) =>
    api.post("/compliance/check", body),

  /**
   * No route found: GET /api/v1/compliance/reports
   */
  listReports: () => noRoute("/compliance/reports"),

  /**
   * No route found: GET /api/v1/compliance/evidence
   * Pull evidence bundle for a period.
   */
  getEvidence: (params?: { from?: string; to?: string; type?: string }) =>
    noRoute("/compliance/evidence", params),

  /**
   * No route found: POST /api/v1/compliance/evidence/export
   * Generate and download evidence package.
   * Use for: enterprise proof-of-compliance, HIPAA/GDPR audit packages.
   */
  exportEvidence: (body: { type: string; from: string; to: string; format?: "pdf" | "json" }) =>
    noRoute("/compliance/evidence/export", body),

  /**
   * POST /api/v1/compliance/report
   */
  generateReport: (body: { type: string; from?: string; to?: string }) =>
    api.post("/compliance/report", body),

  // ─── Privacy (PII + GDPR) ─────────────────────────────────────────────────

  /**
   * No route found: GET /api/v1/privacy/settings
   */
  getPrivacySettings: () => noRoute("/privacy/settings"),

  /**
   * No route found: PATCH /api/v1/privacy/settings
   * Powers: auto-redact toggle in Playground.
   */
  updatePrivacySettings: (body: {
    auto_redact_pii?: boolean;
    data_residency?: string;
    retention_days?: number;
  }) => noRoute("/privacy/settings", body),

  /**
   * POST /api/v1/privacy/export or POST /api/v1/privacy/delete
   * GDPR export / delete request.
   */
  submitDataRequest: (body: { type: "export" | "delete"; user_id?: string }) =>
    api.post(body.type === "delete" ? "/privacy/delete" : "/privacy/export", body),

  /**
   * No route found: GET /api/v1/privacy/data-requests
   */
  listDataRequests: (params?: { status?: string }) =>
    noRoute("/privacy/data-requests", params),
};
