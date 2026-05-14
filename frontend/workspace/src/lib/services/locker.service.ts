import { api } from "@/lib/api";

export const lockerService = {
  // ─── Locker Users ────────────────────────────────────────
  /** GET /locker/users */
  listUsers: (params?: { page?: number; limit?: number; search?: string }) =>
    api.get("/locker/users", { params }),

  /** POST /locker/users */
  createUser: (body: Record<string, unknown>) =>
    api.post("/locker/users", body),

  /** GET /locker/users/{user_id} */
  getUser: (user_id: string) => api.get(`/locker/users/${user_id}`),

  /** PATCH /locker/users/{user_id} */
  updateUser: (user_id: string, body: Record<string, unknown>) =>
    api.patch(`/locker/users/${user_id}`, body),

  /** DELETE /locker/users/{user_id} */
  deleteUser: (user_id: string) => api.delete(`/locker/users/${user_id}`),

  /** POST /locker/users/{user_id}/grant */
  grantAccess: (user_id: string, body: { resource: string; permission: string }) =>
    api.post(`/locker/users/${user_id}/grant`, body),

  /** POST /locker/users/{user_id}/revoke */
  revokeAccess: (user_id: string, body: { resource: string; permission: string }) =>
    api.post(`/locker/users/${user_id}/revoke`, body),

  // ─── Locker Security (see security.service for more) ─────
  /** GET /locker/security/access-log */
  getAccessLog: (params?: { from?: string; to?: string; user_id?: string }) =>
    api.get("/locker/security/access-log", { params }),

  /** POST /locker/security/mfa/enforce */
  enforceMFA: () => api.post("/locker/security/mfa/enforce"),
};
