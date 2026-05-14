import { api } from "@/lib/api";

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

  /** POST /admin/users/{user_id}/suspend */
  suspendUser: (user_id: string) => api.post(`/admin/users/${user_id}/suspend`),

  /** POST /admin/users/{user_id}/unsuspend */
  unsuspendUser: (user_id: string) => api.post(`/admin/users/${user_id}/unsuspend`),

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

  /** GET /admin/stats/revenue */
  getRevenueStats: (params?: { from?: string; to?: string }) =>
    api.get("/admin/stats/revenue", { params }),

  /** GET /admin/stats/usage */
  getUsageStats: (params?: { from?: string; to?: string }) =>
    api.get("/admin/stats/usage", { params }),

  // ─── Feature Flags ───────────────────────────────────────
  /** GET /admin/flags */
  listFlags: () => api.get("/admin/flags"),

  /** PATCH /admin/flags/{flag} */
  setFlag: (flag: string, enabled: boolean) =>
    api.patch(`/admin/flags/${flag}`, { enabled }),

  // ─── Kill Switch ─────────────────────────────────────────
  /** GET /kill-switch */
  getKillSwitch: () => api.get("/kill-switch"),

  /** POST /kill-switch/engage */
  engageKillSwitch: (body: { reason: string; scope?: string }) =>
    api.post("/kill-switch/engage", body),

  /** POST /kill-switch/disengage */
  disengageKillSwitch: () => api.post("/kill-switch/disengage"),
};
