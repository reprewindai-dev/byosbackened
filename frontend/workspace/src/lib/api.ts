/**
 * Veklom API Client — Source of Truth
 * Generated from backend/apps/api/routers/* (43 routers)
 * All calls resolve against window.__VEKLOM_API_BASE__ → https://api.veklom.com
 *
 * Usage:
 *   import { api } from "@/lib/api";
 *   const health = await api.health.get();
 *   const res = await api.exec.stream({ model, messages });
 */

// ─── Base helpers ─────────────────────────────────────────────────────────────

function base(): string {
  return (
    (typeof window !== "undefined" && (window as any).__VEKLOM_API_BASE__) ||
    "https://api.veklom.com"
  );
}

function token(): string | null {
  try {
    return (
      sessionStorage.getItem("veklom_token") ||
      sessionStorage.getItem("vk_token") ||
      null
    );
  } catch {
    return null;
  }
}

function authHeaders(): Record<string, string> {
  const t = token();
  return {
    "Content-Type": "application/json",
    ...(t ? { Authorization: `Bearer ${t}` } : {}),
  };
}

async function get<T>(
  path: string,
  params?: Record<string, string | number | boolean>
): Promise<T> {
  const url = new URL(`${base()}/api/v1${path}`);
  if (params) {
    Object.entries(params).forEach(([k, v]) =>
      url.searchParams.set(k, String(v))
    );
  }
  const res = await fetch(url.toString(), {
    headers: authHeaders(),
    credentials: "include",
  });
  if (!res.ok) throw new Error(`GET ${path} → ${res.status}`);
  return res.json();
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${base()}/api/v1${path}`, {
    method: "POST",
    headers: authHeaders(),
    credentials: "include",
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`POST ${path} → ${res.status}`);
  return res.json();
}

async function patch<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${base()}/api/v1${path}`, {
    method: "PATCH",
    headers: authHeaders(),
    credentials: "include",
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`PATCH ${path} → ${res.status}`);
  return res.json();
}

