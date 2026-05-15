/**
 * Marketplace Service — Full Competitive Advantage Map
 * Maps to: backend/apps/api/routers/marketplace_v1.py
 *
 * Every listing MUST show:
 *   type | category | tags | preflight cost | quality prediction
 *   failure risk | install button | source verification
 *   compliance badges | install count | audit/evidence behavior
 *
 * Marketplace is NOT a list of external links.
 * It is where Veklom's advantages become buyable.
 */
import { api, noRoute } from "@/lib/api";

export interface MarketplaceListing {
  id: string;
  name: string;
  description: string;
  type: "tool" | "pipeline" | "connector" | "plugin" | "model" | string;
  category: string;
  tags: string[];
  source_url?: string;
  source_license?: string;
  install_count: number;
  rating: number | null;
  compliance_badges: string[];
  is_installed: boolean;
  created_at: string;
  updated_at: string;
}

export interface PreflightResult {
  estimated_cost: string;
  quality_prediction: number;
  failure_risk: number;
  selected_provider?: string;
  compliance_status: "pass" | "warn" | "fail";
  pii_risk: "none" | "low" | "medium" | "high";
  installable: boolean;
  warnings: string[];
}

export interface AutoClassifyResult {
  type: string;
  category: string;
  tags: string[];
  confidence: number;
}

export interface AutoValidateResult {
  is_valid: boolean;
  errors: string[];
  warnings: string[];
  pii_detected: boolean;
  compliance_issues: string[];
}

export const marketplaceV2Service = {
  // ─── Discovery ────────────────────────────────────────────────────────────

  /**
   * GET /api/v1/marketplace/listings
   * Main browse view.
   */
  listListings: (params?: {
    category?: string;
    type?: string;
    tags?: string;
    search?: string;
    page?: number;
    limit?: number;
    sort?: "popular" | "newest" | "cheapest" | "rating";
  }) => api.get<MarketplaceListing[]>("/marketplace/listings", { params }),

  /**
   * GET /api/v1/marketplace/categories
   * Category browser — left nav filter.
   */
  listCategories: () => api.get<{ id: string; name: string; count: number }[]>("/marketplace/categories"),

  /**
   * GET /api/v1/marketplace/featured
   * Hero / featured section on marketplace home.
   */
  getFeatured: () => api.get<MarketplaceListing[]>("/marketplace/featured"),

  /**
   * GET /api/v1/marketplace/listings/{listing_id}
   * Detail page.
   */
  getListing: (listing_id: string) =>
    api.get<MarketplaceListing>(`/marketplace/listings/${listing_id}`),

  // ─── Preflight (the moat) ──────────────────────────────────────────────────

  /**
   * GET /api/v1/marketplace/listings/{listing_id}/preflight
   * Call before install button activates.
   * Returns: estimated cost, quality prediction, failure risk, compliance status,
   * PII risk, installability, warnings.
   */
  preflight: (listing_id: string) =>
    api.get<PreflightResult>(`/marketplace/listings/${listing_id}/preflight`),

  // ─── Install ──────────────────────────────────────────────────────────────

  /**
   * POST /api/v1/marketplace/listings/{listing_id}/install
   * One-click install → becomes real pipeline in workspace.
   */
  install: (listing_id: string) =>
    api.post(`/marketplace/listings/${listing_id}/install`),

  /**
   * No route found: DELETE /api/v1/marketplace/listings/{listing_id}/install
   */
  uninstall: (listing_id: string) =>
    noRoute(`/marketplace/listings/${listing_id}/install`),

  // ─── Publishing pipeline ──────────────────────────────────────────────────

  /**
   * POST /api/v1/marketplace/listings/auto-classify
   * Auto-detect type, category, tags for a new listing.
   */
  autoClassify: (body: { name: string; description: string; source_url?: string; readme?: string }) =>
    api.post<AutoClassifyResult>("/marketplace/listings/auto-classify", body),

  /**
   * POST /api/v1/marketplace/listings/auto-validate
   * Validate listing before publish — runs PII detection, compliance check.
   */
  autoValidate: (body: Record<string, unknown>) =>
    api.post<AutoValidateResult>("/marketplace/listings/auto-validate", body),

  /**
   * POST /api/v1/marketplace/listings/import-github
   * Import GitHub repo as listing.
   * Flow: find GitHub tool → import → auto-classify → auto-validate → publish.
   */
  importFromGitHub: (body: { repo_url: string; branch?: string; subpath?: string }) =>
    api.post("/marketplace/listings/import-github", body),

  /**
   * POST /api/v1/marketplace/listings/from-plugin
   * Wrap an enabled plugin as a marketplace listing.
   */
  listingFromPlugin: (body: { plugin_id: string; name?: string; description?: string }) =>
    api.post("/marketplace/listings/from-plugin", body),

  /**
   * POST /api/v1/marketplace/listings/create
   * Create listing manually.
   */
  createListing: (body: Record<string, unknown>) =>
    api.post("/marketplace/listings/create", body),

  /**
   * PATCH /api/v1/marketplace/listings/{listing_id}
   */
  updateListing: (listing_id: string, body: Record<string, unknown>) =>
    api.patch(`/marketplace/listings/${listing_id}`, body),

  /**
   * No route found: POST /api/v1/marketplace/listings/{listing_id}/publish
   */
  publishListing: (listing_id: string) =>
    noRoute(`/marketplace/listings/${listing_id}/publish`),

  /**
   * No route found: DELETE /api/v1/marketplace/listings/{listing_id}
   */
  deleteListing: (listing_id: string) =>
    noRoute(`/marketplace/listings/${listing_id}`),

  // ─── Reviews ──────────────────────────────────────────────────────────────

  listReviews: (listing_id: string) =>
    noRoute(`/marketplace/listings/${listing_id}/reviews`),

  createReview: (listing_id: string, body: { rating: number; comment?: string }) =>
    noRoute(`/marketplace/listings/${listing_id}/reviews`, body),

  // ─── Purchases ────────────────────────────────────────────────────────────

  purchase: (body: { listing_id: string; payment_method_id?: string }) =>
    api.post("/marketplace/payments/create-checkout", { listing_id: body.listing_id }),

  listPurchases: (params?: { page?: number; limit?: number }) =>
    api.get("/marketplace/orders/me", { params }),
};
