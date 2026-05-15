import { api, apiRoot, noRoute } from "@/lib/api";

export const workspaceService = {
  /** GET /workspace/ */
  get: () => api.get("/workspace"),

  /** PATCH /workspace/profile */
  update: (body: Record<string, unknown>) => api.patch("/workspace/profile", body),

  /** GET /workspace/members */
  listMembers: () => api.get("/workspace/members"),

  /** POST /workspace/members/invite */
  inviteMember: (body: { email: string; role?: string }) =>
    api.post("/workspace/members/invite", body),

  /** DELETE /workspace/members/{user_id} */
  removeMember: (user_id: string) => api.delete(`/workspace/members/${user_id}`),

  /** No route found: PATCH /workspace/members/{user_id}/role */
  updateMemberRole: (user_id: string, role: string) =>
    noRoute(`/workspace/members/${user_id}/role`, role),

  /** GET /workspace/usage */
  getUsage: () => api.get("/workspace/usage"),

  /** GET /workspace/overview */
  getSettings: () => api.get("/workspace/overview"),

  /** PATCH /workspace/profile */
  updateSettings: (body: Record<string, unknown>) => api.patch("/workspace/profile", body),

  /** GET /routing/providers (source-of-truth bridge) */
  listProviders: () => api.get("/routing/providers"),

  /** No route found: POST /workspace/providers */
  addProvider: (body: Record<string, unknown>) => noRoute("/workspace/providers", body),

  /** No route found: PATCH /workspace/providers/{provider_id} */
  updateProvider: (provider_id: string, body: Record<string, unknown>) =>
    noRoute(`/workspace/providers/${provider_id}`, body),

  /** No route found: DELETE /workspace/providers/{provider_id} */
  deleteProvider: (provider_id: string) =>
    noRoute(`/workspace/providers/${provider_id}`),

  /** POST /routing/test */
  testProvider: (provider_id: string) =>
    api.post("/routing/test", { provider_id }),

  /** GET /security/locker */
  getLockerConfig: () => api.get("/security/locker"),

  /** GET /status/data (public, no /api/v1 prefix) */
  publicStatus: (workspace_slug: string) =>
    apiRoot.get("/status/data", { params: { workspace_slug } }),
};
