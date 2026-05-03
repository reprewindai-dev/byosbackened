(() => {
  const host = window.location.hostname || "";
  const apiRoot = (
    window.__VEKLOM_API_BASE__ ||
    (host.endsWith(".veklom.dev") ? "https://api.veklom.dev" : "https://api.veklom.com")
  ).replace(/\/api\/v1\/?$/, "").replace(/\/+$/, "");
  const apiBase = `${apiRoot}/api/v1`;

  const token = () => {
    try {
      return localStorage.getItem("vk_access") || "";
    } catch {
      return "";
    }
  };

  const authHeaders = () => {
    const access = token();
    return access ? { Authorization: `Bearer ${access}` } : {};
  };

  const originalFetch = window.fetch.bind(window);
  window.fetch = (input, init = {}) => {
    const url = typeof input === "string" ? input : input && input.url;
    const shouldAuthorize = !!url && (
      url.startsWith(apiBase) ||
      url.startsWith(`${apiRoot}/api/v1`) ||
      url.startsWith("/api/v1/")
    );
    let nextInit = init;
    if (url && url.includes("/api/v1/ai/complete") && init && init.body) {
      try {
        const payload = JSON.parse(init.body);
        const models = (window.__VEKLOM_WORKSPACE_STATE__ && window.__VEKLOM_WORKSPACE_STATE__.models) || [];
        const connected = models.find((model) => model.enabled && model.connected);
        if (connected && payload && payload.model && !models.some((model) => model.model_slug === payload.model)) {
          nextInit = { ...init, body: JSON.stringify({ ...payload, model: connected.model_slug }) };
        }
      } catch {
        nextInit = init;
      }
    }
    if (!shouldAuthorize || !token()) {
      return originalFetch(input, nextInit);
    }
    const headers = new Headers(nextInit.headers || (typeof input !== "string" ? input.headers : undefined) || {});
    headers.set("Authorization", `Bearer ${token()}`);
    return originalFetch(input, { ...nextInit, headers });
  };

  const api = async (path, options = {}) => {
    const res = await originalFetch(`${apiBase}${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...authHeaders(),
        ...(options.headers || {}),
      },
    });
    const text = await res.text();
    const data = text ? JSON.parse(text) : null;
    if (!res.ok) {
      const error = new Error((data && data.detail) || `HTTP ${res.status}`);
      error.status = res.status;
      throw error;
    }
    return data;
  };

  const safe = (value, fallback = "") => value === null || value === undefined || value === "" ? fallback : String(value);
  const initials = (name, email) => {
    const basis = (name || email || "Veklom User").trim();
    const parts = basis.includes("@") ? basis.split("@")[0].split(/[._-]+/) : basis.split(/\s+/);
    return parts.filter(Boolean).slice(0, 2).map((part) => part[0].toUpperCase()).join("") || "VU";
  };

  const replaceText = (root, replacements) => {
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode(node) {
        if (!node.nodeValue || !node.nodeValue.trim()) return NodeFilter.FILTER_REJECT;
        const parent = node.parentElement;
        if (!parent || ["SCRIPT", "STYLE", "TEXTAREA", "INPUT"].includes(parent.tagName)) {
          return NodeFilter.FILTER_REJECT;
        }
        return NodeFilter.FILTER_ACCEPT;
      },
    });
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    for (const node of nodes) {
      let next = node.nodeValue;
      for (const [from, to] of replacements) {
        next = next.split(from).join(to);
      }
      if (next !== node.nodeValue) node.nodeValue = next;
    }
  };

  const setInputPlaceholders = (workspaceName) => {
    for (const input of document.querySelectorAll("input[placeholder]")) {
      const p = input.getAttribute("placeholder") || "";
      if (p.includes("Jump to model")) {
        input.setAttribute("placeholder", `Search ${workspaceName}: models, repos, logs, API keys...`);
      }
    }
  };

  const injectStatus = (state) => {
    let el = document.getElementById("veklom-live-workspace-status");
    if (!el) {
      el = document.createElement("div");
      el.id = "veklom-live-workspace-status";
      el.style.cssText = "position:fixed;right:14px;bottom:14px;z-index:80;max-width:360px;border:1px solid rgba(148,163,184,.25);background:rgba(2,6,23,.88);backdrop-filter:blur(12px);color:#e5e7eb;border-radius:10px;padding:10px 12px;font:12px/1.35 ui-monospace,SFMono-Regular,Menlo,monospace;box-shadow:0 18px 40px rgba(0,0,0,.35)";
      document.body.appendChild(el);
    }
    const repos = state.repos ? `${state.repos.length} repos` : "repos protected";
    const wallet = state.wallet && typeof state.wallet.balance !== "undefined" ? `${state.wallet.balance} credits` : "wallet protected";
    const models = state.models ? `${state.models.length} models` : "models protected";
    el.innerHTML = `
      <div style="display:flex;align-items:center;gap:7px;margin-bottom:4px;">
        <span style="width:7px;height:7px;border-radius:999px;background:#22c55e;display:inline-block"></span>
        <strong>Live tenant connected</strong>
      </div>
      <div>${state.workspaceName} - ${safe(state.userEmail, "authenticated user")}</div>
      <div style="color:#94a3b8;margin-top:2px;">${repos} - ${models} - ${wallet}</div>
    `;
  };

  const fmtMoney = (value) => `$${Number(value || 0).toFixed(6)}`;
  const fmtInt = (value) => Number(value || 0).toLocaleString();

  const routeName = () => {
    const hash = location.hash || "";
    const path = location.pathname || "";
    if (hash.includes("/playground") || path.startsWith("/playground")) return "playground";
    if (hash.includes("/marketplace") || path.startsWith("/marketplace")) return "marketplace";
    if (hash.includes("/billing") || path.startsWith("/billing")) return "billing";
    if (hash.includes("/models") || path.startsWith("/models")) return "models";
    if (hash.includes("/monitoring") || path.startsWith("/monitoring")) return "monitoring";
    return "dashboard";
  };

  const liveCard = (label, value, sub = "") => `
    <div style="border:1px solid rgba(148,163,184,.18);background:rgba(15,23,42,.52);border-radius:10px;padding:12px;">
      <div style="color:#94a3b8;font:10px/1.2 ui-monospace,SFMono-Regular,Menlo,monospace;text-transform:uppercase;letter-spacing:.14em">${label}</div>
      <div style="margin-top:6px;color:#f8fafc;font:600 20px/1.1 ui-sans-serif,system-ui">${value}</div>
      ${sub ? `<div style="margin-top:4px;color:#94a3b8;font:12px/1.35 ui-sans-serif,system-ui">${sub}</div>` : ""}
    </div>
  `;

  const emptyState = (text) => `
    <div style="border:1px dashed rgba(148,163,184,.25);border-radius:10px;padding:14px;color:#94a3b8;font:13px/1.5 ui-sans-serif,system-ui">
      ${text}
    </div>
  `;

  const renderTruthPanel = (state) => {
    const root = document.getElementById("root");
    if (!root) return;
    let panel = document.getElementById("veklom-live-route-panel");
    if (!panel) {
      panel = document.createElement("section");
      panel.id = "veklom-live-route-panel";
      panel.style.cssText = "max-width:1400px;margin:16px auto 0;padding:0 24px;position:relative;z-index:15";
      const header = root.querySelector("header");
      if (header && header.parentElement) {
        header.parentElement.insertBefore(panel, header.nextSibling);
      } else {
        root.prepend(panel);
      }
    }
    const route = routeName();
    const overview = state.overview || {};
    const wallet = state.wallet || {};
    const cost = state.costBudget || {};
    const models = state.models || [];
    const repos = state.repos || [];
    const recent = (state.observability && state.observability.rows) || overview.live_feed || [];
    const listings = state.marketplaceListings || [];
    const connectedModels = models.filter((model) => model.connected);
    const enabledModels = models.filter((model) => model.enabled);
    let title = "Live workspace state";
    let body = "";

    if (!token()) {
      title = "Workspace requires sign in";
      body = emptyState("This workspace is protected. Sign in to load tenant-scoped dashboard, wallet, model, repo, and playground data.");
    } else if (route === "playground") {
      title = "Playground readiness";
      body = `
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px">
          ${liveCard("Authenticated", "yes", safe(state.userEmail, "active session"))}
          ${liveCard("Model route", connectedModels[0] ? connectedModels[0].model_slug : "none", connectedModels[0] ? connectedModels[0].display_name : "No connected runtime model")}
          ${liveCard("Wallet", fmtInt(wallet.balance), "credits available")}
          ${liveCard("Audit writes", "enabled", "/api/v1/ai/complete logs success")}
        </div>
        ${connectedModels.length ? "" : emptyState("No connected model is available. Playground calls will show the real backend error instead of fake output.")}
      `;
    } else if (route === "marketplace") {
      title = "Marketplace live catalog";
      body = `
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px">
          ${liveCard("Listings", fmtInt(listings.length), "from /api/v1/marketplace/listings")}
          ${liveCard("Products", listings.filter((item) => item.source_url).length, "source-verified")}
          ${liveCard("Paid checkout", "guarded", "shown only where backend supports it")}
          ${liveCard("GitHub repos", repos.length ? fmtInt(repos.length) : "none", state.githubConnected ? "connected account" : "connect GitHub to load repos")}
        </div>
      `;
    } else if (route === "billing") {
      title = "Billing and reserve truth";
      body = `
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px">
          ${liveCard("Wallet balance", fmtInt(wallet.balance), "live token reserve")}
          ${liveCard("Included", fmtInt(wallet.monthly_credits_included), "monthly credits")}
          ${liveCard("Used", fmtInt(wallet.monthly_credits_used || wallet.total_credits_used), "credits consumed")}
          ${liveCard("Plan", state.subscription ? state.subscription.plan : "free", state.subscription ? state.subscription.status : "live subscription endpoint")}
        </div>
      `;
    } else if (route === "models") {
      title = "Model catalog truth";
      body = `
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px">
          ${liveCard("Models", fmtInt(models.length), "workspace-scoped")}
          ${liveCard("Connected", fmtInt(connectedModels.length), "runtime health checked")}
          ${liveCard("Enabled", fmtInt(enabledModels.length), "allowed for playground")}
          ${liveCard("Primary", connectedModels[0] ? connectedModels[0].provider : "none", connectedModels[0] ? connectedModels[0].bedrock_model_id : "No model connected")}
        </div>
      `;
    } else {
      title = "Dashboard live backend state";
      body = `
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px">
          ${liveCard("API calls", fmtInt(overview.total_api_calls), "this workspace / month")}
          ${liveCard("Tokens", fmtInt(overview.total_tokens_used), "live usage logs")}
          ${liveCard("Cost", fmtMoney(overview.total_cost_usd || cost.total_cost_usd), "calculated from logs")}
          ${liveCard("Wallet", fmtInt(wallet.balance), "credits available")}
        </div>
        <div style="margin-top:12px">
          ${recent.length ? `
            <div style="overflow:auto;border:1px solid rgba(148,163,184,.18);border-radius:10px">
              <table style="width:100%;border-collapse:collapse;font:12px/1.35 ui-monospace,SFMono-Regular,Menlo,monospace;color:#cbd5e1">
                <thead><tr style="color:#94a3b8;text-align:left"><th style="padding:9px">Time</th><th>Kind</th><th>Model</th><th>Status</th><th>Tokens</th></tr></thead>
                <tbody>${recent.slice(0, 6).map((row) => `
                  <tr style="border-top:1px solid rgba(148,163,184,.12)">
                    <td style="padding:9px">${safe(row.created_at || row.timestamp, "-")}</td>
                    <td>${safe(row.kind || row.request_kind, "-")}</td>
                    <td>${safe(row.model, "-")}</td>
                    <td>${safe(row.status, "-")}</td>
                    <td>${fmtInt(row.tokens || row.tokens_out || row.tokens_in)}</td>
                  </tr>
                `).join("")}</tbody>
              </table>
            </div>
          ` : emptyState("No live runs yet for this workspace. Charts and history will populate after the first authenticated Playground/API call.")}
        </div>
      `;
    }

    panel.innerHTML = `
      <div style="border:1px solid rgba(34,197,94,.22);background:linear-gradient(135deg,rgba(2,6,23,.94),rgba(15,23,42,.88));box-shadow:0 18px 50px rgba(0,0,0,.32);border-radius:14px;padding:14px">
        <div style="display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:10px">
          <div>
            <div style="color:#22c55e;font:10px/1.2 ui-monospace,SFMono-Regular,Menlo,monospace;text-transform:uppercase;letter-spacing:.16em">Live backend truth layer</div>
            <div style="color:#f8fafc;font:700 17px/1.25 ui-sans-serif,system-ui;margin-top:3px">${title}</div>
          </div>
          <div style="color:#94a3b8;font:11px/1.35 ui-monospace,SFMono-Regular,Menlo,monospace;text-align:right">${safe(state.workspaceName, "workspace")}<br>${safe(state.userEmail, "signed out")}</div>
        </div>
        ${body}
      </div>
    `;
  };

  const applyState = (state) => {
    const name = safe(state.fullName, state.githubUsername || state.userEmail || "Veklom User");
    const email = safe(state.userEmail, "user@veklom.com");
    const workspace = safe(state.workspaceName, "Veklom Workspace");
    const slug = safe(state.workspaceSlug, workspace.toLowerCase().replace(/[^a-z0-9]+/g, "-"));
    const init = initials(name, email);
    const shortName = name.includes(" ") ? name.split(/\s+/).slice(0, 2).join(" ") : name;
    const connected = state.githubConnected ? `GitHub - ${state.githubUsername}` : "GitHub - connect";

    replaceText(document.body, [
      ["Elliot Jurić", name],
      ["Elliot J.", shortName],
      ["EJ", init],
      ["elliot@acme.io", email],
      ["kira@acme.io", email],
      ["alex@acme.io", email],
      ["sara@acme.io", email],
      ["tomas@acme.io", email],
      ["lin@acme.io", email],
      ["Kira Bansal", name],
      ["Alex Tran", name],
      ["Sara Olin", name],
      ["Tomás Reyes", name],
      ["Lin Park", name],
      ["acme-prod", workspace],
      ["acme.veklom.app", `${slug}.veklom.app`],
      ["Okta · active", connected],
      ["GitHub · enabled", state.githubConnected ? connected : "GitHub - available"],
    ]);
    setInputPlaceholders(workspace);
    injectStatus(state);
    wireVisibleActions();
  };

  const showActionNotice = (message, tone = "info") => {
    let el = document.getElementById("veklom-action-truth-notice");
    if (!el) {
      el = document.createElement("div");
      el.id = "veklom-action-truth-notice";
      el.style.cssText = "position:fixed;left:14px;bottom:14px;z-index:90;max-width:420px;border:1px solid rgba(148,163,184,.25);background:rgba(2,6,23,.92);color:#e5e7eb;border-radius:10px;padding:10px 12px;font:12px/1.45 ui-sans-serif,system-ui;box-shadow:0 18px 40px rgba(0,0,0,.35)";
      document.body.appendChild(el);
    }
    el.style.borderColor = tone === "warn" ? "rgba(245,158,11,.45)" : tone === "error" ? "rgba(239,68,68,.45)" : "rgba(34,197,94,.35)";
    el.textContent = message;
    window.clearTimeout(showActionNotice._timer);
    showActionNotice._timer = window.setTimeout(() => {
      if (el) el.remove();
    }, 5200);
  };

  const visibleText = (el) => (el.innerText || el.textContent || "").replace(/\s+/g, " ").trim();

  const setButtonUnavailable = (el, reason) => {
    el.dataset.veklomActionTruth = "disabled";
    el.setAttribute("aria-disabled", "true");
    el.setAttribute("title", reason);
    el.style.opacity = "0.58";
    el.style.cursor = "not-allowed";
    el.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      showActionNotice(reason, "warn");
    }, true);
  };

  const wireButton = (el, handler, title = "Live action") => {
    el.dataset.veklomActionTruth = "wired";
    el.setAttribute("title", title);
    el.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      handler();
    }, true);
  };

  const sourceForCurrentMarketplaceItem = () => {
    const state = window.__VEKLOM_WORKSPACE_STATE__ || {};
    const slug = (location.hash.split("/marketplace/")[1] || location.pathname.split("/marketplace/")[1] || "").replace(/^\/+|\/+$/g, "");
    if (!slug) return null;
    const item = (state.marketplaceListings || []).find((listing) => listing.id === slug);
    return item && (item.use_url || item.source_url);
  };

  const connectGithub = async () => {
    try {
      const out = await api("/auth/github/login");
      if (!out || !out.auth_url) throw new Error("GitHub OAuth did not return an auth URL");
      if (out.state) sessionStorage.setItem("vk_github_oauth_state", out.state);
      location.href = out.auth_url;
    } catch (error) {
      showActionNotice(error.message || "GitHub OAuth is not available", "error");
    }
  };

  const wireVisibleActions = () => {
    const unavailable = new Map([
      ["New deployment", "Deployment creation is not available in the current stabilized shell. Existing model/runtime state is live."],
      ["Deploy first model", "One-click deployment is not enabled in this shell yet. Runtime models are read from the live backend."],
      ["SSO settings", "SSO administration is not self-serve in this shell yet."],
      ["Invite member", "Team invitations are not enabled in this shell yet."],
      ["Pause all deployments", "Global deployment pause is not exposed in this shell yet."],
      ["Pause", "This destructive control is disabled in the public workspace shell."],
      ["Rotate workspace secrets", "Secret rotation is not exposed in this shell yet."],
      ["Rotate", "Secret/key rotation is disabled unless a backend-backed row action is present."],
      ["Export", "Export requires a backend-backed export endpoint for this panel; no fake export generated."],
      ["Create listing", "Use the Vendor Console for listing creation; this compiled marketplace card is read-only."],
      ["Create Draft", "Use the Vendor Console authenticated flow for listing creation."],
      ["Save Vendor Profile", "Use the Vendor Console authenticated flow for vendor profile updates."],
    ]);

    for (const el of document.querySelectorAll("button, a[role='button']")) {
      if (el.dataset.veklomActionTruth) continue;
      const text = visibleText(el);
      if (!text) continue;

      if (text === "Open Playground") {
        wireButton(el, () => { location.href = "/playground/"; }, "Open the real playground route");
      } else if (text === "Sign out") {
        wireButton(el, () => {
          localStorage.removeItem("vk_access");
          localStorage.removeItem("vk_refresh");
          localStorage.removeItem("vk_expires_at");
          location.href = "/login/";
        }, "Sign out of this browser session");
      } else if (text.includes("Connect GitHub") || text === "GitHub - connect" || text === "GitHub · connect") {
        wireButton(el, connectGithub, "Start real GitHub OAuth");
      } else if (["Install", "Use now", "Docs"].includes(text)) {
        wireButton(el, () => {
          const url = sourceForCurrentMarketplaceItem();
          if (url) {
            window.open(url, "_blank", "noopener,noreferrer");
          } else {
            showActionNotice("No source URL is available for this listing.", "warn");
          }
        }, "Open the real source/use URL for this listing");
      } else if (unavailable.has(text)) {
        setButtonUnavailable(el, unavailable.get(text));
      }
    }
  };

  const loadLiveState = async () => {
    if (!token()) {
      injectStatus({ workspaceName: "Signed out", userEmail: "login required" });
      return;
    }
    const state = {};
    const me = await api("/auth/me");
    state.fullName = me.full_name;
    state.userEmail = me.email;
    state.workspaceName = me.workspace_name || "Veklom Workspace";
    state.workspaceSlug = me.workspace_slug;
    state.licenseTier = me.license_tier;

    const optionalCalls = await Promise.allSettled([
      api("/auth/connected-accounts"),
      api("/workspace/overview"),
      api("/workspace/observability?limit=25&days=30"),
      api("/workspace/cost-budget"),
      api("/workspace/models"),
      api("/workspace/api-keys"),
      api("/wallet/balance"),
      api("/subscriptions/current"),
      api("/auth/github/repos"),
      api("/marketplace/listings"),
    ]);
    const [connected, overview, observability, costBudget, models, keys, wallet, subscription, repos, marketplaceListings] = optionalCalls;
    if (connected.status === "fulfilled") {
      state.githubConnected = !!connected.value.github_connected;
      state.githubUsername = connected.value.github_username;
    }
    if (overview.status === "fulfilled") state.overview = overview.value;
    if (observability.status === "fulfilled") state.observability = observability.value;
    if (costBudget.status === "fulfilled") state.costBudget = costBudget.value;
    if (models.status === "fulfilled") state.models = models.value.models || [];
    if (keys.status === "fulfilled") state.apiKeys = keys.value.keys || [];
    if (wallet.status === "fulfilled") state.wallet = wallet.value;
    if (subscription.status === "fulfilled") state.subscription = subscription.value;
    if (repos.status === "fulfilled") state.repos = repos.value.repos || [];
    if (marketplaceListings.status === "fulfilled") state.marketplaceListings = marketplaceListings.value || [];
    window.__VEKLOM_WORKSPACE_STATE__ = state;
    applyState(state);
    renderTruthPanel(state);
  };

  let lastPath = "";
  const scheduleApply = () => {
    const state = window.__VEKLOM_WORKSPACE_STATE__;
    if (state) {
      applyState(state);
      renderTruthPanel(state);
      wireVisibleActions();
    }
    if (lastPath !== location.hash + location.pathname) {
      lastPath = location.hash + location.pathname;
      setTimeout(() => state && (applyState(state), renderTruthPanel(state), wireVisibleActions()), 150);
      setTimeout(() => state && (applyState(state), renderTruthPanel(state), wireVisibleActions()), 600);
    }
  };

  const start = () => {
    loadLiveState().catch((error) => {
      const status = error.status === 401 ? "Signed out" : "Live state degraded";
      injectStatus({ workspaceName: status, userEmail: error.message || "backend unavailable" });
    });
    const observer = new MutationObserver(scheduleApply);
    observer.observe(document.body, { childList: true, subtree: true });
    window.addEventListener("hashchange", scheduleApply);
    wireVisibleActions();
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, { once: true });
  } else {
    start();
  }
})();
