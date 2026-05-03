(() => {
  const host = window.location.hostname || "";
  window.__VEKLOM_API_BASE__ = host.endsWith(".veklom.dev")
    ? "https://api.veklom.dev"
    : "https://api.veklom.com";
})();
