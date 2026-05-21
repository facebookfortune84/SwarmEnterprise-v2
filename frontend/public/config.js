// API base — override per environment (baked at deploy or via query ?api=)
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
})();
