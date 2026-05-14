import { api } from "@/lib/api";

/**
 * Internal operator routes — only callable by super-admins/operators.
 * These wrap /internal/operators and /internal/uacp endpoints.
 */
export const internalService = {
  // ─── Operators ───────────────────────────────────────────
  /** GET /internal/operators */
  listOperators: (params?: { page?: number; limit?: number }) =>
    api.get("/internal/operators", { params }),

  /** POST /internal/operators */
  createOperator: (body: Record<string, unknown>) =>
    api.post("/internal/operators", body),

  /** GET /internal/operators/{operator_id} */
  getOperator: (operator_id: string) =>
    api.get(`/internal/operators/${operator_id}`),

  /** PATCH /internal/operators/{operator_id} */
  updateOperator: (operator_id: string, body: Record<string, unknown>) =>
    api.patch(`/internal/operators/${operator_id}`, body),

  /** DELETE /internal/operators/{operator_id} */
  deleteOperator: (operator_id: string) =>
    api.delete(`/internal/operators/${operator_id}`),

  /** POST /internal/operators/{operator_id}/suspend */
  suspendOperator: (operator_id: string) =>
    api.post(`/internal/operators/${operator_id}/suspend`),

  // ─── UACP (Universal AI Control Plane) ───────────────────
  /** GET /internal/uacp/status */
  getUACPStatus: () => api.get("/internal/uacp/status"),

  /** GET /internal/uacp/nodes */
  listUACPNodes: () => api.get("/internal/uacp/nodes"),

  /** POST /internal/uacp/nodes */
  addUACPNode: (body: Record<string, unknown>) =>
    api.post("/internal/uacp/nodes", body),

  /** DELETE /internal/uacp/nodes/{node_id} */
  removeUACPNode: (node_id: string) =>
    api.delete(`/internal/uacp/nodes/${node_id}`),

  /** POST /internal/uacp/sync */
  syncUACP: () => api.post("/internal/uacp/sync"),

  /** GET /internal/uacp/versions */
  listUACPVersions: () => api.get("/internal/uacp/versions"),

  /** POST /internal/uacp/upgrade */
  upgradeUACP: (body: { target_version: string }) =>
    api.post("/internal/uacp/upgrade", body),
};
