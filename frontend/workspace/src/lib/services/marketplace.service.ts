import { api } from "@/lib/api";

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

  /** POST /marketplace/listings */
  createListing: (body: Record<string, unknown>) =>
    api.post("/marketplace/listings", body),

  /** PATCH /marketplace/listings/{listing_id} */
  updateListing: (listing_id: string, body: Record<string, unknown>) =>
    api.patch(`/marketplace/listings/${listing_id}`, body),

  /** DELETE /marketplace/listings/{listing_id} */
  deleteListing: (listing_id: string) =>
    api.delete(`/marketplace/listings/${listing_id}`),

  /** POST /marketplace/listings/{listing_id}/publish */
  publishListing: (listing_id: string) =>
    api.post(`/marketplace/listings/${listing_id}/publish`),

  // ─── Purchases / Installs ────────────────────────────────
  /** POST /marketplace/purchase */
  purchase: (body: { listing_id: string; payment_method_id?: string }) =>
    api.post("/marketplace/purchase", body),

  /** GET /marketplace/purchases */
  listPurchases: (params?: { page?: number; limit?: number }) =>
    api.get("/marketplace/purchases", { params }),

  /** POST /marketplace/install/{listing_id} */
  install: (listing_id: string) =>
    api.post(`/marketplace/install/${listing_id}`),

  /** DELETE /marketplace/install/{listing_id} */
  uninstall: (listing_id: string) =>
    api.delete(`/marketplace/install/${listing_id}`),

  // ─── Reviews ─────────────────────────────────────────────
  /** GET /marketplace/listings/{listing_id}/reviews */
  listReviews: (listing_id: string) =>
    api.get(`/marketplace/listings/${listing_id}/reviews`),

  /** POST /marketplace/listings/{listing_id}/reviews */
  createReview: (listing_id: string, body: { rating: number; comment?: string }) =>
    api.post(`/marketplace/listings/${listing_id}/reviews`, body),

  // ─── Automation ──────────────────────────────────────────
  /** GET /marketplace/automation/jobs */
  listAutomationJobs: (params?: { page?: number; limit?: number; status?: string }) =>
    api.get("/marketplace/automation/jobs", { params }),

  /** POST /marketplace/automation/jobs */
  createAutomationJob: (body: Record<string, unknown>) =>
    api.post("/marketplace/automation/jobs", body),

  /** GET /marketplace/automation/jobs/{job_id} */
  getAutomationJob: (job_id: string) =>
    api.get(`/marketplace/automation/jobs/${job_id}`),

  /** POST /marketplace/automation/jobs/{job_id}/cancel */
  cancelAutomationJob: (job_id: string) =>
    api.post(`/marketplace/automation/jobs/${job_id}/cancel`),
};
