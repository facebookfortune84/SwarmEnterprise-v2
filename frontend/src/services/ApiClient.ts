/**
 * SwarmOS API Client
 *
 * Features:
 * - Typed methods for all backend REST endpoints
 * - Auth header injection from authStore
 * - HTTP 429 retry with exponential back-off + jitter (base 1s, max 30s, max 5 retries)
 * - HTTP 401 interceptor: clear token + redirect to /login?redirect=<path>
 * - HTTP 403 interceptor: fire error Toast
 * - WebSocket subscription for the agent feed
 */

import toast from "react-hot-toast";
import { useAuthStore } from "@/store/authStore";
import type {
  AuthResponse,
  Company,
  CampaignRequest,
  CreateCompanyRequest,
  CreateDeploymentRequest,
  CreateSequenceRequest,
  DailyMetric,
  Deployment,
  HealthCheck,
  InboxReply,
  Lead,
  LoginRequest,
  Notification,
  PaginatedResponse,
  RegisterRequest,
  Sequence,
  SequenceEnrollment,
  Tenant,
  Ticket,
  TimelineEntry,
  UpdateProfileRequest,
  User,
  Workflow,
  AgentEvent,
} from "@/types/api";

// ── Base URL ─────────────────────────────────────────────────────────────────

const BASE_URL =
  (window as unknown as Record<string, string>)["SWARM_API_BASE"] || "http://localhost:8000";

// ── Low-level fetch with retry and interceptors ───────────────────────────────

async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
  retries = 0,
): Promise<T> {
  const store = useAuthStore.getState();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (store.token) {
    headers["Authorization"] = `Bearer ${store.token}`;
  }

  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}`, { ...options, headers });
  } catch (err) {
    throw new Error(`Network error: ${String(err)}`);
  }

  // HTTP 429 — exponential back-off with jitter
  if (response.status === 429 && retries < 5) {
    const delay = Math.min(1000 * Math.pow(2, retries), 30_000) + Math.random() * 1000;
    await new Promise((resolve) => setTimeout(resolve, delay));
    return apiFetch<T>(path, options, retries + 1);
  }

  // HTTP 401 — clear auth and redirect
  if (response.status === 401) {
    store.clearToken();
    const redirect = encodeURIComponent(window.location.pathname + window.location.search);
    setTimeout(() => {
      window.location.href = `/login?redirect=${redirect}`;
    }, 500);
    throw new Error("Session expired. Please sign in again.");
  }

  // HTTP 403 — show error toast
  if (response.status === 403) {
    toast.error("Access denied.");
    throw new Error("Forbidden");
  }

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const json = (await response.json()) as { detail?: string; message?: string };
      detail = json.detail ?? json.message ?? detail;
    } catch {
      // ignore JSON parse error
    }
    const error = new Error(detail);
    (error as Error & { status: number }).status = response.status;
    throw error;
  }

  if (response.status === 204) return null as T;
  return response.json() as Promise<T>;
}

// ── Auth ──────────────────────────────────────────────────────────────────────

const auth = {
  login: (payload: LoginRequest) =>
    apiFetch<AuthResponse>("/api/auth/login", { method: "POST", body: JSON.stringify(payload) }),

  register: (payload: RegisterRequest) =>
    apiFetch<AuthResponse>("/api/auth/register", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  logout: () => apiFetch<null>("/api/auth/logout", { method: "POST" }),

  me: () => apiFetch<User>("/api/auth/me"),

  refresh: (refreshToken: string) =>
    apiFetch<AuthResponse>("/api/auth/refresh", {
      method: "POST",
      body: JSON.stringify({ refresh_token: refreshToken }),
    }),
};

// ── Users ─────────────────────────────────────────────────────────────────────

const users = {
  updateProfile: (payload: UpdateProfileRequest) =>
    apiFetch<User>("/api/users/me", { method: "PUT", body: JSON.stringify(payload) }),

  listAll: () => apiFetch<User[]>("/api/admin/users"),

  toggleActive: (userId: string, isActive: boolean) =>
    apiFetch<User>(`/api/admin/users/${userId}`, {
      method: "PATCH",
      body: JSON.stringify({ is_active: isActive }),
    }),

  apiKeys: {
    list: () => apiFetch<unknown[]>("/api/users/me/api-keys"),
    create: (name: string, scope: string) =>
      apiFetch<unknown>("/api/users/me/api-keys", {
        method: "POST",
        body: JSON.stringify({ name, scope }),
      }),
    revoke: (keyId: string) =>
      apiFetch<null>(`/api/users/me/api-keys/${keyId}`, { method: "DELETE" }),
  },
};

// ── Companies ─────────────────────────────────────────────────────────────────

const companies = {
  list: (params?: { skip?: number; limit?: number; status_filter?: string; q?: string }) => {
    const qs = new URLSearchParams(
      Object.entries(params ?? {}).filter(([, v]) => v != null) as [string, string][],
    ).toString();
    return apiFetch<Company[]>(`/api/companies/${qs ? `?${qs}` : ""}`);
  },
  get: (id: string) => apiFetch<Company>(`/api/companies/${id}`),
  create: (payload: CreateCompanyRequest) =>
    apiFetch<Company>("/api/companies/generate", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  delete: (id: string) => apiFetch<null>(`/api/companies/${id}`, { method: "DELETE" }),
  regenerate: (id: string) =>
    apiFetch<Company>(`/api/companies/${id}/regenerate`, { method: "POST" }),
};

// ── Deployments ───────────────────────────────────────────────────────────────

const deployments = {
  list: (status_filter?: string) =>
    apiFetch<Deployment[]>(`/api/deployments/${status_filter ? `?status_filter=${status_filter}` : ""}`),
  get: (id: string) => apiFetch<Deployment>(`/api/deployments/${id}`),
  create: (payload: CreateDeploymentRequest) =>
    apiFetch<Deployment>("/api/deployments/", { method: "POST", body: JSON.stringify(payload) }),
  start: (id: string) => apiFetch<Deployment>(`/api/deployments/${id}/start`, { method: "POST" }),
  stop: (id: string, force = false) =>
    apiFetch<Deployment>(`/api/deployments/${id}/stop?force=${force}`, { method: "POST" }),
  restart: (id: string) =>
    apiFetch<Deployment>(`/api/deployments/${id}/restart`, { method: "POST" }),
  delete: (id: string) => apiFetch<null>(`/api/deployments/${id}`, { method: "DELETE" }),
  logs: (id: string, lines = 200) => apiFetch<unknown>(`/api/deployments/${id}/logs?lines=${lines}`),
  metrics: (id: string) => apiFetch<unknown>(`/api/deployments/${id}/metrics`),
};

// ── Tenants ───────────────────────────────────────────────────────────────────

const tenants = {
  list: () => apiFetch<Tenant[]>("/api/tenants"),
  get: (id: string) => apiFetch<Tenant>(`/api/tenants/${id}`),
  register: (name: string, slug?: string) =>
    apiFetch<Tenant>("/api/tenants/register", {
      method: "POST",
      body: JSON.stringify({ name, slug }),
    }),
};

// ── Tickets ───────────────────────────────────────────────────────────────────

const tickets = {
  list: () => apiFetch<Ticket[]>("/api/tickets"),
  get: (id: string) => apiFetch<Ticket>(`/api/tickets/${id}`),
  update: (id: string, payload: Partial<Ticket>) =>
    apiFetch<Ticket>(`/api/tickets/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
};

