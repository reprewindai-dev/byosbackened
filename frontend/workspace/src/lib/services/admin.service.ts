import { api, noRoute } from "@/lib/api";

export const adminService = {
  // ─── Users ───────────────────────────────────────────────
  /** GET /admin/users */
  listUsers: (params?: { page?: number; limit?: number; search?: string }) =>
    api.get("/admin/users", { params }),

  /** GET /admin/users/{user_id} */
  getUser: (user_id: string) => api.get(`/admin/users/${user_id}`),

  /** PATCH /admin/users/{user_id} */
  updateUser: (user_id: string, body: Record<string, unknown>) =>
    api.patch(`/admin/users/${user_id}`, body),

  /** DELETE /admin/users/{user_id} */
  deleteUser: (user_id: string) => api.delete(`/admin/users/${user_id}`),

  /** No route found: POST /admin/users/{user_id}/suspend */
  suspendUser: (user_id: string) => noRoute(`/admin/users/${user_id}/suspend`),

  /** No route found: POST /admin/users/{user_id}/unsuspend */
  unsuspendUser: (user_id: string) => noRoute(`/admin/users/${user_id}/unsuspend`),

  // ─── Workspaces ──────────────────────────────────────────
  /** GET /admin/workspaces */
  listWorkspaces: (params?: { page?: number; limit?: number }) =>
    api.get("/admin/workspaces", { params }),

  /** GET /admin/workspaces/{workspace_id} */
  getWorkspace: (workspace_id: string) =>
    api.get(`/admin/workspaces/${workspace_id}`),

  /** PATCH /admin/workspaces/{workspace_id} */
  updateWorkspace: (workspace_id: string, body: Record<string, unknown>) =>
    api.patch(`/admin/workspaces/${workspace_id}`, body),

  // ─── Analytics & Stats ───────────────────────────────────
  /** GET /admin/stats */
  getStats: () => api.get("/admin/stats"),

  /** GET /admin/financials */
  getRevenueStats: (params?: { from?: string; to?: string }) =>
    api.get("/admin/financials", { params }),

  /** GET /admin/live-ops */
  getUsageStats: (params?: { from?: string; to?: string }) =>
    api.get("/admin/live-ops", { params }),

  /** POST /admin/impersonate/{user_id} */
  impersonateUser: (user_id: string) => api.post(`/admin/impersonate/${user_id}`),

  // ─── Feature Flags ───────────────────────────────────────
  /** No route found: GET /admin/flags */
  listFlags: () => noRoute("/admin/flags"),

  /** No route found: PATCH /admin/flags/{flag} */
  setFlag: (flag: string, enabled: boolean) =>
    noRoute(`/admin/flags/${flag}`, enabled),

  // ─── Kill Switch ─────────────────────────────────────────
  /** GET /kill-switch/status */
  getKillSwitch: () => api.get("/kill-switch/status"),

  /** POST /kill-switch/activate */
  engageKillSwitch: (body: { reason: string; scope?: string }) =>
    api.post("/kill-switch/activate", body),

  /** POST /kill-switch/deactivate */
  disengageKillSwitch: () => api.post("/kill-switch/deactivate"),
};
