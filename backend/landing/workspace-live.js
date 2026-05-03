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
    if (!shouldAuthorize || !token()) {
      return originalFetch(input, init);
    }
    const headers = new Headers(init.headers || (typeof input !== "string" ? input.headers : undefined) || {});
    headers.set("Authorization", `Bearer ${token()}`);
    return originalFetch(input, { ...init, headers });
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
      <div>${state.workspaceName} · ${safe(state.userEmail, "authenticated user")}</div>
      <div style="color:#94a3b8;margin-top:2px;">${repos} · ${models} · ${wallet}</div>
    `;
  };

  const applyState = (state) => {
    const name = safe(state.fullName, state.githubUsername || state.userEmail || "Veklom User");
    const email = safe(state.userEmail, "user@veklom.com");
    const workspace = safe(state.workspaceName, "Veklom Workspace");
    const slug = safe(state.workspaceSlug, workspace.toLowerCase().replace(/[^a-z0-9]+/g, "-"));
    const init = initials(name, email);
    const shortName = name.includes(" ") ? name.split(/\s+/).slice(0, 2).join(" ") : name;
    const connected = state.githubConnected ? `GitHub · ${state.githubUsername}` : "GitHub · connect";

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
      ["GitHub · enabled", state.githubConnected ? connected : "GitHub · available"],
    ]);
    setInputPlaceholders(workspace);
    injectStatus(state);
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
      api("/workspace/models"),
      api("/workspace/api-keys"),
      api("/wallet/balance"),
      api("/subscriptions/current"),
      api("/auth/github/repos"),
    ]);
    const [connected, models, keys, wallet, subscription, repos] = optionalCalls;
    if (connected.status === "fulfilled") {
      state.githubConnected = !!connected.value.github_connected;
      state.githubUsername = connected.value.github_username;
    }
    if (models.status === "fulfilled") state.models = models.value.models || [];
    if (keys.status === "fulfilled") state.apiKeys = keys.value.keys || [];
    if (wallet.status === "fulfilled") state.wallet = wallet.value;
    if (subscription.status === "fulfilled") state.subscription = subscription.value;
    if (repos.status === "fulfilled") state.repos = repos.value.repos || [];
    window.__VEKLOM_WORKSPACE_STATE__ = state;
    applyState(state);
  };

  let lastPath = "";
  const scheduleApply = () => {
    const state = window.__VEKLOM_WORKSPACE_STATE__;
    if (state) applyState(state);
    if (lastPath !== location.hash + location.pathname) {
      lastPath = location.hash + location.pathname;
      setTimeout(() => state && applyState(state), 150);
      setTimeout(() => state && applyState(state), 600);
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
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, { once: true });
  } else {
    start();
  }
})();
