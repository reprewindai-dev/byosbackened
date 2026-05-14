import { api } from "@/lib/api";

export const authService = {
  /** POST /auth/register */
  register: (body: { email: string; password: string; workspace_name?: string; plan?: string }) =>
    api.post("/auth/register", body),

  /** POST /auth/login */
  login: (body: { email: string; password: string }) =>
    api.post<{ access_token: string; refresh_token: string; expires_in: number; token_type: string }>("/auth/login", body),

  /** POST /auth/refresh */
  refresh: (refresh_token: string) =>
    api.post<{ access_token: string; refresh_token: string; expires_in: number }>("/auth/refresh", { refresh_token }),

  /** POST /auth/logout */
  logout: () => api.post("/auth/logout"),

  /** GET /auth/me */
  me: () => api.get("/auth/me"),

  /** POST /auth/forgot-password */
  forgotPassword: (email: string) => api.post("/auth/forgot-password", { email }),

  /** POST /auth/reset-password */
  resetPassword: (token: string, new_password: string) =>
    api.post("/auth/reset-password", { token, new_password }),

  /** POST /auth/verify-email */
  verifyEmail: (token: string) => api.post("/auth/verify-email", { token }),

  /** GET /auth/github */
  githubOAuth: () => api.get("/auth/github"),

  /** GET /auth/github/callback */
  githubCallback: (code: string, state?: string) =>
    api.get("/auth/github/callback", { params: { code, state } }),

  /** POST /auth/api-keys */
  createApiKey: (body: { name: string; scopes?: string[]; expires_at?: string }) =>
    api.post("/auth/api-keys", body),

  /** GET /auth/api-keys */
  listApiKeys: () => api.get("/auth/api-keys"),

  /** DELETE /auth/api-keys/{key_id} */
  deleteApiKey: (key_id: string) => api.delete(`/auth/api-keys/${key_id}`),
};
