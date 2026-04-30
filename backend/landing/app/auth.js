// Veklom self-serve auth client.
// Stores access + refresh tokens in localStorage, exposes a small API.
const _hostname = window.location.hostname;
if (!window.VEKLOM_API) {
  if (_hostname.endsWith(".veklom.dev")) {
    window.VEKLOM_API = "https://api.veklom.dev/api/v1";
  } else {
    window.VEKLOM_API = "https://api.veklom.com/api/v1";
  }
}

const VK = {
  apiBase: window.VEKLOM_API,

  saveTokens(t) {
    localStorage.setItem("vk_access", t.access_token);
    localStorage.setItem("vk_refresh", t.refresh_token);
    localStorage.setItem("vk_expires_at", String(Date.now() + (t.expires_in || 1800) * 1000));
  },

  clearTokens() {
    localStorage.removeItem("vk_access");
    localStorage.removeItem("vk_refresh");
    localStorage.removeItem("vk_expires_at");
  },

  isLoggedIn() {
    const access = localStorage.getItem("vk_access");
    const expiresAtRaw = localStorage.getItem("vk_expires_at");
    if (!access) return false;
    const expiresAt = Number(expiresAtRaw || 0);
    if (expiresAt && Date.now() >= expiresAt - 30000) {
      this.clearTokens();
      return false;
    }
    return true;
  },

  requireLogin(redirectUrl = "/login/") {
    if (this.isLoggedIn()) return true;
    window.location.href = redirectUrl;
    return false;
  },

  authHeader() {
    const t = localStorage.getItem("vk_access");
    return t ? { "Authorization": "Bearer " + t } : {};
  },

  async request(path, opts = {}) {
    const headers = {
      "Content-Type": "application/json",
      ...this.authHeader(),
      ...(opts.headers || {})
    };
    const res = await fetch(this.apiBase + path, { ...opts, headers });
    let data = null;
    const ct = res.headers.get("content-type") || "";
    if (ct.includes("application/json")) {
      data = await res.json();
    } else {
      data = await res.text();
    }
    if (!res.ok) {
      const err = new Error((data && data.detail) || ("HTTP " + res.status));
      err.status = res.status;
      err.data = data;
      throw err;
    }
    return data;
  },

  async publicRequest(path, opts = {}) {
    const headers = {
      "Content-Type": "application/json",
      ...(opts.headers || {})
    };
    const res = await fetch(this.apiBase + path, { ...opts, headers });
    let data = null;
    const ct = res.headers.get("content-type") || "";
    if (ct.includes("application/json")) {
      data = await res.json();
    } else {
      data = await res.text();
    }
    if (!res.ok) {
      const err = new Error((data && data.detail) || ("HTTP " + res.status));
      err.status = res.status;
      err.data = data;
      throw err;
    }
    return data;
  },

  async register({ email, password, full_name, workspace_name, trial_tier = null }) {
    const t = await this.request("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, full_name, workspace_name, trial_tier })
    });
    this.saveTokens(t);
    return t;
  },

  async login({ email, password }) {
    const t = await this.request("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password })
    });
    this.saveTokens(t);
    return t;
  },

  async getGithubAuthUrl() {
    return this.request("/auth/github/login", { method: "GET" });
  },

  async startGithubLogin() {
    let out;
    try {
      out = await this.getGithubAuthUrl();
    } catch (err) {
      if (err && err.status === 503) {
        throw new Error("GitHub sign-in is not configured on the server.");
      }
      throw err;
    }
    if (!out || !out.auth_url || !out.state) {
      throw new Error("GitHub OAuth initialization failed");
    }
    sessionStorage.setItem("vk_github_oauth_state", out.state);
    window.location.href = out.auth_url;
  },

  async finishGithubLogin({ code, state }) {
    const expectedState = sessionStorage.getItem("vk_github_oauth_state");
    if (!expectedState || expectedState !== state) {
      throw new Error("OAuth state mismatch. Please try again.");
    }
    sessionStorage.removeItem("vk_github_oauth_state");
    const t = await this.request(
      "/auth/github/callback?code=" + encodeURIComponent(code) + "&state=" + encodeURIComponent(state),
      { method: "POST" }
    );
    this.saveTokens(t);
    return t;
  },

  async me() {
    return this.request("/auth/me");
  },

  async listApiKeys() {
    return this.request("/auth/api-keys");
  },

  async createApiKey({ name, scopes = ["read", "write"] } = {}) {
    return this.request("/auth/api-keys", {
      method: "POST",
      body: JSON.stringify({ name: name || "default", scopes })
    });
  },

  async revokeApiKey(id) {
    return this.request("/auth/api-keys/" + encodeURIComponent(id), { method: "DELETE" });
  },

  async getCurrentSubscription() {
    return this.request("/subscriptions/current");
  },

  async workspaceOverview() {
    return this.request("/workspace/overview");
  },

  async workspaceObservability(params = {}) {
    const qs = new URLSearchParams();
    if (params.model) qs.set("model", params.model);
    if (params.status) qs.set("status", params.status);
    if (params.days) qs.set("days", String(params.days));
    if (params.limit) qs.set("limit", String(params.limit));
    if (params.offset) qs.set("offset", String(params.offset));
    const suffix = qs.toString() ? ("?" + qs.toString()) : "";
    return this.request("/workspace/observability" + suffix, { method: "GET" });
  },

  async workspaceApiKeys() {
    return this.request("/workspace/api-keys");
  },

  async workspaceModels() {
    return this.request("/workspace/models");
  },

  async workspaceToggleModel(model_slug, enabled) {
    return this.request("/workspace/models/" + encodeURIComponent(model_slug), {
      method: "PATCH",
      body: JSON.stringify({ enabled: !!enabled })
    });
  },

  async workspaceCostBudget() {
    return this.request("/workspace/cost-budget");
  },

  async workspaceBudget() {
    return this.request("/workspace/budget");
  },

  async workspaceBudgetUpdate(payload) {
    return this.request("/workspace/budget", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  },

  async workspaceCostCsv() {
    return this.request("/workspace/cost-budget.csv", { method: "GET" });
  },

  async getWalletBalance() {
    return this.request("/wallet/balance");
  },

  async aiComplete({ model, prompt, max_tokens = 512 }) {
    return this.request("/ai/complete", {
      method: "POST",
      body: JSON.stringify({ model, prompt, max_tokens })
    });
  },

  async getGithubRepos() {
    return this.request("/auth/github/repos");
  },

  async marketplaceList(status_filter = null) {
    const qs = status_filter ? ("?status_filter=" + encodeURIComponent(status_filter)) : "";
    return this.request("/listings" + qs, { method: "GET" });
  },

  async marketplaceCreateVendor({ display_name }) {
    return this.request("/vendors/create", {
      method: "POST",
      body: JSON.stringify({ display_name })
    });
  },

  async marketplaceCreateListing({ title, description = "", price_cents = 0, currency = "usd" }) {
    return this.request("/listings/create", {
      method: "POST",
      body: JSON.stringify({ title, description, price_cents, currency })
    });
  },

  async marketplaceSubmitListing({ listing_id }) {
    return this.request("/listings/submit", {
      method: "POST",
      body: JSON.stringify({ listing_id })
    });
  },

  async marketplaceMyListings() {
    return this.request("/vendors/me/listings", { method: "GET" });
  },

  async marketplaceGetUploadUrl({ listing_id, file_name, file_type = null }) {
    return this.request("/files/upload-url", {
      method: "POST",
      body: JSON.stringify({ listing_id, file_name, file_type })
    });
  },

  async marketplaceConfirmFile({ listing_id, s3_key, size = null, checksum = null, file_type = null }) {
    return this.request("/files/confirm", {
      method: "POST",
      body: JSON.stringify({ listing_id, s3_key, size, checksum, file_type })
    });
  },

  async marketplaceCreateOrder({ items }) {
    return this.request("/orders/create", {
      method: "POST",
      body: JSON.stringify({ items })
    });
  },

  async marketplaceCreateCheckout({ order_id, success_url = null, cancel_url = null }) {
    return this.request("/payments/create-checkout", {
      method: "POST",
      body: JSON.stringify({ order_id, success_url, cancel_url })
    });
  },

  async createCheckout({ plan, billing_cycle = "monthly", success_url = null, cancel_url = null }) {
    return this.request("/subscriptions/checkout", {
      method: "POST",
      body: JSON.stringify({
        plan,
        billing_cycle,
        success_url: success_url || (window.location.origin + "/dashboard/?checkout=success"),
        cancel_url: cancel_url || (window.location.origin + "/dashboard/?checkout=cancel")
      })
    });
  },

  async logout() {
    try { await this.request("/auth/logout", { method: "POST" }); } catch (_) {}
    this.clearTokens();
    window.location.href = "/";
  }
};

window.VK = VK;
