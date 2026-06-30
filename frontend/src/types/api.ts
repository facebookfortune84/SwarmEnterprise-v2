// ── Type definitions for all SwarmOS API entities ────────────────────────────

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: "admin" | "user";
  subscription_tier: string;
  is_active: boolean;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

export interface DecodedToken {
  sub: string;
  exp: number;
  iat: number;
  role?: string;
}

export interface Company {
  id: string;
  name: string;
  slug: string;
  domain?: string;
  status: "active" | "inactive" | "pending" | "completed" | "generating_tickets" | "failed";
  tech_stack?: string;
  created_at: string;
  updated_at?: string;
}

export interface Deployment {
  id: string;
  company_id?: string;
  tenant_name?: string;
  subdomain?: string;
  status: "running" | "stopped" | "creating" | "failed" | "pending" | "queued" | "deleted";
  memory_mb?: number;
  cpu_cores?: number;
  disk_gb?: number;
  auto_start?: boolean;
  backup_enabled?: boolean;
  created_at: string;
  updated_at?: string;
}

export interface Tenant {
  id: string;
  name: string;
  slug: string;
  status: string;
  created_at: string;
}

export interface Ticket {
  id: string;
  project_id?: string;
  title: string;
  instruction?: string;
  status: "OPEN" | "IN_PROGRESS" | "RESOLVED" | "CLOSED";
  priority: "low" | "medium" | "high" | "critical";
  assignee_id?: string;
  reporter_id?: string;
  due_date?: string;
  sla_hours?: number;
  tags?: string;
  created_at: string;
  resolved_at?: string;
}

export interface Workflow {
  id: string;
  name: string;
  status: "pending" | "running" | "paused" | "completed" | "failed";
  current_step: number;
  steps_json: string;
  error_message?: string;
  created_at: string;
  updated_at?: string;
  completed_at?: string;
}

export interface Lead {
  id: string;
  email?: string;
  name?: string;
  company?: string;
  website?: string;
  linkedin_url?: string;
  intent_score?: number;
  needs_review?: boolean;
  email_invalid?: boolean;
  status: "NEW" | "CONTACTED" | "QUALIFIED" | "COLD" | "COLD_REJECTED";
  created_at: string;
}

export interface Sequence {
  id: string;
  name: string;
  status: "active" | "paused" | "archived";
  step_count: number;
  enrolled_count: number;
  created_at: string;
}

export interface SequenceStep {
  delay_days: number;
  subject_template: string;
  body_template: string;
}

export interface SequenceEnrollment {
  id: string;
  lead_id: string;
  sequence_id: string;
  status: string;
  current_step: number;
  enrolled_at: string;
}

export interface InboxReply {
  id: string;
  mailbox: string;
  uid: string;
  sender?: string;
  from?: string;
  subject?: string;
  classification?: "interested" | "not_interested" | "auto_reply" | "bounce";
  // Extended fields used by outreach components
  sentiment?: "interested" | "not_interested" | "neutral" | "out_of_office" | "unsubscribe";
  lead_id?: string;
  lead_email?: string;
  lead_name?: string;
  body?: string;
  read?: boolean;
  received_at: string;
}

export interface DailyMetric {
  date: string;
  prospects_discovered?: number;
  emails_sent?: number;
  open_rate?: number | null;
  reply_rate?: number | null;
  interested_count?: number;
  bounce_rate?: number | null;
  // Outreach chart fields
  sent?: number;
  opened?: number;
  replied?: number;
  bounced?: number;
  clicked?: number;
}

export interface AgentEvent {
  id?: string;
  timestamp: string;
  agent?: string;
  message: string;
  type?: "info" | "warning" | "error" | "success" | "build" | "deploy";
}

export interface TimelineEntry {
  from_status: string | null;
  to_status: string;
  triggered_by: string;
  occurred_at: string;
}

export interface Notification {
  id: string;
  user_id: string;
  type: "info" | "warning" | "error" | "success";
  title: string;
  message: string;
  is_read: boolean;
  created_at: string;
}

export interface HealthCheck {
  status: string;
  version?: string;
  checks?: {
    db?: string;
    redis?: string;
    ollama?: string;
  };
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// ── Request payload types ─────────────────────────────────────────────────────

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  full_name: string;
}

export interface UpdateProfileRequest {
  full_name?: string;
  password?: string;
}

export interface CreateCompanyRequest {
  name: string;
  description: string;
  tech_stack: string;
  features?: string[];
}

export interface CreateDeploymentRequest {
  company_id: string;
  tenant_name: string;
  subdomain: string;
  memory_mb?: number;
  cpu_cores?: number;
  disk_gb?: number;
  auto_start?: boolean;
  backup_enabled?: boolean;
}

export interface CampaignRequest {
  recipients: string[];
  subject: string;
  body: string;
  from_name?: string;
  scheduled_at?: string;
}

export interface CreateSequenceRequest {
  name: string;
  steps: SequenceStep[];
  status?: "active" | "paused" | "archived";
}

export interface WorkflowNode {
  id: string;
  type: string;
  label: string;
  x: number;
  y: number;
}

export interface WorkflowEdge {
  id: string;
  source: string;
  target: string;
}

export interface WorkflowGraph {
  nodes: Array<{
    id: string;
    type: string;
    position: { x: number; y: number };
    data: Record<string, unknown>;
  }>;
  edges: Array<{
    id: string;
    source: string;
    target: string;
    label?: string;
  }>;
}

export interface APIKey {
  id: string;
  name: string;
  scope: string;
  is_active: boolean;
  created_at: string;
}

export interface APIKeyCreatePayload {
  name: string;
  scope: string;
}
