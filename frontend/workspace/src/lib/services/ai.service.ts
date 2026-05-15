import { api, apiRoot, noRoute } from "@/lib/api";

export const aiService = {
  /** No route found: POST /ai/chat */
  chat: (body: {
    messages: { role: string; content: string }[];
    model?: string;
    provider?: string;
    stream?: boolean;
    workspace_id?: string;
    temperature?: number;
    max_tokens?: number;
  }) => noRoute("/ai/chat", body),

  /** No route found: SSE /ai/chat/stream */
  chatStreamUrl: (params?: Record<string, string | number | boolean>) =>
    (() => {
      void params;
      throw new Error("No route found: /ai/chat/stream");
    })(),

  /** POST /ai/complete */
  complete: (body: { prompt: string; model?: string; provider?: string }) =>
    api.post("/ai/complete", body),

  /** POST /ai/exec */
  exec: (body: { prompt: string; model?: string; provider?: string; stream?: boolean; workspace_id?: string }) =>
    api.post("/ai/exec", body),

  /** POST /v1/exec */
  execV1: (body: { prompt: string; model?: string; provider?: string; stream?: boolean; workspace_id?: string }) =>
    apiRoot.post("/v1/exec", body),

  /** No route found: POST /ai/embed */
  embed: (body: { input: string | string[]; model?: string; provider?: string }) =>
    noRoute("/ai/embed", body),

  /** GET /workspace/models */
  listModels: (params?: { provider?: string }) =>
    api.get("/workspace/models", { params }),

  /** GET /routing/providers */
  listProviders: () => api.get("/routing/providers"),

  /** POST /routing/test */
  routeRequest: (body: Record<string, unknown>) => api.post("/routing/test", body),

  /** GET /ai/conversation/{id} */
  getConversation: (id: string) => noRoute(`/ai/conversation/${id}`),

  /** POST /ai/conversation/{id} */
  deleteConversation: (id: string) => noRoute(`/ai/conversation/${id}`),

  /** POST /ai/stream */
  stream: (body: Record<string, unknown>) => noRoute("/ai/stream", body),

  /** No route found: POST /ai/summarize */
  summarize: (body: { text: string; max_length?: number; model?: string }) =>
    noRoute("/ai/summarize", body),

  /** No route found: POST /ai/classify */
  classify: (body: { text: string; labels: string[]; model?: string }) =>
    noRoute("/ai/classify", body),

  /** No route found: POST /ai/translate */
  translate: (body: { text: string; target_language: string; source_language?: string }) =>
    noRoute("/ai/translate", body),
};
