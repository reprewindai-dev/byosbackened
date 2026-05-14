import { api } from "@/lib/api";

export const supportService = {
  // ─── Support Bot ─────────────────────────────────────────
  /** POST /support/chat */
  chat: (body: { message: string; session_id?: string; context?: Record<string, unknown> }) =>
    api.post("/support/chat", body),

  /** GET /support/sessions */
  listSessions: (params?: { page?: number; limit?: number }) =>
    api.get("/support/sessions", { params }),

  /** GET /support/sessions/{session_id} */
  getSession: (session_id: string) =>
    api.get(`/support/sessions/${session_id}`),

  /** POST /support/sessions/{session_id}/close */
  closeSession: (session_id: string) =>
    api.post(`/support/sessions/${session_id}/close`),

  /** POST /support/tickets */
  createTicket: (body: { subject: string; description: string; priority?: "low" | "medium" | "high" }) =>
    api.post("/support/tickets", body),

  /** GET /support/tickets */
  listTickets: (params?: { status?: string; page?: number; limit?: number }) =>
    api.get("/support/tickets", { params }),

  /** GET /support/tickets/{ticket_id} */
  getTicket: (ticket_id: string) =>
    api.get(`/support/tickets/${ticket_id}`),

  /** PATCH /support/tickets/{ticket_id} */
  updateTicket: (ticket_id: string, body: Record<string, unknown>) =>
    api.patch(`/support/tickets/${ticket_id}`, body),

  // ─── Plugins ─────────────────────────────────────────────
  /** GET /plugins */
  listPlugins: (params?: { category?: string; installed?: boolean }) =>
    api.get("/plugins", { params }),

  /** POST /plugins/{plugin_id}/install */
  installPlugin: (plugin_id: string) =>
    api.post(`/plugins/${plugin_id}/install`),

  /** DELETE /plugins/{plugin_id}/install */
  uninstallPlugin: (plugin_id: string) =>
    api.delete(`/plugins/${plugin_id}/install`),

  /** GET /plugins/{plugin_id}/config */
  getPluginConfig: (plugin_id: string) =>
    api.get(`/plugins/${plugin_id}/config`),

  /** PATCH /plugins/{plugin_id}/config */
  updatePluginConfig: (plugin_id: string, body: Record<string, unknown>) =>
    api.patch(`/plugins/${plugin_id}/config`, body),
};
