/**
 * SwarmOS API Client
 * Typed client with auth, error handling, and retry logic.
 * Reads base URL from window.SWARM_API_BASE (set by config.js).
 */
(function (global) {
  "use strict";

  // ── Token storage ─────────────────────────────────────────────────────────
  const _token = {
    get access() { return sessionStorage.getItem("swarm_access_token") || localStorage.getItem("swarm_access_token"); },
    get refresh() { return localStorage.getItem("swarm_refresh_token"); },
    setAccess(t) { sessionStorage.setItem("swarm_access_token", t); localStorage.setItem("swarm_access_token", t); },
    setRefresh(t) { localStorage.setItem("swarm_refresh_token", t); },
    clear() {
      sessionStorage.removeItem("swarm_access_token");
      localStorage.removeItem("swarm_access_token");
      localStorage.removeItem("swarm_refresh_token");
      localStorage.removeItem("swarm_user");
    },
    setUser(u) { localStorage.setItem("swarm_user", JSON.stringify(u)); },
    get user() { try { return JSON.parse(localStorage.getItem("swarm_user") || "null"); } catch { return null; } },
  };

  // ── Core fetch wrapper ────────────────────────────────────────────────────
  let _refreshPromise = null;

  async function _fetch(path, opts = {}, _retry = true) {
    const base = (global.SWARM_API_BASE || "").replace(/\/$/, "");
    const headers = { "Content-Type": "application/json", ...(opts.headers || {}) };
    if (_token.access) headers["Authorization"] = "Bearer " + _token.access;

    const resp = await fetch(base + path, { ...opts, headers });

    // Auto-refresh on 401
    if (resp.status === 401 && _retry && _token.refresh) {
      if (!_refreshPromise) {
        _refreshPromise = _fetch("/api/auth/refresh", {
          method: "POST",
          body: JSON.stringify({ refresh_token: _token.refresh }),
        }, false).then(d => {
          _token.setAccess(d.access_token);
          _refreshPromise = null;
        }).catch(() => {
          _token.clear();
          _refreshPromise = null;
          global.dispatchEvent(new CustomEvent("swarm:auth:expired"));
        });
      }
      await _refreshPromise;
      return _fetch(path, opts, false);
    }

    if (!resp.ok) {
      let detail = resp.statusText;
      try { const j = await resp.json(); detail = j.detail || j.message || detail; } catch {}
      const err = new Error(detail);
      err.status = resp.status;
      throw err;
    }

    if (resp.status === 204) return null;
    return resp.json().catch(() => null);
  }

  // ── Auth API ──────────────────────────────────────────────────────────────
  const auth = {
    async login(email, password) {
      const data = await _fetch("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      _token.setAccess(data.access_token);
      _token.setRefresh(data.refresh_token);
      _token.setUser(data.user);
      global.dispatchEvent(new CustomEvent("swarm:auth:login", { detail: data.user }));
      return data;
    },
    async logout() {
      try { await _fetch("/api/auth/logout", { method: "POST" }); } catch {}
      _token.clear();
      global.dispatchEvent(new CustomEvent("swarm:auth:logout"));
    },
    async register(email, password, full_name) {
      const data = await _fetch("/api/auth/register", {
        method: "POST",
        body: JSON.stringify({ email, password, full_name }),
      });
      _token.setAccess(data.access_token);
      _token.setRefresh(data.refresh_token);
      _token.setUser(data.user);
      return data;
    },
    async me() { return _fetch("/api/auth/me"); },
    isAuthenticated() { return !!_token.access; },
    currentUser() { return _token.user; },
  };

  // ── Companies API ─────────────────────────────────────────────────────────
  const companies = {
    async generate(name, description, tech_stack, features = []) {
      return _fetch("/api/companies/generate", {
        method: "POST",
        body: JSON.stringify({ name, description, tech_stack, features }),
      });
    },
    async list(skip = 0, limit = 100, status_filter = null) {
      const q = new URLSearchParams({ skip, limit });
      if (status_filter) q.set("status_filter", status_filter);
      return _fetch("/api/companies/?" + q);
    },
    async get(id) { return _fetch("/api/companies/" + id); },
    async status(id) { return _fetch("/api/companies/" + id + "/status"); },
    async download(id) { return _fetch("/api/companies/" + id + "/download"); },
    async metadata(id) { return _fetch("/api/companies/" + id + "/metadata"); },
    async delete(id) { return _fetch("/api/companies/" + id, { method: "DELETE" }); },
    async regenerate(id) { return _fetch("/api/companies/" + id + "/regenerate", { method: "POST" }); },
  };

  // ── Deployments API ───────────────────────────────────────────────────────
  const deployments = {
    async create(payload) {
      return _fetch("/api/deployments/", {
        method: "POST",
        body: JSON.stringify(payload),
      });
    },
    async list(status_filter = null) {
      const q = status_filter ? "?status_filter=" + status_filter : "";
      return _fetch("/api/deployments/" + q);
    },
    async get(id) { return _fetch("/api/deployments/" + id); },
    async start(id) { return _fetch("/api/deployments/" + id + "/start", { method: "POST" }); },
    async stop(id, force = false) {
      return _fetch("/api/deployments/" + id + "/stop?force=" + force, { method: "POST" });
    },
    async restart(id) { return _fetch("/api/deployments/" + id + "/restart", { method: "POST" }); },
    async delete(id, delete_vm = true) {
      return _fetch("/api/deployments/" + id + "?delete_vm=" + delete_vm, { method: "DELETE" });
    },
    async metrics(id) { return _fetch("/api/deployments/" + id + "/metrics"); },
    async backup(id) { return _fetch("/api/deployments/" + id + "/backup", { method: "POST" }); },
    async logs(id, lines = 100) { return _fetch("/api/deployments/" + id + "/logs?lines=" + lines); },
  };

  // ── Tenants API ───────────────────────────────────────────────────────────
  const tenants = {
    async register(name, slug = null) {
      return _fetch("/api/tenants/register", {
        method: "POST",
        body: JSON.stringify({ name, slug }),
      });
    },
    async list() { return _fetch("/api/tenants"); },
    async get(id) { return _fetch("/api/tenants/" + id); },
    async status(id) { return _fetch("/api/tenants/" + id + "/status"); },
    async provision(id, use_vm = false) {
      return _fetch("/api/tenants/" + id + "/provision", {
        method: "POST",
        body: JSON.stringify({ use_vm }),
      });
    },
  };

  // ── Notifications API ─────────────────────────────────────────────────────
  const notifications = {
    async list(skip = 0, limit = 50, unread_only = false) {
      const q = new URLSearchParams({ skip, limit, unread_only });
      return _fetch("/api/notifications?" + q);
    },
    async markRead(id) { return _fetch("/api/notifications/read/" + id, { method: "POST" }); },
    async markAllRead() { return _fetch("/api/notifications/read-all", { method: "POST" }); },
    async delete(id) { return _fetch("/api/notifications/" + id, { method: "DELETE" }); },
  };

  // ── Health API ────────────────────────────────────────────────────────────
  const health = {
    async check() { return _fetch("/health"); },
    async metrics() { return _fetch("/metrics"); },
    async opsStatus() { return _fetch("/api/ops/status"); },
  };

  // ── Ops API ───────────────────────────────────────────────────────────────
  const ops = {
    async status() { return _fetch("/api/ops/status"); },
    async heal() { return _fetch("/api/ops/heal", { method: "POST" }); },
  };

  // ── Build API ─────────────────────────────────────────────────────────────
  const build = {
    async trigger(name, description, stack) {
      return _fetch("/api/build", {
        method: "POST",
        body: JSON.stringify({ name, description, stack }),
      });
    },
  };

  // ── Outreach API ─────────────────────────────────────────────────────────
  const outreach = {
    async send(payload) {
      return _fetch("/api/outreach/", {
        method: "POST",
        body: JSON.stringify(payload),
      });
    },
    async campaign(payload) {
      return _fetch("/api/outreach/campaign", {
        method: "POST",
        body: JSON.stringify(payload),
      });
    },
  };

  // ── WebSocket Manager ─────────────────────────────────────────────────────
  class WSManager {
    constructor() {
      this._sockets = {};
      this._handlers = {};
      this._backoffs = {};
      this._stopped = {};
    }

    /**
     * Connect to a WS endpoint with auto-reconnect and exponential backoff.
     * @param {string} key  - unique key (e.g. "notifications:user-123")
     * @param {string} path - WS path (e.g. "/ws/notifications/user-123")
     * @param {Function} onMessage - callback(data)
     * @param {Function} [onStatus] - callback("connected"|"disconnected"|"reconnecting")
     */
    connect(key, path, onMessage, onStatus) {
      this._stopped[key] = false;
      this._handlers[key] = { onMessage, onStatus };
      this._doConnect(key, path);
    }

    _doConnect(key, path) {
      if (this._stopped[key]) return;
      const base = (global.SWARM_API_BASE || global.location.origin)
        .replace(/^http/, "ws").replace(/\/$/, "");
      const url = base + path;
      const ws = new WebSocket(url);
      this._sockets[key] = ws;
      const h = this._handlers[key] || {};

      ws.onopen = () => {
        this._backoffs[key] = 0;
        if (h.onStatus) h.onStatus("connected");
        // Heartbeat ping every 25 s
        ws._ping = setInterval(() => { if (ws.readyState === WebSocket.OPEN) ws.send("ping"); }, 25000);
      };

      ws.onmessage = (evt) => {
        if (evt.data === "pong") return;
        try {
          const data = JSON.parse(evt.data);
          if (h.onMessage) h.onMessage(data);
        } catch {
          if (h.onMessage) h.onMessage(evt.data);
        }
      };

      ws.onerror = () => {};
      ws.onclose = () => {
        clearInterval(ws._ping);
        if (this._stopped[key]) return;
        const delay = Math.min(1000 * Math.pow(2, this._backoffs[key] || 0), 30000);
        this._backoffs[key] = (this._backoffs[key] || 0) + 1;
        if (h.onStatus) h.onStatus("reconnecting");
        setTimeout(() => this._doConnect(key, path), delay);
      };
    }

    disconnect(key) {
      this._stopped[key] = true;
      const ws = this._sockets[key];
      if (ws) { clearInterval(ws._ping); ws.close(); }
      delete this._sockets[key];
    }

    disconnectAll() {
      Object.keys(this._sockets).forEach(k => this.disconnect(k));
    }
  }

  const wsManager = new WSManager();

  // ── Deployment status poller (WS + REST fallback) ─────────────────────────
  function watchDeployment(deploymentId, onUpdate, onStatus) {
    const key = "deploy:" + deploymentId;
    let wsConnected = false;

    wsManager.connect(
      key,
      "/ws/notifications/deployment-" + deploymentId,
      (data) => { wsConnected = true; onUpdate(data); },
      (s) => {
        if (s === "connected") wsConnected = true;
        if (onStatus) onStatus(s);
      }
    );

    // REST polling fallback — runs even if WS is alive (belt-and-suspenders)
    const pollInterval = setInterval(async () => {
      try {
        const d = await deployments.get(deploymentId);
        if (!wsConnected) onUpdate(d);
        if (d.status === "running" || d.status === "failed" || d.status === "deleted") {
          clearInterval(pollInterval);
          if (d.status !== "running") wsManager.disconnect(key);
        }
      } catch {}
    }, 5000);

    return () => { clearInterval(pollInterval); wsManager.disconnect(key); };
  }

  // ── Toast notification system ─────────────────────────────────────────────
  const toast = (() => {
    let container = null;
    function _ensureContainer() {
      if (!container) {
        container = document.createElement("div");
        container.id = "swarm-toast-container";
        container.style.cssText =
          "position:fixed;top:1rem;right:1rem;z-index:9999;display:flex;flex-direction:column;gap:0.5rem;max-width:360px;";
        document.body.appendChild(container);
      }
      return container;
    }
    function show(message, type = "info", duration = 4000) {
      const c = _ensureContainer();
      const colors = { success: "#166534", error: "#991b1b", info: "#1e3a5f", warning: "#713f12" };
      const borders = { success: "#22c55e", error: "#f87171", info: "#38bdf8", warning: "#fbbf24" };
      const el = document.createElement("div");
      el.style.cssText = `background:${colors[type]};border-left:3px solid ${borders[type]};color:#e2e8f0;
        padding:0.75rem 1rem;border-radius:6px;font-size:0.875rem;line-height:1.4;
        box-shadow:0 4px 12px rgba(0,0,0,0.4);opacity:1;transition:opacity 0.3s;cursor:pointer;`;
      el.textContent = message;
      el.onclick = () => el.remove();
      c.appendChild(el);
      setTimeout(() => { el.style.opacity = "0"; setTimeout(() => el.remove(), 300); }, duration);
    }
    return {
      success: (m, d) => show(m, "success", d),
      error: (m, d) => show(m, "error", d),
      info: (m, d) => show(m, "info", d),
      warning: (m, d) => show(m, "warning", d),
    };
  })();

  // ── Public API ────────────────────────────────────────────────────────────
  global.SwarmAPI = {
    auth,
    companies,
    deployments,
    tenants,
    notifications,
    health,
    ops,
    build,
    outreach,
    wsManager,
    watchDeployment,
    toast,
    _fetch,
    get token() { return _token; },
  };
})(window);
