(() => {
  const host = window.location.hostname || "";
  const backendBase = host.endsWith(".veklom.dev")
    ? "https://api.veklom.dev"
    : "https://api.veklom.com";
  window.__UACP_BACKEND_BASE_URL__ = backendBase;
  window.__VEKLOM_API_BASE__ = backendBase;
})();