// ── Workflows ─────────────────────────────────────────────────────────────────

const workflows = {
  list: () => apiFetch<Workflow[]>("/api/workflows"),
  get: (id: string) => apiFetch<Workflow>(`/api/workflows/${id}`),
  create: (payload: unknown) =>
    apiFetch<Workflow>("/api/workflows", { method: "POST", body: JSON.stringify(payload) }),
  trigger: (id: string) =>
    apiFetch<unknown>(`/api/workflows/${id}/trigger`, { method: "POST" }),
};

// ── Leads ─────────────────────────────────────────────────────────────────────

const leads = {
  list: (params?: { q?: string; sort?: string; page?: number; status?: string }) => {
    const qs = new URLSearchParams(
      Object.entries(params ?? {}).filter(([, v]) => v != null) as [string, string][],
    ).toString();
    return apiFetch<Lead[]>(`/api/leads${qs ? `?${qs}` : ""}`);
  },
  get: (id: string) => apiFetch<Lead>(`/api/leads/${id}`),
  update: (id: string, payload: Partial<Lead>) =>
    apiFetch<Lead>(`/api/leads/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
  delete: (id: string) => apiFetch<null>(`/api/leads/${id}`, { method: "DELETE" }),
  enrich: (id: string) => apiFetch<Lead>(`/api/leads/${id}/enrich`, { method: "POST" }),
  timeline: (id: string) => apiFetch<TimelineEntry[]>(`/api/leads/${id}/timeline`),
};

// ── Outreach ──────────────────────────────────────────────────────────────────

const outreach = {
  campaign: (payload: CampaignRequest) =>
    apiFetch<{ status: string; queued: number }>("/api/outreach/campaign", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  sequences: {
    list: () => apiFetch<Sequence[]>("/api/outreach/sequences"),
    create: (payload: CreateSequenceRequest) =>
      apiFetch<Sequence>("/api/outreach/sequence", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    enroll: (lead_ids: string[], sequence_id: string) =>
      apiFetch<{ enrolled: SequenceEnrollment[]; conflicts: unknown[] }>(
        "/api/outreach/sequence/enroll",
        { method: "POST", body: JSON.stringify({ lead_ids, sequence_id }) },
      ),
  },

  inbox: () => apiFetch<InboxReply[]>("/api/outreach/inbox"),

  reports: {
    daily: (start_date: string, end_date: string) =>
      apiFetch<DailyMetric[]>(
        `/api/outreach/reports/daily?start_date=${start_date}&end_date=${end_date}`,
      ),
  },

  weeklyCount: () => apiFetch<{ count: number }>("/api/outreach?period=week"),
};

// ── Notifications ─────────────────────────────────────────────────────────────

const notifications = {
  list: (unread_only = false) =>
    apiFetch<Notification[]>(`/api/notifications?unread_only=${unread_only}`),
  markRead: (id: string) => apiFetch<null>(`/api/notifications/read/${id}`, { method: "POST" }),
  markAllRead: () => apiFetch<null>("/api/notifications/read-all", { method: "POST" }),
};

// ── Health ────────────────────────────────────────────────────────────────────

const health = {
  check: () => apiFetch<HealthCheck>("/health"),
};

// ── Usage ─────────────────────────────────────────────────────────────────────

const usage = {
  list: () => apiFetch<unknown[]>("/api/usage"),
};

// ── Ops ───────────────────────────────────────────────────────────────────────

const ops = {
  status: () => apiFetch<unknown>("/api/ops/status"),
  heal: () => apiFetch<unknown>("/api/ops/heal", { method: "POST" }),
};

// ── Build ─────────────────────────────────────────────────────────────────────

const build = {
  trigger: (name: string, description: string, stack: string) =>
    apiFetch<{ project_id: string }>("/api/build", {
      method: "POST",
      body: JSON.stringify({ name, description, stack }),
    }),
};

// ── WebSocket agent feed ──────────────────────────────────────────────────────

function subscribeAgentFeed(onMessage: (event: AgentEvent) => void): () => void {
  const wsBase = BASE_URL.replace(/^http/, "ws").replace(/\/$/, "");
  const ws = new WebSocket(`${wsBase}/api/ws`);

  ws.onmessage = (evt: MessageEvent) => {
    if (evt.data === "pong") return;
    try {
      const data = JSON.parse(evt.data as string) as AgentEvent;
      onMessage(data);
    } catch {
      // ignore non-JSON messages
    }
  };

  return () => ws.close();
}

// ── Admin ─────────────────────────────────────────────────────────────────────

const admin = {
  listUsers: (skip = 0, limit = 25) =>
    apiFetch<PaginatedResponse<User>>(`/api/admin/users?skip=${skip}&limit=${limit}`),
  toggleUser: (id: string, is_active: boolean) =>
    apiFetch<User>(`/api/admin/users/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ is_active }),
    }),
  listTenants: (skip = 0, limit = 25) =>
    apiFetch<PaginatedResponse<Tenant>>(`/api/admin/tenants?skip=${skip}&limit=${limit}`),
  activateTenant: (id: string) =>
    apiFetch<Tenant>(`/api/admin/tenants/${id}/activate`, { method: "POST" }),
  deactivateTenant: (id: string) =>
    apiFetch<Tenant>(`/api/admin/tenants/${id}/deactivate`, { method: "POST" }),
};

