import { api, noRoute } from "@/lib/api";

export const lockerService = {
  // ─── Locker Users ────────────────────────────────────────
  /** GET /locker/users/ */
  listUsers: (params?: { page?: number; limit?: number; search?: string }) =>
    api.get("/locker/users/", { params }),

  /** POST /locker/users/ */
  createUser: (body: Record<string, unknown>) =>
    api.post("/locker/users/", body),

  /** GET /locker/users/{user_id} */
  getUser: (user_id: string) => api.get(`/locker/users/${user_id}`),

  /** PUT /locker/users/{user_id} */
  updateUser: (user_id: string, body: Record<string, unknown>) =>
    api.put(`/locker/users/${user_id}`, body),

  /** DELETE /locker/users/{user_id} */
  deleteUser: (user_id: string) => api.delete(`/locker/users/${user_id}`),

  /** No route found: POST /locker/users/{user_id}/grant */
  grantAccess: (user_id: string, body: { resource: string; permission: string }) =>
    noRoute(`/locker/users/${user_id}/grant`, body),

  /** No route found: POST /locker/users/{user_id}/revoke */
  revokeAccess: (user_id: string, body: { resource: string; permission: string }) =>
    noRoute(`/locker/users/${user_id}/revoke`, body),

  // ─── Locker Security (see security.service for more) ─────
  /** No route found: GET /locker/security/access-log */
  getAccessLog: (params?: { from?: string; to?: string; user_id?: string }) =>
    noRoute("/locker/security/access-log", params),

  /** No route found: POST /locker/security/mfa/enforce */
  enforceMFA: () => noRoute("/locker/security/mfa/enforce"),
};
