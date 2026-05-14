import { api } from "@/lib/api";

export const routingService = {
  // ─── Routing ─────────────────────────────────────────────
  /** GET /routing/rules */
  listRules: () => api.get("/routing/rules"),

  /** POST /routing/rules */
  createRule: (body: Record<string, unknown>) => api.post("/routing/rules", body),

  /** PATCH /routing/rules/{rule_id} */
  updateRule: (rule_id: string, body: Record<string, unknown>) =>
    api.patch(`/routing/rules/${rule_id}`, body),

  /** DELETE /routing/rules/{rule_id} */
  deleteRule: (rule_id: string) => api.delete(`/routing/rules/${rule_id}`),

  /** POST /routing/test */
  testRouting: (body: { input: Record<string, unknown> }) =>
    api.post("/routing/test", body),

  // ─── Search ──────────────────────────────────────────────
  /** GET /search */
  search: (params: { q: string; type?: string; page?: number; limit?: number }) =>
    api.get("/search", { params }),

  // ─── Suggestions ─────────────────────────────────────────
  /** GET /suggestions */
  getSuggestions: (params?: { context?: string; limit?: number }) =>
    api.get("/suggestions", { params }),

  // ─── Explainability ──────────────────────────────────────
  /** POST /explainability/explain */
  explain: (body: { request_id: string; detail?: "summary" | "full" }) =>
    api.post("/explainability/explain", body),

  /** GET /explainability/{request_id} */
  getExplanation: (request_id: string) =>
    api.get(`/explainability/${request_id}`),

  // ─── Autonomous ──────────────────────────────────────────
  /** POST /autonomous/run */
  runAutonomousTask: (body: { task: string; context?: Record<string, unknown>; model?: string }) =>
    api.post("/autonomous/run", body),

  /** GET /autonomous/tasks */
  listAutonomousTasks: (params?: { status?: string; page?: number }) =>
    api.get("/autonomous/tasks", { params }),

  /** DELETE /autonomous/tasks/{task_id} */
  cancelAutonomousTask: (task_id: string) =>
    api.delete(`/autonomous/tasks/${task_id}`),
};
