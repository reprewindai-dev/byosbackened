export interface User {
  id: string;
  email: string;
  name?: string;
  full_name?: string | null;
  role: "owner" | "admin" | "analyst" | "user" | "readonly" | "developer" | "viewer" | "billing";
  mfa_enabled: boolean;
  mfa_backup_codes_remaining?: number;
  created_at: string;
  avatar_url?: string | null;
  workspace_id?: string;
  workspace_name?: string;
  workspace_slug?: string;
  industry?: string;
  playground_profile?: string;
  risk_tier?: string;
  default_policy_pack?: string;
  plan?: string;
  region?: string;
  last_login_at?: string | null;
  last_login?: string | null;
  is_superuser?: boolean;
  github_username?: string | null;
  github_connected?: boolean;
}

export interface PlatformPulseActivity {
  kind: "listing_new" | "order_completed" | "upgrade" | "user_registered" | "rate_limit_hit";
  actor: string;
  ts: string;
  title?: string;
  order_id?: string;
  to_plan?: string;
  tier?: string;
  amount_cents?: number;
  billing_cycle?: string;
}

export interface PlatformPulseSuperuser {
  mrr_cents: number;
  mrr_delta_pct_vs_prior: number;
  arpu_cents: number;
  churn_pct_30d: number;
  trial_conversions_30d: number;
  open_security_threats: number;
  past_due_subscriptions: number;
  marketplace_gross_30d_cents: number;
}

export interface PlatformPulse {
  users: { total: number; delta_pct_30d: number; added_30d: number };
  active_listings: { total: number; added_7d: number };
  tool_installs: { total: number; active_tools: number };
  orders_30d: { count: number; delta_pct_vs_prior: number };
  paid_tier_users: { total: number; upgrades_30d: number };
  tier_distribution: Record<string, number>;
  activity: PlatformPulseActivity[];
  is_superuser: boolean;
  generated_at: string;
  superuser?: PlatformPulseSuperuser;
}

export interface LiveOpsOccupant {
  user_id: string;
  email: string;
  full_name?: string | null;
  role: string;
  is_superuser: boolean;
  session_id: string;
  last_accessed: string;
  expires_at: string;
  ip_address?: string | null;
}

export interface LiveOpsWorkspace {
  workspace_id: string;
  workspace_name: string;
  workspace_slug: string;
  is_active: boolean;
  active_session_count: number;
  active_user_count: number;
  recent_requests_15m: number;
  failed_requests_15m: number;
  last_request_at?: string | null;
  last_error_at?: string | null;
  current_status: string;
  occupants: LiveOpsOccupant[];
}

export interface LiveOpsSummary {
  generated_at: string;
  active_tenants: number;
  open_rooms: number;
  live_users: number;
  live_sessions: number;
  degraded_workspaces: number;
  workspaces: LiveOpsWorkspace[];
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
  access_token?: string;
  refresh_token?: string;
  token_type?: "bearer";
  expires_in?: number;
  user?: User;
  mfa_required?: boolean;
  mfa_challenge_token?: string;
  user_id?: string;
  workspace_id?: string;
  email?: string;
  github_username?: string;
}

export interface LoginRequest {
  email: string;
  password: string;
  mfa_code?: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  full_name?: string;
  name?: string;
  workspace_name?: string;
  signup_type?: string;
  industry?: string;
  utm_source?: string;
  utm_campaign?: string;
}

export interface PlaygroundScenario {
  scenario_id: string;
  title: string;
  prompt: string;
  suggested_workflow: string[];
  suggested_models_tools: string[];
  evidence_emphasis: string[];
}

export interface PlaygroundProfile {
  workspaceId: string;
  tenantId: string;
  industry: string;
  playground_profile: string;
  profileName: string;
  risk_tier: string;
  policy_pack: string;
  suggested_demo_prompts: string[];
  sample_workflows: string[];
  policy_checks: string[];
  evidence_requirements: string[];
  gpc_templates: string[];
  restricted_actions: string[];
  recommended_model_tool_constraints: string[];
  default_demo_scenarios: PlaygroundScenario[];
  default_blocking_rules: string[];
}

