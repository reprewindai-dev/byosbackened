import type { VeklomClientOptions, CompletionRequest, CompleteResponse } from './types';
import { AuthError, RateLimitError, VeklomError } from './exceptions';

const DEFAULT_BASE_URL = 'https://api.veklom.com/api/v1';

export class VeklomClient {
  private readonly baseUrl: string;
  private readonly token: string;
  private readonly timeout: number;

  constructor(options: VeklomClientOptions) {
    if (!options.apiKey && !options.accessToken) {
      throw new Error('Provide either apiKey or accessToken');
    }
    this.token = (options.apiKey ?? options.accessToken)!;
    this.baseUrl = (options.baseUrl ?? DEFAULT_BASE_URL).replace(/\/$/, '');
    this.timeout = options.timeout ?? 30_000;
  }

  private get headers(): Record<string, string> {
    return {
      Authorization: `Bearer ${this.token}`,
      'Content-Type': 'application/json',
      'X-Veklom-SDK': 'js/0.1.0',
    };
  }

  async complete(request: CompletionRequest): Promise<CompleteResponse> {
    const payload = {
      prompt: request.prompt,
      model: request.model,
      max_tokens: request.maxTokens ?? 1024,
      temperature: request.temperature ?? 0.7,
      workspace_id: request.workspaceId,
    };

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeout);

    try {
      const res = await fetch(`${this.baseUrl}/ai/complete`, {
        method: 'POST',
        headers: this.headers,
        body: JSON.stringify(payload),
        signal: controller.signal,
      });

      if (res.status === 401 || res.status === 403) throw new AuthError(`HTTP ${res.status}`);
      if (res.status === 429) throw new RateLimitError('Rate limit exceeded');
      if (!res.ok) throw new VeklomError(`HTTP ${res.status}: ${await res.text()}`);

      const data = await res.json();
      return {
        text: data.text,
        auditLogId: data.audit_log_id,
        provider: data.provider,
        model: data.model,
        tokensUsed: data.tokens_used,
        requestedModel: data.requested_model,
      };
    } finally {
      clearTimeout(timer);
    }
  }
}
