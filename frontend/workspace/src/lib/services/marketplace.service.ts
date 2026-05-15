import { api, noRoute } from "@/lib/api";

export const marketplaceService = {
  // ─── Listings ────────────────────────────────────────────
  /** GET /marketplace/listings */
  listListings: (params?: {
    category?: string;
    page?: number;
    limit?: number;
    search?: string;
    sort?: string;
  }) => api.get("/marketplace/listings", { params }),

  /** GET /marketplace/listings/{listing_id} */
  getListing: (listing_id: string) =>
    api.get(`/marketplace/listings/${listing_id}`),

  /** POST /marketplace/listings/create */
  createListing: (body: Record<string, unknown>) =>
    api.post("/marketplace/listings", body),

  /** PATCH /marketplace/listings/{listing_id} */
  updateListing: (listing_id: string, body: Record<string, unknown>) =>
    api.patch(`/marketplace/listings/${listing_id}`, body),

  /** No route found: DELETE /marketplace/listings/{listing_id} */
  deleteListing: (listing_id: string) =>
    noRoute(`/marketplace/listings/${listing_id}`),

  /** No route found: POST /marketplace/listings/{listing_id}/publish */
  publishListing: (listing_id: string) =>
    noRoute(`/marketplace/listings/${listing_id}/publish`),

  // ─── Purchases / Installs ────────────────────────────────
  /** POST /marketplace/checkout */
  purchase: (body: { listing_id: string; payment_method_id?: string }) =>
    api.post("/marketplace/payments/create-checkout", { listing_id: body.listing_id }),

  /** GET /marketplace/orders */
  listPurchases: (params?: { page?: number; limit?: number }) =>
    api.get("/marketplace/orders", { params }),

  /** POST /marketplace/listings/{listing_id}/install */
  install: (listing_id: string) =>
    api.post(`/marketplace/listings/${listing_id}/install`),

  /** No route found: DELETE /marketplace/install/{listing_id} */
  uninstall: (listing_id: string) =>
    noRoute(`/marketplace/install/${listing_id}`),

  // ─── Reviews ─────────────────────────────────────────────
  /** No route found: GET /marketplace/listings/{listing_id}/reviews */
  listReviews: (listing_id: string) =>
    noRoute(`/marketplace/listings/${listing_id}/reviews`),

  /** No route found: POST /marketplace/listings/{listing_id}/reviews */
  createReview: (listing_id: string, body: { rating: number; comment?: string }) =>
    noRoute(`/marketplace/listings/${listing_id}/reviews`, body),

  // ─── Automation ──────────────────────────────────────────
  /** No route found: GET /marketplace/automation/jobs */
  listAutomationJobs: (params?: { page?: number; limit?: number; status?: string }) =>
    noRoute("/marketplace/automation/jobs", params),

  /** POST /marketplace/automation/run */
  createAutomationJob: (body: Record<string, unknown>) =>
    api.post("/marketplace/automation/run", body),

  /** No route found: GET /marketplace/automation/jobs/{job_id} */
  getAutomationJob: (job_id: string) =>
    noRoute(`/marketplace/automation/jobs/${job_id}`),

  /** No route found: POST /marketplace/automation/jobs/{job_id}/cancel */
  cancelAutomationJob: (job_id: string) =>
    noRoute(`/marketplace/automation/jobs/${job_id}/cancel`),
};