// ── Analytics ─────────────────────────────────────────────────────────────────

const analytics = {
  metrics: (start: string, end: string) =>
    apiFetch<DailyMetric[]>(`/api/outreach/reports/daily?start_date=${start}&end_date=${end}`),
};

// ── Profile ───────────────────────────────────────────────────────────────────

const profile = {
  me: () => apiFetch<User>("/api/auth/me"),
  updateMe: (payload: UpdateProfileRequest) =>
    apiFetch<User>("/api/auth/me", { method: "PATCH", body: JSON.stringify(payload) }),
  listApiKeys: () => apiFetch<unknown[]>("/api/users/me/api-keys"),
  createApiKey: (payload: { name: string; scope: string }) =>
    apiFetch<unknown>("/api/users/me/api-keys", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  revokeApiKey: (id: string) =>
    apiFetch<null>(`/api/users/me/api-keys/${id}`, { method: "DELETE" }),
};

// ── ApiError class ────────────────────────────────────────────────────────────

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

// ── Public export ─────────────────────────────────────────────────────────────

const ApiClient = {
  auth,
  users,
  companies,
  deployments,
  tenants,
  tickets,
  workflows,
  leads,
  outreach,
  notifications,
  health,
  usage,
  ops,
  build,
  admin,
  analytics,
  profile,
  subscribeAgentFeed,
  _fetch: apiFetch,
};

export default ApiClient;
export { apiFetch, ApiClient };