export interface GpcHandoff {
  workspaceId: string;
  tenantId: string;
  industry: string;
  playground_profile: string;
  scenario_id: string;
  scenario_title: string;
  user_input: string;
  risk_tier: string;
  policy_pack: string;
  evidence_requirements: string[];
  blocking_rules: string[];
  suggested_workflow: string[];
  suggested_models_tools: string[];
  handoff_status: "prepared";
  claim_level: "draft";
  github_connected?: boolean;
  selected_repo_full_name?: string | null;
  selected_repo_id?: number | null;
  selected_branch?: string | null;
  repo_context_scope?: string;
  allowed_repo_actions?: string[];
  restricted_repo_actions?: string[];
}

export interface MFASetupResponse {
  secret: string;
  provisioning_uri: string;
  qr_url: string;
}

export interface MFAEnableResponse {
  message: string;
  mfa_enabled: boolean;
  audit_event: string;
  backup_codes: string[];
}

export interface MFARecoveryCodeStatus {
  backup_codes_remaining: number;
  backup_codes_total: number;
}

export interface ConnectedAccountsResponse {
  github_configured: boolean;
  github_connected: boolean;
  github_username?: string | null;
  github_connected_at?: string | null;
  github_account_id?: string | null;
}

export interface GithubRepo {
  id: number;
  name: string;
  full_name: string;
  description?: string | null;
  html_url: string;
  stars: number;
  language?: string | null;
  updated_at: string;
  private: boolean;
  visibility?: string;
  default_branch?: string | null;
  permissions?: Record<string, boolean>;
  topics: string[];
}

export interface WorkspaceSelectedGithubRepo {
  id: string;
  workspace_id: string;
  github_account_id?: string | null;
  connected_account_id?: string | null;
  repo_full_name: string;
  repo_id?: number | null;
  default_branch?: string | null;
  permissions?: Record<string, boolean>;
  visibility?: string | null;
  repo_context_scope: string;
  allowed_repo_actions: string[];
  restricted_repo_actions: string[];
  selected_at?: string | null;
  selected_by?: string | null;
}

export interface WorkspaceGithubIntegration {
  github_configured: boolean;
  github_connected: boolean;
  github_username?: string | null;
  github_account_id?: string | null;
  repo_access_mode: string;
  repo_context_scope: string;
  selected_repos: WorkspaceSelectedGithubRepo[];
  policy: {
    default_repo_access: string;
    private_repo_external_provider_transfer_requires_policy: boolean;
    write_commit_pr_actions_enabled: boolean;
    secrets_extraction_allowed: boolean;
    human_approval_required_for_high_risk_actions: boolean;
  };
}

export interface AcceptInviteRequest {
  invite_secret: string;
  password: string;
  full_name?: string;
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
  // Per-metric history for inline sparklines (24 buckets × 5min = last 2h).
  requests_series?: number[];
  tokens_series?: number[];
  spend_series?: number[];
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

// ─── Service Gateway (BYOS Internal Services) ──────────────────────────────

export type ServiceType = "ai_provider" | "core" | "integration" | "monitoring" | "billing";
export type ServiceStatus = "healthy" | "degraded" | "unhealthy" | "unknown";

export interface RegisteredService {
  service_id: string;
  name: string;
  service_type: ServiceType;
  base_url: string;
  health_endpoint: string;
  status: ServiceStatus;
  enabled: boolean;
  last_health_check: number | null;
  last_healthy: number | null;
  metadata: Record<string, unknown>;
}

export interface ServiceTopologyLayer {
  id: string;
  name: string;
  url: string;
  status: ServiceStatus;
  enabled: boolean;
}

export interface WiringEdge {
  from: string;
  to: string;
  protocol: string;
  description: string;
}

export interface ServiceTopology {
  platform: string;
  version: string;
  layers: {
    ai_providers: ServiceTopologyLayer[];
    core: ServiceTopologyLayer[];
    integrations: ServiceTopologyLayer[];
    monitoring: ServiceTopologyLayer[];
    billing: ServiceTopologyLayer[];
  };
  wiring: WiringEdge[];
  timestamp: number;
}