async function del<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${base()}/api/v1${path}`, {
    method: "DELETE",
    headers: authHeaders(),
    credentials: "include",
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`DELETE ${path} → ${res.status}`);
  return res.json();
}

// ─── health.py ────────────────────────────────────────────────────────────────
export const health = {
  get: () =>
    get<{ status: string; version: string; uptime_seconds: number }>("/health"),
};

// ─── audit.py ────────────────────────────────────────────────────────────────
export const audit = {
  logs: (p?: { limit?: number; offset?: number; action?: string }) =>
    get<{ logs: any[]; total: number }>("/audit/logs", p as any),
  verify: (id: string) =>
    get<{ id: string; valid: boolean; hash: string }>(`/audit/verify/${id}`),
};

// ─── auth.py ─────────────────────────────────────────────────────────────────
export const auth = {
  login: (email: string, password: string) =>
    post<{ access_token: string; token_type: string; user: any }>("/auth/login", {
      email,
      password,
    }),
  register: (body: {
    email: string;
    password: string;
    name: string;
    company?: string;
  }) => post<{ access_token: string; user: any }>("/auth/register", body),
  me: () =>
    get<{
      id: string;
      email: string;
      name: string;
      role: string;
      plan: string;
    }>("/auth/me"),
  logout: () => post<{ message: string }>("/auth/logout"),
  refresh: () => post<{ access_token: string }>("/auth/refresh"),
  changePassword: (body: {
    current_password: string;
    new_password: string;
  }) => post<{ message: string }>("/auth/change-password", body),
  forgotPassword: (email: string) =>
    post<{ message: string }>("/auth/forgot-password", { email }),
  resetPassword: (body: { token: string; new_password: string }) =>
    post<{ message: string }>("/auth/reset-password", body),
  apiKeys: {
    list: () => get<{ keys: any[] }>("/auth/api-keys"),
    create: (body: {
      name: string;
      scopes?: string[];
      expires_in_days?: number;
    }) => post<{ key: string; id: string; name: string }>("/auth/api-keys", body),
    delete: (id: string) =>
      del<{ message: string }>(`/auth/api-keys/${id}`),
    rotate: (id: string) =>
      post<{ key: string }>(`/auth/api-keys/${id}/rotate`),
  },
  sessions: {
    list: () => get<{ sessions: any[] }>("/auth/sessions"),
    revoke: (sessionId: string) =>
      del<{ message: string }>(`/auth/sessions/${sessionId}`),
    revokeAll: () => del<{ message: string }>("/auth/sessions"),
  },
  mfa: {
    setup: () =>
      post<{ qr_code: string; secret: string }>("/auth/mfa/setup"),
    verify: (code: string) =>
      post<{ message: string }>("/auth/mfa/verify", { code }),
    disable: () => post<{ message: string }>("/auth/mfa/disable"),
  },
};

// ─── exec_router.py ───────────────────────────────────────────────────────────
export const exec = {
  /** SSE streaming inference — caller reads via response.body.getReader() */
  stream: (body: {
    model: string;
    messages: { role: string; content: string }[];
    temperature?: number;
    max_tokens?: number;
    tools?: any[];
    workspace_id?: string;
  }) =>
    fetch(`${base()}/api/v1/exec`, {
      method: "POST",
      headers: authHeaders(),
      credentials: "include",
      body: JSON.stringify({ ...body, stream: true }),
    }),
  /** Non-streaming single completion */
  complete: (body: {
    model: string;
    messages: any[];
    temperature?: number;
    max_tokens?: number;
  }) =>
    post<{ id: string; content: string; usage: any; model: string }>(
      "/exec",
      body
    ),
};

// ─── workspace.py ─────────────────────────────────────────────────────────────
export const workspace = {
  models: {
    list: () => get<{ models: any[] }>("/workspace/models"),
    toggle: (modelId: string, enabled: boolean) =>
      patch<{ model: any }>(`/workspace/models/${modelId}`, { enabled }),
    update: (modelId: string, body: Partial<any>) =>
      patch<{ model: any }>(`/workspace/models/${modelId}`, body),
  },
  settings: {
    get: () => get<Record<string, any>>("/workspace/settings"),
    update: (body: Record<string, any>) =>
      patch<Record<string, any>>("/workspace/settings", body),
  },
  apiKeys: {
    list: () => get<{ keys: any[] }>("/workspace/api-keys"),
  },
  usage: () =>
    get<{ tokens_used: number; requests: number; cost_usd: number }>(
      "/workspace/usage"
    ),
};

// ─── token_wallet.py ──────────────────────────────────────────────────────────
export const wallet = {
  balance: () =>
    get<{ balance: number; currency: string; burn_rate_per_hour: number }>(
      "/wallet/balance"
    ),
  transactions: (p?: { limit?: number; offset?: number }) =>
    get<{ transactions: any[]; total: number }>(
      "/wallet/transactions",
      p as any
    ),
  topupOptions: () => get<{ options: any[] }>("/wallet/topup/options"),
  topupCheckout: (body: { amount: number; payment_method?: string }) =>
    post<{ checkout_url: string; session_id: string }>(
      "/wallet/topup/checkout",
      body
    ),
  topupDirect: (body: { amount: number; credits: number }) =>
    post<{ balance: number; transaction_id: string }>(
      "/wallet/topup/direct",
      body
    ),
};

// ─── billing.py ───────────────────────────────────────────────────────────────
export const billing = {
  invoices: () => get<{ invoices: any[] }>("/billing/invoices"),
  invoice: (id: string) => get<any>(`/billing/invoices/${id}`),
  paymentMethods: {
    list: () => get<{ methods: any[] }>("/billing/payment-methods"),
    add: (body: { token: string; set_default?: boolean }) =>
      post<{ method: any }>("/billing/payment-methods", body),
    delete: (id: string) =>
      del<{ message: string }>(`/billing/payment-methods/${id}`),
    setDefault: (id: string) =>
      post<{ message: string }>(
        `/billing/payment-methods/${id}/default`
      ),
  },
};

// ─── subscriptions.py ─────────────────────────────────────────────────────────
export const subscriptions = {
  current: () =>
    get<{
      plan: string;
      status: string;
      expires_at: string;
      features: any;
    }>("/subscriptions/current"),
  plans: () => get<{ plans: any[] }>("/subscriptions/plans"),
  upgrade: (body: { plan: string; payment_method_id?: string }) =>
    post<{ subscription: any; checkout_url?: string }>(
      "/subscriptions/upgrade",
      body
    ),
  cancel: () => post<{ message: string }>("/subscriptions/cancel"),
  reactivate: () => post<{ message: string }>("/subscriptions/reactivate"),
};

// ─── budget.py ────────────────────────────────────────────────────────────────
export const budget = {
  get: () =>
    get<{ limit: number; current: number; alert_threshold: number }>("/budget"),
  update: (body: { limit?: number; alert_threshold?: number }) =>
    patch<{ budget: any }>("/budget", body),
  alerts: () => get<{ alerts: any[] }>("/budget/alerts"),
};

// ─── cost.py ──────────────────────────────────────────────────────────────────
export const cost = {
  summary: (p?: { period?: string }) =>
    get<{ total: number; by_model: any[]; by_day: any[] }>(
      "/cost/summary",
      p as any
    ),
  breakdown: (p?: { model?: string; from?: string; to?: string }) =>
    get<{ items: any[] }>("/cost/breakdown", p as any),
};

// ─── admin.py ─────────────────────────────────────────────────────────────────
export const admin = {
  users: {
    list: (p?: { limit?: number; offset?: number; search?: string }) =>
      get<{ users: any[]; total: number }>("/admin/users", p as any),
    get: (userId: string) => get<any>(`/admin/users/${userId}`),
    update: (userId: string, body: Partial<any>) =>
      patch<any>(`/admin/users/${userId}`, body),
    delete: (userId: string) =>
      del<{ message: string }>(`/admin/users/${userId}`),
    suspend: (userId: string) =>
      post<{ message: string }>(`/admin/users/${userId}/suspend`),
    unsuspend: (userId: string) =>
      post<{ message: string }>(`/admin/users/${userId}/unsuspend`),
    impersonate: (userId: string) =>
      post<{ access_token: string }>(
        `/admin/users/${userId}/impersonate`
      ),
  },
  stats: () =>
    get<{
      total_users: number;
      active_today: number;
      mrr: number;
      requests_today: number;
    }>("/admin/stats"),
  config: {
    get: () => get<Record<string, any>>("/admin/config"),
    update: (body: Record<string, any>) =>
      patch<Record<string, any>>("/admin/config", body),
  },
};

// ─── marketplace_v1.py ────────────────────────────────────────────────────────
export const marketplace = {
  listings: (p?: {
    limit?: number;
    offset?: number;
    category?: string;
    q?: string;
  }) =>
    get<{ listings: any[]; total: number }>("/marketplace/listings", p as any),
  listing: (id: string) => get<any>(`/marketplace/listings/${id}`),
  create: (body: any) =>
    post<{ listing: any }>("/marketplace/listings", body),
  update: (id: string, body: any) =>
    patch<{ listing: any }>(`/marketplace/listings/${id}`, body),
  delete: (id: string) =>
    del<{ message: string }>(`/marketplace/listings/${id}`),
  publish: (id: string) =>
    post<{ listing: any }>(`/marketplace/listings/${id}/publish`),
  unpublish: (id: string) =>
    post<{ listing: any }>(`/marketplace/listings/${id}/unpublish`),
  purchase: (id: string, body?: { payment_method_id?: string }) =>
    post<{ order: any; download_url?: string }>(
      `/marketplace/listings/${id}/purchase`,
      body
    ),
  search: (q: string, filters?: Record<string, string>) =>
    get<{ results: any[]; total: number }>("/marketplace/search", {
      q,
      ...filters,
    } as any),
  categories: () => get<{ categories: any[] }>("/marketplace/categories"),
  myListings: () => get<{ listings: any[] }>("/marketplace/my-listings"),
  myPurchases: () => get<{ purchases: any[] }>("/marketplace/my-purchases"),
};

// ─── marketplace_automation.py ────────────────────────────────────────────────
export const marketplaceAutomation = {
  list: (p?: { limit?: number; status?: string }) =>
    get<{ automations: any[] }>("/marketplace/automation", p as any),
  get: (id: string) => get<any>(`/marketplace/automation/${id}`),
  create: (body: any) =>
    post<{ automation: any }>("/marketplace/automation", body),
  update: (id: string, body: any) =>
    patch<any>(`/marketplace/automation/${id}`, body),
  delete: (id: string) =>
    del<{ message: string }>(`/marketplace/automation/${id}`),
  trigger: (id: string, input?: any) =>
    post<{ run_id: string; status: string }>(
      `/marketplace/automation/${id}/trigger`,
      input
    ),
  runs: (id: string) =>
    get<{ runs: any[] }>(`/marketplace/automation/${id}/runs`),
};

// ─── monitoring_suite.py ──────────────────────────────────────────────────────
export const monitoring = {
  health: () =>
    get<{ status: string; services: any[]; latency_ms: number }>(
      "/monitoring/health"
    ),
  overview: () =>
    get<{
      requests_today: number;
      error_rate: number;
      avg_latency_ms: number;
      active_models: number;
    }>("/monitoring/overview"),
  services: () => get<{ services: any[] }>("/monitoring/services"),
  metrics: (p?: {
    service?: string;
    from?: string;
    to?: string;
    granularity?: string;
  }) => get<{ metrics: any[] }>("/monitoring/metrics", p as any),
  alerts: {
    list: () => get<{ alerts: any[] }>("/monitoring/alerts"),
    create: (body: {
      name: string;
      condition: string;
      threshold: number;
      channel: string;
    }) => post<{ alert: any }>("/monitoring/alerts", body),
    delete: (id: string) =>
      del<{ message: string }>(`/monitoring/alerts/${id}`),
    acknowledge: (id: string) =>
      post<{ message: string }>(`/monitoring/alerts/${id}/acknowledge`),
  },
};

// ─── platform_pulse.py ────────────────────────────────────────────────────────
export const pulse = {
  snapshot: () =>
    get<{
      nodes: any[];
      throughput: number;
      active_sessions: number;
    }>("/platform/pulse"),
  /** Full SSE stream URL — use with EventSource or fetch+getReader() */
  streamUrl: (): string => `${base()}/api/v1/platform/pulse/stream`,
  history: (p?: { limit?: number }) =>
    get<{ events: any[] }>("/platform/pulse/history", p as any),
};

// ─── pipelines.py + demo_pipeline.py ─────────────────────────────────────────
export const pipelines = {
  list: (p?: { limit?: number; status?: string }) =>
    get<{ pipelines: any[]; total: number }>("/pipelines", p as any),
  get: (id: string) => get<any>(`/pipelines/${id}`),
  create: (body: any) => post<{ pipeline: any }>("/pipelines", body),
  update: (id: string, body: any) => patch<any>(`/pipelines/${id}`, body),
  delete: (id: string) =>
    del<{ message: string }>(`/pipelines/${id}`),
  run: (id: string, input?: any) =>
    post<{ run_id: string; status: string }>(`/pipelines/${id}/run`, input),
  runs: (id: string, p?: { limit?: number }) =>
    get<{ runs: any[] }>(`/pipelines/${id}/runs`, p as any),
  runStatus: (pipelineId: string, runId: string) =>
    get<{ status: string; logs: string[]; output?: any }>(
      `/pipelines/${pipelineId}/runs/${runId}`
    ),
  demo: {
    run: (body?: any) =>
      post<{ run_id: string; steps: any[] }>("/demo/pipeline/run", body),
    status: (runId: string) => get<any>(`/demo/pipeline/status/${runId}`),
  },
};

// ─── deployments.py ───────────────────────────────────────────────────────────
export const deployments = {
  list: (p?: { limit?: number; zone?: string; status?: string }) =>
    get<{ deployments: any[]; total: number }>("/deployments", p as any),
  get: (id: string) => get<any>(`/deployments/${id}`),
  create: (body: {
    model_id: string;
    zone: string;
    replicas?: number;
    config?: any;
  }) => post<{ deployment: any }>("/deployments", body),
  update: (id: string, body: any) => patch<any>(`/deployments/${id}`, body),
  delete: (id: string) =>
    del<{ message: string }>(`/deployments/${id}`),
  scale: (id: string, replicas: number) =>
    post<{ message: string }>(`/deployments/${id}/scale`, { replicas }),
  restart: (id: string) =>
    post<{ message: string }>(`/deployments/${id}/restart`),
  logs: (id: string, p?: { tail?: number }) =>
    get<{ logs: string[] }>(`/deployments/${id}/logs`, p as any),
};

// ─── edge_canary.py ───────────────────────────────────────────────────────────
export const edgeCanary = {
  list: () => get<{ canaries: any[] }>("/edge/canary"),
  create: (body: { deployment_id: string; traffic_pct: number }) =>
    post<{ canary: any }>("/edge/canary", body),
  update: (id: string, traffic_pct: number) =>
    patch<{ canary: any }>(`/edge/canary/${id}`, { traffic_pct }),
  promote: (id: string) =>
    post<{ message: string }>(`/edge/canary/${id}/promote`),
  rollback: (id: string) =>
    post<{ message: string }>(`/edge/canary/${id}/rollback`),
  delete: (id: string) =>
    del<{ message: string }>(`/edge/canary/${id}`),
};

// ─── routing.py ───────────────────────────────────────────────────────────────
export const routing = {
  rules: () => get<{ rules: any[] }>("/routing/rules"),
  create: (body: any) => post<{ rule: any }>("/routing/rules", body),
  update: (id: string, body: any) =>
    patch<any>(`/routing/rules/${id}`, body),
  delete: (id: string) =>
    del<{ message: string }>(`/routing/rules/${id}`),
  simulate: (body: { request: any }) =>
    post<{ routed_to: string; reason: string }>("/routing/simulate", body),
};

// ─── compliance.py ────────────────────────────────────────────────────────────
export const compliance = {
  regulations: () => get<{ regulations: any[] }>("/compliance/regulations"),
  check: (body: {
    text?: string;
    workflow_id?: string;
    regulation?: string;
  }) =>
    post<{ compliant: boolean; issues: any[]; score: number }>(
      "/compliance/check",
      body
    ),
  report: (p?: { from?: string; to?: string }) =>
    get<any>("/compliance/report", p as any),
};

// ─── content_safety.py ────────────────────────────────────────────────────────
export const contentSafety = {
  scan: (body: {
    text?: string;
    image_url?: string;
    context?: string;
  }) =>
    post<{ safe: boolean; categories: any[]; score: number }>(
      "/content-safety/scan",
      body
    ),
  policies: () => get<{ policies: any[] }>("/content-safety/policies"),
  updatePolicy: (id: string, body: any) =>
    patch<any>(`/content-safety/policies/${id}`, body),
  logs: (p?: { limit?: number }) =>
    get<{ logs: any[] }>("/content-safety/logs", p as any),
};

// ─── privacy.py ───────────────────────────────────────────────────────────────
export const privacy = {
  scan: (body: { text: string; mask?: boolean }) =>
    post<{ pii_found: any[]; masked_text?: string }>("/privacy/scan", body),
  settings: () =>
    get<{
      retention_days: number;
      pii_masking: boolean;
      audit_logging: boolean;
    }>("/privacy/settings"),
  updateSettings: (body: any) => patch<any>("/privacy/settings", body),
};

// ─── explainability.py ────────────────────────────────────────────────────────
export const explainability = {
  explain: (body: {
    inference_id: string;
    detail_level?: "summary" | "full";
  }) =>
    post<{ explanation: any; steps: any[] }>(
      "/explainability/explain",
      body
    ),
  history: (p?: { limit?: number }) =>
    get<{ explanations: any[] }>("/explainability/history", p as any),
};

// ─── kill_switch.py ───────────────────────────────────────────────────────────
export const killSwitch = {
  status: () =>
    get<{
      active: boolean;
      triggered_by?: string;
      triggered_at?: string;
      scope?: string;
    }>("/kill-switch/status"),
  trigger: (body: {
    scope: "all" | "model" | "service";
    target_id?: string;
    reason: string;
  }) =>
    post<{ message: string; incident_id: string }>(
      "/kill-switch/trigger",
      body
    ),
  release: (body: { incident_id: string; reason: string }) =>
    post<{ message: string }>("/kill-switch/release", body),
  history: () => get<{ events: any[] }>("/kill-switch/history"),
};

// ─── locker_users.py ──────────────────────────────────────────────────────────
export const lockerUsers = {
  list: () => get<{ users: any[] }>("/locker/users"),
  get: (id: string) => get<any>(`/locker/users/${id}`),
  create: (body: any) => post<any>("/locker/users", body),
  update: (id: string, body: any) =>
    patch<any>(`/locker/users/${id}`, body),
  delete: (id: string) =>
    del<{ message: string }>(`/locker/users/${id}`),
  isolate: (id: string) =>
    post<{ message: string }>(`/locker/users/${id}/isolate`),
};

// ─── locker_security.py ───────────────────────────────────────────────────────
export const lockerSecurity = {
  rules: () => get<{ rules: any[] }>("/locker/security/rules"),
  createRule: (body: any) => post<any>("/locker/security/rules", body),
  updateRule: (id: string, body: any) =>
    patch<any>(`/locker/security/rules/${id}`, body),
  deleteRule: (id: string) =>
    del<{ message: string }>(`/locker/security/rules/${id}`),
  scan: (body: { target_id: string }) =>
    post<{ findings: any[]; risk_score: number }>(
      "/locker/security/scan",
      body
    ),
};

// ─── locker_monitoring.py ─────────────────────────────────────────────────────
export const lockerMonitoring = {
  overview: () => get<{ environments: any[] }>("/locker/monitoring/overview"),
  events: (envId: string, p?: { limit?: number }) =>
    get<{ events: any[] }>(`/locker/monitoring/${envId}/events`, p as any),
  metrics: (envId: string) =>
    get<any>(`/locker/monitoring/${envId}/metrics`),
};

// ─── security_suite.py ────────────────────────────────────────────────────────
export const security = {
  posture: () =>
    get<{ score: number; findings: any[]; last_scan: string }>(
      "/security/posture"
    ),
  threats: (p?: { limit?: number; severity?: string }) =>
    get<{ threats: any[] }>("/security/threats", p as any),
  scan: (body?: { target?: string }) =>
    post<{ scan_id: string; status: string }>("/security/scan", body),
  scanStatus: (id: string) => get<any>(`/security/scan/${id}`),
  incidents: () => get<{ incidents: any[] }>("/security/incidents"),
  resolveIncident: (id: string) =>
    post<{ message: string }>(`/security/incidents/${id}/resolve`),
};

// ─── internal_uacp.py ─────────────────────────────────────────────────────────
export const uacp = {
  status: () =>
    get<{
      version: string;
      state: string;
      operators: number;
      health: string;
    }>("/internal/uacp/status"),
  versions: () => get<{ versions: any[] }>("/internal/uacp/versions"),
  activate: (version: string) =>
    post<{ message: string }>("/internal/uacp/activate", { version }),
  metrics: () =>
    get<{
      latency_p99: number;
      throughput: number;
      error_rate: number;
    }>("/internal/uacp/metrics"),
  config: {
    get: () => get<Record<string, any>>("/internal/uacp/config"),
    update: (body: Record<string, any>) =>
      patch<Record<string, any>>("/internal/uacp/config", body),
  },
  routing: {
    rules: () => get<{ rules: any[] }>("/internal/uacp/routing/rules"),
    update: (body: any) =>
      patch<any>("/internal/uacp/routing/rules", body),
  },
};

// ─── internal_operators.py ────────────────────────────────────────────────────
export const operators = {
  list: (p?: { limit?: number; status?: string }) =>
    get<{ operators: any[]; total: number }>("/internal/operators", p as any),
  get: (id: string) => get<any>(`/internal/operators/${id}`),
  register: (body: { name: string; type: string; config: any }) =>
    post<{ operator: any }>("/internal/operators", body),
  update: (id: string, body: any) =>
    patch<any>(`/internal/operators/${id}`, body),
  delete: (id: string) =>
    del<{ message: string }>(`/internal/operators/${id}`),
  enable: (id: string) =>
    post<{ message: string }>(`/internal/operators/${id}/enable`),
  disable: (id: string) =>
    post<{ message: string }>(`/internal/operators/${id}/disable`),
  health: (id: string) =>
    get<{ healthy: boolean; latency_ms: number }>(
      `/internal/operators/${id}/health`
    ),
};

// ─── source_of_truth_bridge.py ────────────────────────────────────────────────
export const sourceOfTruth = {
  snapshot: () =>
    get<{ hash: string; synced_at: string; components: any[] }>(
      "/source-of-truth/snapshot"
    ),
  sync: () =>
    post<{ message: string; diff: any }>("/source-of-truth/sync"),
  diff: () => get<{ changes: any[] }>("/source-of-truth/diff"),
  rollback: (snapshotId: string) =>
    post<{ message: string }>("/source-of-truth/rollback", {
      snapshot_id: snapshotId,
    }),
  history: (p?: { limit?: number }) =>
    get<{ snapshots: any[] }>("/source-of-truth/history", p as any),
};

// ─── autonomous.py ────────────────────────────────────────────────────────────
export const autonomous = {
  tasks: {
    list: (p?: { limit?: number; status?: string }) =>
      get<{ tasks: any[] }>("/autonomous/tasks", p as any),
    create: (body: {
      goal: string;
      constraints?: any;
      max_steps?: number;
    }) =>
      post<{ task_id: string; status: string }>("/autonomous/tasks", body),
    get: (id: string) => get<any>(`/autonomous/tasks/${id}`),
    cancel: (id: string) =>
      post<{ message: string }>(`/autonomous/tasks/${id}/cancel`),
    steps: (id: string) =>
      get<{ steps: any[] }>(`/autonomous/tasks/${id}/steps`),
  },
};

// ─── job.py ───────────────────────────────────────────────────────────────────
export const jobs = {
  list: (p?: { limit?: number; status?: string; type?: string }) =>
    get<{ jobs: any[]; total: number }>("/jobs", p as any),
  get: (id: string) => get<any>(`/jobs/${id}`),
  cancel: (id: string) =>
    post<{ message: string }>(`/jobs/${id}/cancel`),
  retry: (id: string) =>
    post<{ message: string }>(`/jobs/${id}/retry`),
};

// ─── insights.py ──────────────────────────────────────────────────────────────
export const insights = {
  summary: (p?: { period?: string }) =>
    get<{
      top_models: any[];
      peak_hours: any[];
      savings_opportunity: number;
    }>("/insights/summary", p as any),
  recommendations: () =>
    get<{ recommendations: any[] }>("/insights/recommendations"),
  anomalies: () => get<{ anomalies: any[] }>("/insights/anomalies"),
};

// ─── extract.py ───────────────────────────────────────────────────────────────
export const extract = {
  document: (body: { url?: string; text?: string; format?: string }) =>
    post<{ entities: any[]; summary: string; metadata: any }>(
      "/extract/document",
      body
    ),
  structured: (body: { text: string; schema: any }) =>
    post<{ data: any }>("/extract/structured", body),
};

// ─── upload.py ────────────────────────────────────────────────────────────────
export const upload = {
  file: async (
    file: File
  ): Promise<{
    file_id: string;
    url: string;
    name: string;
    size: number;
  }> => {
    const form = new FormData();
    form.append("file", file);
    const t = token();
    const res = await fetch(`${base()}/api/v1/upload`, {
      method: "POST",
      headers: { ...(t ? { Authorization: `Bearer ${t}` } : {}) },
      credentials: "include",
      body: form,
    });
    if (!res.ok) throw new Error(`upload → ${res.status}`);
    return res.json();
  },
};

// ─── transcribe.py ────────────────────────────────────────────────────────────
export const transcribe = {
  audio: async (
    file: File
  ): Promise<{
    text: string;
    duration_seconds: number;
    language: string;
  }> => {
    const form = new FormData();
    form.append("audio", file);
    const t = token();
    const res = await fetch(`${base()}/api/v1/transcribe`, {
      method: "POST",
      headers: { ...(t ? { Authorization: `Bearer ${t}` } : {}) },
      credentials: "include",
      body: form,
    });
    if (!res.ok) throw new Error(`transcribe → ${res.status}`);
    return res.json();
  },
};

// ─── ai.py ────────────────────────────────────────────────────────────────────
export const ai = {
  embeddings: (body: { text: string | string[]; model?: string }) =>
    post<{ embeddings: number[][]; model: string; usage: any }>(
      "/ai/embeddings",
      body
    ),
  classify: (body: {
    text: string;
    labels: string[];
    model?: string;
  }) =>
    post<{ label: string; scores: Record<string, number> }>(
      "/ai/classify",
      body
    ),
  summarize: (body: {
    text: string;
    length?: "short" | "medium" | "long";
  }) => post<{ summary: string }>("/ai/summarize", body),
  translate: (body: {
    text: string;
    target_language: string;
    source_language?: string;
  }) =>
    post<{ translated: string; detected_language?: string }>(
      "/ai/translate",
      body
    ),
  fineTune: {
    list: () => get<{ jobs: any[] }>("/ai/fine-tune"),
    create: (body: { model: string; dataset_id: string; config?: any }) =>
      post<{ job_id: string; status: string }>("/ai/fine-tune", body),
    get: (id: string) => get<any>(`/ai/fine-tune/${id}`),
    cancel: (id: string) =>
      post<{ message: string }>(`/ai/fine-tune/${id}/cancel`),
  },
};

// ─── search.py ────────────────────────────────────────────────────────────────
export const search = {
  query: (q: string, p?: { type?: string; limit?: number }) =>
    get<{ results: any[]; total: number }>("/search", {
      q,
      ...p,
    } as any),
};

// ─── suggestions.py ───────────────────────────────────────────────────────────
export const suggestions = {
  get: (p?: { context?: string; model?: string }) =>
    get<{ suggestions: string[] }>("/suggestions", p as any),
};

// ─── support_bot.py ───────────────────────────────────────────────────────────
export const support = {
  message: (body: { message: string; session_id?: string }) =>
    post<{ reply: string; session_id: string; sources: any[] }>(
      "/support/message",
      body
    ),
  history: (sessionId: string) =>
    get<{ messages: any[] }>(`/support/history/${sessionId}`),
};

// ─── plugins.py ───────────────────────────────────────────────────────────────
export const plugins = {
  list: () => get<{ plugins: any[] }>("/plugins"),
  get: (id: string) => get<any>(`/plugins/${id}`),
  install: (id: string, config?: any) =>
    post<{ message: string }>(`/plugins/${id}/install`, config),
  uninstall: (id: string) =>
    del<{ message: string }>(`/plugins/${id}`),
  toggle: (id: string, enabled: boolean) =>
    patch<any>(`/plugins/${id}`, { enabled }),
};

// ─── metrics.py ───────────────────────────────────────────────────────────────
export const metrics = {
  /** Returns raw Prometheus text format */
  prometheus: (): Promise<string> => {
    const t = token();
    return fetch(`${base()}/api/v1/metrics`, {
      headers: { ...(t ? { Authorization: `Bearer ${t}` } : {}) },
    }).then((r) => r.text());
  },
};

// ─── telemetry.py ─────────────────────────────────────────────────────────────
export const telemetry = {
  event: (body: {
    event: string;
    properties?: Record<string, any>;
    timestamp?: string;
  }) => post<{ received: boolean }>("/telemetry/event", body),
  batch: (events: any[]) =>
    post<{ received: number }>("/telemetry/batch", { events }),
};

// ─── export.py ────────────────────────────────────────────────────────────────
export const exportData = {
  request: (body: {
    type: "logs" | "usage" | "transactions";
    format?: "csv" | "json";
    from?: string;
    to?: string;
  }) =>
    post<{ export_id: string; status: string; download_url?: string }>(
      "/export",
      body
    ),
  status: (id: string) =>
    get<{ status: string; download_url?: string }>(`/export/${id}`),
};

// ─── Aggregate export ─────────────────────────────────────────────────────────

export const api = {
  health,
  audit,
  auth,
  exec,
  workspace,
  wallet,
  billing,
  subscriptions,
  budget,
  cost,
  admin,
  marketplace,
  marketplaceAutomation,
  monitoring,
  pulse,
  pipelines,
  deployments,
  edgeCanary,
  routing,
  compliance,
  contentSafety,
  privacy,
  explainability,
  killSwitch,
  lockerUsers,
  lockerSecurity,
  lockerMonitoring,
  security,
  uacp,
  operators,
  sourceOfTruth,
  autonomous,
  jobs,
  insights,
  extract,
  upload,
  transcribe,
  ai,
  search,
  suggestions,
  support,
  plugins,
  metrics,
  telemetry,
  exportData,
};

export default api;
