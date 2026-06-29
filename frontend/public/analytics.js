/**
 * SwarmOS — Umami analytics tracker
 * Loads the Umami script and tracks meaningful user interactions.
 * No data leaves the self-hosted instance.
 *
 * Configure via window.SWARM_ANALYTICS_URL and window.SWARM_ANALYTICS_SITE_ID,
 * which are set by config.js from environment variables.
 */
(function (global) {
  "use strict";

  // Read config from config.js runtime injection
  const ANALYTICS_URL = global.SWARM_ANALYTICS_URL || "";
  const SITE_ID = global.SWARM_ANALYTICS_SITE_ID || "";

  // Do not load if not configured
  if (!ANALYTICS_URL || !SITE_ID) return;

  // Inject the Umami tracking script
  const script = document.createElement("script");
  script.defer = true;
  script.async = true;
  script.setAttribute("data-website-id", SITE_ID);
  script.setAttribute("data-domains", global.location.hostname);
  script.setAttribute("data-cache", "true");
  // Umami auto-tracks pageviews; we add the script after page load
  script.src = ANALYTICS_URL.replace(/\/$/, "") + "/script.js";
  document.head.appendChild(script);

  // ── Event tracker helper ─────────────────────────────────────────────────
  function track(eventName, eventData) {
    // Use Umami's umami.track() API once the script has loaded
    if (typeof global.umami !== "undefined" && global.umami.track) {
      global.umami.track(eventName, eventData || {});
    }
  }

  // Expose globally so other scripts can call SwarmAnalytics.track(...)
  global.SwarmAnalytics = {
    track,
    /**
     * Track a page view (Umami auto-tracks these but this allows manual calls)
     */
    pageView(path) {
      track("pageview", { path: path || global.location.pathname });
    },
    /**
     * Track company generation initiated
     */
    companyGenerationStarted(techStack) {
      track("company_generation_started", { tech_stack: techStack });
    },
    /**
     * Track company generation completed
     */
    companyGenerationCompleted(companyId, techStack) {
      track("company_generation_completed", { company_id: companyId, tech_stack: techStack });
    },
    /**
     * Track deployment created
     */
    deploymentCreated(tenantName) {
      track("deployment_created", { tenant_name: tenantName });
    },
    /**
     * Track deployment status change
     */
    deploymentStatusChanged(deploymentId, newStatus) {
      track("deployment_status_changed", { deployment_id: deploymentId, status: newStatus });
    },
    /**
     * Track errors encountered
     */
    errorEncountered(context, errorMessage) {
      track("error_encountered", { context, error: String(errorMessage).slice(0, 200) });
    },
    /**
     * Track tenant registered
     */
    tenantRegistered(tenantName) {
      track("tenant_registered", { tenant_name: tenantName });
    },
    /**
     * Track user login
     */
    userLoggedIn() {
      track("user_login");
    },
    /**
     * Track build sprint initiated
     */
    buildSprintInitiated(techStack) {
      track("build_sprint_initiated", { tech_stack: techStack });
    },
  };
})(window);
