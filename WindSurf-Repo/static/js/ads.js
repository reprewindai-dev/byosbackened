/**
 * GoonVault — Ad Configuration
 * ─────────────────────────────────────────────────────────────────────────────
 * Paste your ad network zone IDs here after you're approved.
 * ExoClick: https://www.exoclick.com (sign up → Publisher → Add Zone)
 * TrafficJunky: https://www.trafficjunky.com
 * JuicyAds: https://www.juicyads.com
 *
 * To disable a slot, set enabled: false
 * ─────────────────────────────────────────────────────────────────────────────
 */

window.GV_ADS = {

  // ── Your ExoClick Publisher ID (from dashboard after signup) ──────────────
  exoclick: {
    enabled: false,          // ← flip to true once you have your zone IDs
    publisherId: "PASTE_YOUR_EXOCLICK_PUBLISHER_ID",

    zones: {
      // Leaderboard banner — 728x90 — appears below nav
      leaderboard: { id: "PASTE_ZONE_ID", width: 728, height: 90 },
      // Rectangle — 300x250 — sidebar / between content
      rectangle:   { id: "PASTE_ZONE_ID", width: 300, height: 250 },
      // Mobile banner — 300x100 — mobile only
      mobile:      { id: "PASTE_ZONE_ID", width: 300, height: 100 },
      // Sticky bottom — 320x50 — mobile sticky footer
      sticky:      { id: "PASTE_ZONE_ID", width: 320, height: 50  },
    }
  },

  // ── TrafficJunky (PornHub network) — higher CPM, harder to get in ─────────
  trafficjunky: {
    enabled: false,
    zones: {
      leaderboard: { id: "PASTE_ZONE_ID", width: 728, height: 90 },
      rectangle:   { id: "PASTE_ZONE_ID", width: 300, height: 250 },
    }
  },

  // ── JuicyAds — easy approval, good fallback ───────────────────────────────
  juicyads: {
    enabled: false,
    zones: {
      leaderboard: { id: "PASTE_ZONE_ID", width: 728, height: 90 },
      rectangle:   { id: "PASTE_ZONE_ID", width: 300, height: 250 },
    }
  },
};

// ── Ad renderer — call this from any page ────────────────────────────────────
window.GV_renderAd = function(slotType, containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;

  // Try networks in priority order
  const networks = ['exoclick', 'trafficjunky', 'juicyads'];
  for (const net of networks) {
    const cfg = window.GV_ADS[net];
    if (!cfg || !cfg.enabled) continue;
    const zone = cfg.zones?.[slotType];
    if (!zone || !zone.id || zone.id.startsWith('PASTE')) continue;

    if (net === 'exoclick') {
      container.innerHTML = `
        <div style="display:flex;justify-content:center;align-items:center;width:${zone.width}px;height:${zone.height}px;margin:0 auto">
          <script async src="//ads.exoclick.com/ads.js?zoneid=${zone.id}"><\/script>
          <ins class="adsbyexoclick" data-ad-zone-id="${zone.id}"></ins>
        </div>`;
    } else if (net === 'trafficjunky') {
      container.innerHTML = `
        <div id="tj-${zone.id}" style="width:${zone.width}px;height:${zone.height}px;margin:0 auto"></div>
        <script>new TrafficJunky({zoneid:'${zone.id}',target:'tj-${zone.id}'}).show();<\/script>`;
    } else if (net === 'juicyads') {
      container.innerHTML = `
        <script async src="https://static.juicyads.com/js/ja.js" data-zone="${zone.id}"><\/script>`;
    }
    container.style.display = 'flex';
    container.style.justifyContent = 'center';
    return;
  }

  // No network configured — hide the slot cleanly
  container.style.display = 'none';
};
