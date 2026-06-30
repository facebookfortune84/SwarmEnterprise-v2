// API base — override per environment (baked at deploy or via query ?api=)
// Analytics — set ANALYTICS_URL and ANALYTICS_SITE_ID in environment
(function () {
  const params = new URLSearchParams(window.location.search);
  const override = params.get("api");
  const host = window.location.hostname;
  let base = "";
  if (override) {
    base = override.replace(/\/$/, "");
  } else if (host === "corp.realms2riches.com") {
    base = "https://api.realms2riches.com";
  } else if (host.endsWith("realms2riches.tech")) {
    base = "https://api.realms2riches.com";
  } else if (host === "localhost" || host === "127.0.0.1") {
    base = "http://localhost:8000";
  } else {
    base = window.location.origin.includes("8000")
      ? window.location.origin
      : "https://api.realms2riches.com";
  }
  window.SWARM_API_BASE = base;

  // ── Analytics configuration ─────────────────────────────────────────────
  // These are injected at build time or set here for self-hosted Umami.
  // SWARM_ANALYTICS_URL:     URL of the Umami instance (e.g. http://localhost:3001)
  // SWARM_ANALYTICS_SITE_ID: Umami website ID (UUID from Umami admin dashboard)
  window.SWARM_ANALYTICS_URL     = window.SWARM_ANALYTICS_URL     || "";
  window.SWARM_ANALYTICS_SITE_ID = window.SWARM_ANALYTICS_SITE_ID || "";

  window.SWARM_DOMAIN_CONFIG = {
    landing: "realms2riches.com",
    corp: "corp.realms2riches.com",
    dedicated: "realms2riches.tech",
    hostingNote: "Dedicated deployments and company hosting are available on realms2riches.tech for an additional cost.",
  };
})();
