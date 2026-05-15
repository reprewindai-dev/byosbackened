import { api, noRoute } from "@/lib/api";

export const billingService = {
  /** GET /billing/report */
  getSummary: () => api.get("/billing/report"),

  /** No route found: GET /billing/invoices */
  listInvoices: (params?: { page?: number; limit?: number }) =>
    noRoute("/billing/invoices", params),

  /** No route found: GET /billing/invoices/{invoice_id} */
  getInvoice: (invoice_id: string) => noRoute(`/billing/invoices/${invoice_id}`),

  /** No route found: GET /billing/payment-methods */
  listPaymentMethods: () => noRoute("/billing/payment-methods"),

  /** No route found: POST /billing/payment-methods */
  addPaymentMethod: (body: { payment_method_id: string }) =>
    noRoute("/billing/payment-methods", body),

  /** No route found: DELETE /billing/payment-methods/{pm_id} */
  deletePaymentMethod: (pm_id: string) =>
    noRoute(`/billing/payment-methods/${pm_id}`),

  /** GET /subscriptions/current */
  getSubscription: () => api.get("/subscriptions/current"),

  /** POST /subscriptions/checkout */
  createCheckout: (body: { plan: "starter" | "pro"; billing_cycle?: "activation"; success_url: string; cancel_url: string }) =>
    api.post("/subscriptions/checkout", body),

  /** POST /subscriptions/portal */
  createPortalSession: (body: { return_url: string }) =>
    api.post("/subscriptions/portal", null, { params: { return_url: body.return_url } }),

  /** No route found: POST /subscriptions/cancel */
  cancelSubscription: () => noRoute("/subscriptions/cancel"),

  /** GET /subscriptions/plans */
  listPlans: () => api.get("/subscriptions/plans"),

  /** GET /billing/wallet */
  getWallet: () => api.get("/billing/wallet"),

  /** GET /billing/transactions */
  getTransactions: (params?: { limit?: number; offset?: number; transaction_type?: string }) =>
    api.get("/billing/transactions", { params }),

  /** GET /billing/topup */
  listTopupOptions: () => api.get("/billing/topup"),

  /** POST /billing/topup */
  topUp: (body: { pack_name: string; success_url: string; cancel_url: string }) =>
    api.post("/billing/topup", body),

  /** GET /billing/breakdown */
  getCostBreakdown: (params?: { from?: string; to?: string }) =>
    api.get("/cost/breakdown", { params }),

  /** POST /cost/predict */
  estimateCost: (params: { model: string; tokens: number; provider?: string }) =>
    params.provider
      ? api.post("/cost/predict", {
          operation_type: "generation",
          provider: params.provider,
          model: params.model,
          input_tokens: params.tokens,
        })
      : noRoute("/cost/predict requires provider"),

  /** GET /budget */
  getBudget: () => api.get("/budget/caps"),

  /** POST /budget */
  setBudget: (body: { monthly_limit: number; alert_threshold?: number }) =>
    api.post("/budget/caps", body),

  /** POST /budget */
  updateBudget: (body: { monthly_limit?: number; alert_threshold?: number }) =>
    api.post("/budget/caps", body),
};
