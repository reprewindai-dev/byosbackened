/**
 * useAuditVerify
 *
 * Verify an audit log entry cryptographic hash.
 * Used in: Monitoring page audit table, Evidence panel.
 *
 * UI rules:
 *   - Show hash prefix (first 8 chars) next to each log entry
 *   - Show verify button → triggers this hook
 *   - Show: "Evidence check passed" / "Audit hash verified" / "Tamper detected"
 *   - Never show "compliant" with no evidence.
 */
import { useState, useCallback } from "react";
import { complianceService, type AuditVerifyResult } from "@/lib/services/compliance.service";

export interface AuditVerifyState {
  loading: boolean;
  result: AuditVerifyResult | null;
  error: string | null;
  label: string;
  labelVariant: "success" | "error" | "warning" | "idle";
}

export function useAuditVerify() {
  const [state, setState] = useState<AuditVerifyState>({
    loading: false,
    result: null,
    error: null,
    label: "Verify",
    labelVariant: "idle",
  });

  const verify = useCallback(async (log_id: string) => {
    setState((s) => ({ ...s, loading: true, error: null }));

    try {
      const data = await complianceService.verifyLog(log_id);

      let label: string;
      let labelVariant: AuditVerifyState["labelVariant"];

      if (data.tamper_detected) {
        label = "Tamper detected";
        labelVariant = "error";
      } else if (data.verified && data.hash_match) {
        label = "Audit hash verified";
        labelVariant = "success";
      } else if (data.verified) {
        label = "Evidence check passed";
        labelVariant = "success";
      } else {
        label = "Evidence gap detected";
        labelVariant = "warning";
      }

      setState({ loading: false, result: data, error: null, label, labelVariant });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Verification failed";
      setState({
        loading: false,
        result: null,
        error: msg,
        label: "Verification failed",
        labelVariant: "error",
      });
    }
  }, []);

  return { verify, ...state };
}
