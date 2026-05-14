import { api, sseUrl } from "@/lib/api";

export const aiService = {
  /** POST /ai/chat */
  chat: (body: {
    messages: { role: string; content: string }[];
    model?: string;
    provider?: string;
    stream?: boolean;
    workspace_id?: string;
    temperature?: number;
    max_tokens?: number;
  }) => api.post("/ai/chat", body),

  /** SSE /ai/chat/stream - returns a URL for EventSource */
  chatStreamUrl: (params?: Record<string, string | number | boolean>) =>
    sseUrl("/ai/chat/stream", params),

  /** POST /ai/complete */
  complete: (body: { prompt: string; model?: string; provider?: string }) =>
    api.post("/ai/complete", body),

  /** POST /ai/embed */
  embed: (body: { input: string | string[]; model?: string; provider?: string }) =>
    api.post("/ai/embed", body),

  /** GET /ai/models */
  listModels: (params?: { provider?: string }) =>
    api.get("/ai/models", { params }),

  /** GET /ai/providers */
  listProviders: () => api.get("/ai/providers"),

  /** POST /ai/route */
  routeRequest: (body: Record<string, unknown>) => api.post("/ai/route", body),

  /** POST /ai/summarize */
  summarize: (body: { text: string; max_length?: number; model?: string }) =>
    api.post("/ai/summarize", body),

  /** POST /ai/classify */
  classify: (body: { text: string; labels: string[]; model?: string }) =>
    api.post("/ai/classify", body),

  /** POST /ai/translate */
  translate: (body: { text: string; target_language: string; source_language?: string }) =>
    api.post("/ai/translate", body),
};
