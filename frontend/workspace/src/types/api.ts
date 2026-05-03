export interface User {
  id: string;
  email: string;
  name?: string;
  role: "owner" | "admin" | "developer" | "viewer" | "billing";
  mfa_enabled: boolean;
  created_at: string;
  avatar_url?: string | null;
  workspace_id?: string;
  workspace_name?: string;
  plan?: string;
  region?: string;
  last_login_at?: string | null;
}

export interface Workspace {
  id: string;
  name: string;
  slug: string;
  region: string;
  pricing_tier: "free_evaluation" | "founding" | "standard" | "regulated" | "enterprise";
  activation_type: string;
  event_price_table_version: string;
  reserve_minimum_cents: number;
  reserve_balance_cents: number;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
  expires_in: number;
  user?: User;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  name?: string;
  workspace_name?: string;
}

export interface KpiSummary {
  requests_per_minute: number;
  requests_delta_pct: number;
  p50_latency_ms: number;
  p50_delta_ms: number;
  tokens_per_second: number;
  tokens_delta_pct: number;
  spend_today_cents: number;
  spend_cap_pct: number;
  active_models: number;
  active_models_quantized: number;
  audit_entries: number;
  audit_verified_pct: number;
}

export interface RoutingStatus {
  primary_plane: string;
  burst_plane: string;
  primary_util_pct: number;
  burst_util_pct: number;
  primary_hosts: { name: string; util_pct: number; detail: string }[];
  series: { t: string; primary: number; burst: number }[];
}

export interface RecentRun {
  id: string;
  model: string;
  route: "primary" | "burst";
  latency_ms: number;
  tokens: number;
  cost_cents: number;
  policy: "passed" | "redacted" | "blocked";
  when: string;
}

export interface PolicyEvent {
  id: string;
  ts: string;
  kind: "inbound_prompt" | "policy_match" | "route_decision" | "inference_complete" | "audit_signed";
  summary: string;
  detail: string;
}

export interface AuditEntry {
  id: string;
  kind: string;
  subject: string;
  actor: string;
  ts: string;
  hash_prefix: string;
}

export interface SpendBreakdown {
  spend_cents: number;
  cap_cents: number;
  inference_cents: number;
  embeddings_cents: number;
  gpu_burst_cents: number;
  storage_cents: number;
  burn_rate_per_min_cents: number;
  forecast_eod_cents: number;
  forecast_cap_pct: number;
}

export interface Alert {
  id: string;
  severity: "info" | "warn" | "error";
  title: string;
  scope: string;
  when: string;
}

export interface FleetModel {
  id: string;
  name: string;
  quant: string;
  replicas: number;
  route: "primary" | "burst";
  p50_ms: number;
}

export interface OverviewPayload {
  kpi: KpiSummary;
  routing: RoutingStatus;
  spend: SpendBreakdown;
  recent_runs: RecentRun[];
  policy_events: PolicyEvent[];
  alerts: Alert[];
  audit_trail: AuditEntry[];
  fleet: FleetModel[];
}

export interface ApiError {
  detail: string | { msg: string; type: string }[];
  status_code?: number;
}
