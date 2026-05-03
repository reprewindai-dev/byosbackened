(() => {
  const host = window.location.hostname || "";
  window.__VEKLOM_API_BASE__ = host.endsWith(".veklom.dev")
    ? "https://api.veklom.dev/api/v1"
    : "https://api.veklom.com/api/v1";
})();
