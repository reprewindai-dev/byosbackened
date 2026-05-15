import { api, noRoute } from "@/lib/api";

export const routingService = {
  // ─── Routing ─────────────────────────────────────────────
  /** GET /routing/rules */
  listRules: () => api.get("/routing/rules"),

  /** POST /routing/rules */
  createRule: (body: Record<string, unknown>) => api.post("/routing/rules", body),

  /** No route found: PATCH /routing/rules/{rule_id} */
  updateRule: (rule_id: string, body: Record<string, unknown>) =>
    noRoute(`/routing/rules/${rule_id}`, body),

  /** No route found: DELETE /routing/rules/{rule_id} */
  deleteRule: (rule_id: string) => noRoute(`/routing/rules/${rule_id}`),

  /** POST /routing/test */
  testRouting: (body: { input: Record<string, unknown> }) =>
    api.post("/routing/test", body),

  // ─── Search ──────────────────────────────────────────────
  /** POST /search */
  search: (params: { query: string; num_results?: number }) =>
    api.post("/search", { query: params.query, num_results: params.num_results ?? 10 }),

  /** GET /routing/providers */
  listProviders: () => api.get("/routing/providers"),

  /** No route found: PUT /routing/providers/{provider_id} */
  updateProvider: (provider_id: string, body: Record<string, unknown>) =>
    noRoute(`/routing/providers/${provider_id}`, body),

  // ─── Suggestions ─────────────────────────────────────────
  /** GET /suggestions */
  getSuggestions: (params?: { context?: string; limit?: number }) =>
    api.get("/suggestions", { params }),

  // ─── Explainability ──────────────────────────────────────
  /** POST /explain/cost */
  explain: (body: { predicted_cost: number; input_tokens: number; provider: string }) =>
    api.post("/explain/cost", body),

  /** POST /explain/routing */
  getExplanation: (body: { selected_provider: string; alternatives: Array<unknown>; constraints: Record<string, unknown> }) =>
    api.post("/explain/routing", body),

  // ─── Autonomous ──────────────────────────────────────────
  /** No route found: POST /autonomous/run */
  runAutonomousTask: (body: { task: string; context?: Record<string, unknown>; model?: string }) =>
    noRoute("/autonomous/run", body),

  /** No route found: GET /autonomous/tasks */
  listAutonomousTasks: (params?: { status?: string; page?: number }) =>
    noRoute("/autonomous/tasks", params),

  /** No route found: DELETE /autonomous/tasks/{task_id} */
  cancelAutonomousTask: (task_id: string) =>
    noRoute(`/autonomous/tasks/${task_id}`),
};
