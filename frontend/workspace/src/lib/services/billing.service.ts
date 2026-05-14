import { api } from "@/lib/api";

export const billingService = {
  /** GET /billing/summary */
  getSummary: () => api.get("/billing/summary"),

  /** GET /billing/invoices */
  listInvoices: (params?: { page?: number; limit?: number }) =>
    api.get("/billing/invoices", { params }),

  /** GET /billing/invoices/{invoice_id} */
  getInvoice: (invoice_id: string) => api.get(`/billing/invoices/${invoice_id}`),

  /** GET /billing/payment-methods */
  listPaymentMethods: () => api.get("/billing/payment-methods"),

  /** POST /billing/payment-methods */
  addPaymentMethod: (body: { payment_method_id: string }) =>
    api.post("/billing/payment-methods", body),

  /** DELETE /billing/payment-methods/{pm_id} */
  deletePaymentMethod: (pm_id: string) =>
    api.delete(`/billing/payment-methods/${pm_id}`),

  /** GET /subscriptions */
  getSubscription: () => api.get("/subscriptions"),

  /** POST /subscriptions/checkout */
  createCheckout: (body: { price_id: string; success_url: string; cancel_url: string }) =>
    api.post("/subscriptions/checkout", body),

  /** POST /subscriptions/portal */
  createPortalSession: (body: { return_url: string }) =>
    api.post("/subscriptions/portal", body),

  /** POST /subscriptions/cancel */
  cancelSubscription: () => api.post("/subscriptions/cancel"),

  /** GET /subscriptions/plans */
  listPlans: () => api.get("/subscriptions/plans"),

  /** GET /token-wallet */
  getWallet: () => api.get("/token-wallet"),

  /** GET /token-wallet/transactions */
  getTransactions: (params?: { page?: number; limit?: number }) =>
    api.get("/token-wallet/transactions", { params }),

  /** POST /token-wallet/topup */
  topUp: (body: { amount: number; payment_method_id?: string }) =>
    api.post("/token-wallet/topup", body),

  /** GET /cost/breakdown */
  getCostBreakdown: (params?: { from?: string; to?: string }) =>
    api.get("/cost/breakdown", { params }),

  /** GET /cost/estimate */
  estimateCost: (params: { model: string; tokens: number; provider?: string }) =>
    api.get("/cost/estimate", { params }),

  /** GET /budget */
  getBudget: () => api.get("/budget"),

  /** POST /budget */
  setBudget: (body: { monthly_limit: number; alert_threshold?: number }) =>
    api.post("/budget", body),

  /** PATCH /budget */
  updateBudget: (body: { monthly_limit?: number; alert_threshold?: number }) =>
    api.patch("/budget", body),
};
