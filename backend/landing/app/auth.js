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
    return !!localStorage.getItem("vk_access");
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

  async register({ email, password, full_name, workspace_name }) {
    const t = await this.request("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, full_name, workspace_name })
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
    const out = await this.getGithubAuthUrl();
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

  async createCheckout({ plan, billing_cycle = "monthly" }) {
    return this.request("/subscriptions/checkout", {
      method: "POST",
      body: JSON.stringify({
        plan,
        billing_cycle,
        success_url: window.location.origin + "/dashboard/?checkout=success",
        cancel_url: window.location.origin + "/dashboard/?checkout=cancel"
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
