import { api, noRoute } from "@/lib/api";

export const supportService = {
  // ─── Support Bot ─────────────────────────────────────────
  /** POST /support/chat */
  chat: (body: { message: string; session_id?: string; context?: Record<string, unknown> }) =>
    api.post("/support/chat", body),

  /** No route found: GET /support/sessions */
  listSessions: (params?: { page?: number; limit?: number }) =>
    noRoute("/support/sessions", params),

  /** No route found: GET /support/sessions/{session_id} */
  getSession: (session_id: string) =>
    noRoute(`/support/sessions/${session_id}`),

  /** No route found: POST /support/sessions/{session_id}/close */
  closeSession: (session_id: string) =>
    noRoute(`/support/sessions/${session_id}/close`),

  /** No route found: POST /support/tickets */
  createTicket: (body: { subject: string; description: string; priority?: "low" | "medium" | "high" }) =>
    noRoute("/support/tickets", body),

  /** No route found: GET /support/tickets */
  listTickets: (params?: { status?: string; page?: number; limit?: number }) =>
    noRoute("/support/tickets", params),

  /** No route found: GET /support/tickets/{ticket_id} */
  getTicket: (ticket_id: string) =>
    noRoute(`/support/tickets/${ticket_id}`),

  /** No route found: PATCH /support/tickets/{ticket_id} */
  updateTicket: (ticket_id: string, body: Record<string, unknown>) =>
    noRoute(`/support/tickets/${ticket_id}`, body),

  // ─── Plugins ─────────────────────────────────────────────
  /** GET /plugins */
  listPlugins: (params?: { category?: string; installed?: boolean }) =>
    api.get("/plugins", { params }),

  /** GET /plugins/available */
  listAvailablePlugins: () => api.get("/plugins/available"),

  /** POST /plugins/{plugin_id}/install */
  installPlugin: (plugin_id: string) =>
    api.post(`/plugins/${plugin_id}/install`),

  /** DELETE /plugins/{plugin_id}/uninstall */
  uninstallPlugin: (plugin_id: string) =>
    api.delete(`/plugins/${plugin_id}/uninstall`),

  /** GET /plugins/{plugin_id}/docs */
  getPluginConfig: (plugin_id: string) =>
    api.get(`/plugins/${plugin_id}/docs`),

  /** No route found: PATCH /plugins/{plugin_id}/config */
  updatePluginConfig: (plugin_id: string, body: Record<string, unknown>) =>
    noRoute(`/plugins/${plugin_id}/config`, body),
};
