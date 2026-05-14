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
import { api } from "@/lib/api";

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
   * GET /api/v1/audit/logs/{log_id}
   */
  getLog: (log_id: string) => api.get<AuditLogEntry>(`/audit/logs/${log_id}`),

  /**
   * GET /api/v1/audit/verify/{id}
   * Verify button in Monitoring UI.
   * Show: "Evidence check passed" / "Audit hash verified" / "Tamper detected".
   */
  verifyLog: (log_id: string) =>
    api.get<AuditVerifyResult>(`/audit/verify/${log_id}`),

  // ─── Compliance Evidence ──────────────────────────────────────────────────

  /**
   * GET /api/v1/compliance/status
   * Compliance Center overview.
   */
  getStatus: () => api.get("/compliance/status"),

  /**
   * GET /api/v1/compliance/reports
   */
  listReports: () => api.get<ComplianceEvidenceBundle[]>("/compliance/reports"),

  /**
   * GET /api/v1/compliance/evidence
   * Pull evidence bundle for a period.
   */
  getEvidence: (params?: { from?: string; to?: string; type?: string }) =>
    api.get("/compliance/evidence", { params }),

  /**
   * POST /api/v1/compliance/evidence/export
   * Generate and download evidence package.
   * Use for: enterprise proof-of-compliance, HIPAA/GDPR audit packages.
   */
  exportEvidence: (body: { type: string; from: string; to: string; format?: "pdf" | "json" }) =>
    api.post("/compliance/evidence/export", body, { responseType: "blob" }),

  /**
   * POST /api/v1/compliance/reports/generate
   */
  generateReport: (body: { type: string; from?: string; to?: string }) =>
    api.post("/compliance/reports/generate", body),

  // ─── Privacy (PII + GDPR) ─────────────────────────────────────────────────

  /**
   * GET /api/v1/privacy/settings
   */
  getPrivacySettings: () => api.get("/privacy/settings"),

  /**
   * PATCH /api/v1/privacy/settings
   * Powers: auto-redact toggle in Playground.
   */
  updatePrivacySettings: (body: {
    auto_redact_pii?: boolean;
    data_residency?: string;
    retention_days?: number;
  }) => api.patch("/privacy/settings", body),

  /**
   * POST /api/v1/privacy/data-request
   * GDPR export / delete request.
   */
  submitDataRequest: (body: { type: "export" | "delete"; user_id?: string }) =>
    api.post("/privacy/data-request", body),

  /**
   * GET /api/v1/privacy/data-requests
   */
  listDataRequests: (params?: { status?: string }) =>
    api.get("/privacy/data-requests", { params }),
};
