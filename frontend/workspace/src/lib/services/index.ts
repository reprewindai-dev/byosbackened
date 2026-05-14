/**
 * Central services export — import from here in all components and hooks.
 *
 * Organized by competitive advantage layer:
 *
 * KILLER FEATURE (build P0 first):
 *   costIntelligenceService  — pre-run cost prediction
 *   autonomousService        — ML routing, quality, failure risk, training
 *   complianceService        — audit trail, hash verification, evidence
 *   marketplaceV2Service     — listings, preflight, install, auto-classify
 *
 * PLATFORM SERVICES:
 *   authService              — auth, API keys, OAuth
 *   workspaceService         — settings, members, providers
 *   aiService                — chat, embed, models, SSE stream
 *   uploadService            — file upload, transcribe, extract, export
 *   billingService           — billing, subscriptions, token wallet
 *   adminService             — users, workspaces, stats, flags, kill-switch
 *   monitoringService        — platform pulse, alerts, audit, telemetry, insights
 *   securityService          — security suite, content safety, locker, compliance
 *   pipelinesService         — pipelines, deployments, jobs, demo pipeline
 *   edgeService              — edge devices, MQTT, Modbus, SNMP, canary
 *   lockerService            — locker users, access log, MFA
 *   internalService          — operators, UACP control plane
 *   routingService           — routing rules, search, suggestions, explainability, autonomous tasks
 *   supportService           — support bot, tickets, plugins
 */

// ─── Killer Feature Services ──────────────────────────────────────────────────
export { costIntelligenceService } from "./cost-intelligence.service";
export { autonomousService } from "./autonomous.service";
export { complianceService } from "./compliance.service";
export { marketplaceV2Service } from "./marketplace-v2.service";

// ─── Platform Services ────────────────────────────────────────────────────────
export { authService } from "./auth.service";
export { workspaceService } from "./workspace.service";
export { aiService } from "./ai.service";
export { uploadService } from "./upload.service";
export { billingService } from "./billing.service";
export { adminService } from "./admin.service";
export { marketplaceService } from "./marketplace.service";
export { monitoringService } from "./monitoring.service";
export { securityService } from "./security.service";
export { pipelinesService } from "./pipelines.service";
export { edgeService } from "./edge.service";
export { lockerService } from "./locker.service";
export { internalService } from "./internal.service";
export { routingService } from "./routing.service";
export { supportService } from "./support.service";

// ─── Type re-exports ──────────────────────────────────────────────────────────
export type { CostPredictRequest, CostPredictResponse, CostHistoryEntry } from "./cost-intelligence.service";
export type { MLCostPredictResponse, RouteSelectResponse, RoutingStatsResponse, QualityPredictResponse, FailureRiskResponse, TrainResponse } from "./autonomous.service";
export type { AuditLogEntry, AuditVerifyResult, ComplianceEvidenceBundle } from "./compliance.service";
export type { MarketplaceListing, PreflightResult, AutoClassifyResult, AutoValidateResult } from "./marketplace-v2.service";
