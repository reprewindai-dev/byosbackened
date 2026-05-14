import { api } from "@/lib/api";

export const workspaceService = {
  /** GET /workspace */
  get: () => api.get("/workspace"),

  /** PATCH /workspace */
  update: (body: Record<string, unknown>) => api.patch("/workspace", body),

  /** GET /workspace/members */
  listMembers: () => api.get("/workspace/members"),

  /** POST /workspace/members/invite */
  inviteMember: (body: { email: string; role?: string }) =>
    api.post("/workspace/members/invite", body),

  /** DELETE /workspace/members/{user_id} */
  removeMember: (user_id: string) => api.delete(`/workspace/members/${user_id}`),

  /** PATCH /workspace/members/{user_id}/role */
  updateMemberRole: (user_id: string, role: string) =>
    api.patch(`/workspace/members/${user_id}/role`, { role }),

  /** GET /workspace/usage */
  getUsage: () => api.get("/workspace/usage"),

  /** GET /workspace/settings */
  getSettings: () => api.get("/workspace/settings"),

  /** PATCH /workspace/settings */
  updateSettings: (body: Record<string, unknown>) => api.patch("/workspace/settings", body),

  /** GET /workspace/providers */
  listProviders: () => api.get("/workspace/providers"),

  /** POST /workspace/providers */
  addProvider: (body: Record<string, unknown>) => api.post("/workspace/providers", body),

  /** PATCH /workspace/providers/{provider_id} */
  updateProvider: (provider_id: string, body: Record<string, unknown>) =>
    api.patch(`/workspace/providers/${provider_id}`, body),

  /** DELETE /workspace/providers/{provider_id} */
  deleteProvider: (provider_id: string) =>
    api.delete(`/workspace/providers/${provider_id}`),

  /** POST /workspace/providers/{provider_id}/test */
  testProvider: (provider_id: string) =>
    api.post(`/workspace/providers/${provider_id}/test`),

  /** GET /workspace/locker */
  getLockerConfig: () => api.get("/workspace/locker"),

  /** GET /workspace/status (public, no prefix) */
  publicStatus: (workspace_slug: string) =>
    api.get(`/public/workspace/${workspace_slug}/status`),
};
