export interface VeklomClientOptions {
  apiKey?: string;
  accessToken?: string;
  baseUrl?: string;
  timeout?: number;
}

export interface CompletionRequest {
  prompt: string;
  model?: string;
  maxTokens?: number;
  temperature?: number;
  workspaceId?: string;
}

export interface CompleteResponse {
  text: string;
  auditLogId?: string;
  provider?: 'ollama' | 'groq' | string;
  model?: string;
  tokensUsed?: number;
  requestedModel?: string;
}
