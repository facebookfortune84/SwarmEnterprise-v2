import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Boolean, ForeignKey, Integer, Float
from backend.db.base import Base


class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(String, default="user")
    subscription_tier = Column(String, default="free")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CompanyTenant(Base):
    __tablename__ = "company_tenants"
    id = Column(String, primary_key=True)
    slug = Column(String, unique=True, index=True)
    name = Column(String)
    subdomain = Column(String, unique=True, index=True)
    status = Column(String, default="pending")  # pending, provisioning, running, failed, stopped
    vm_id = Column(String, nullable=True)
    container_id = Column(String, nullable=True)
    box_url = Column(String, nullable=True)
    metadata_json = Column(Text, nullable=True)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Ticket(Base):
    __tablename__ = "tickets"
    id = Column(String, primary_key=True, default=lambda: uuid.uuid4().hex[:8].upper())
    project_id = Column(String, index=True)
    department = Column(String)
    title = Column(String)
    instruction = Column(Text)
    status = Column(String, default="OPEN")
    created_at = Column(DateTime, default=datetime.utcnow)
    # Phase 2 additions
    priority = Column(String, default="medium")  # low/medium/high/critical
    assignee_id = Column(String, ForeignKey("users.id"), nullable=True)
    reporter_id = Column(String, ForeignKey("users.id"), nullable=True)
    due_date = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    sla_hours = Column(Integer, default=24)
    tags = Column(String, nullable=True)  # comma-separated
    parent_ticket_id = Column(String, ForeignKey("tickets.id"), nullable=True)
    estimated_hours = Column(Float, nullable=True)
    actual_hours = Column(Float, nullable=True)


class Project(Base):
    __tablename__ = "projects"
    id = Column(String, primary_key=True)
    stripe_session = Column(String, nullable=True)
    customer_email = Column(String, nullable=True)
    product_id = Column(String, nullable=True)
    price_id = Column(String, nullable=True)
    metadata_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Lead(Base):
    __tablename__ = "leads"
    id = Column(String, primary_key=True, default=lambda: uuid.uuid4().hex[:8].upper())
    email = Column(String, index=True)
    name = Column(String, nullable=True)
    company = Column(String, nullable=True)
    status = Column(String, default="NEW")
    metadata_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    # Phase 3: outreach-pipeline extensions
    website = Column(String, nullable=True)
    linkedin_url = Column(String, nullable=True)
    intent_score = Column(Integer, nullable=True)
    needs_review = Column(Boolean, default=False)
    email_invalid = Column(Boolean, default=False)


class UsageEvent(Base):
    __tablename__ = "usage_events"
    id = Column(String, primary_key=True, default=lambda: uuid.uuid4().hex[:12])
    project_id = Column(String, index=True, nullable=True)
    event_type = Column(String)
    amount = Column(String, nullable=True)
    metadata_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ProcessedEvent(Base):
    __tablename__ = "processed_events"
    id = Column(String, primary_key=True, default=lambda: uuid.uuid4().hex[:12])
    event_id = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Deployment(Base):
    __tablename__ = "deployments"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("company_tenants.id"), index=True)
    status = Column(String, default="queued")  # queued, in_progress, success, failed, rolled_back
    strategy = Column(String)  # blue-green, canary, rolling
    version = Column(String)
    metadata_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class APIKey(Base):
    __tablename__ = "api_keys"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    key = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(String, ForeignKey("users.id"), index=True)
    name = Column(String, nullable=False)
    scope = Column(String, default="read:write")
    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 — Communication, Ticketing, Task Queue, and Workflow models
# ─────────────────────────────────────────────────────────────────────────────


class Notification(Base):
    __tablename__ = "notifications"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), index=True, nullable=False)
    type = Column(String, default="info")  # info/warning/error/success
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    metadata_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class MessageThread(Base):
    __tablename__ = "message_threads"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    subject = Column(String, nullable=False)
    participants_json = Column(Text, nullable=False)  # JSON array of user_ids
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Message(Base):
    __tablename__ = "messages"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    thread_id = Column(String, ForeignKey("message_threads.id"), index=True, nullable=False)
    sender_id = Column(String, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class TicketHistory(Base):
    __tablename__ = "ticket_history"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    ticket_id = Column(String, ForeignKey("tickets.id"), index=True, nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class TicketComment(Base):
    __tablename__ = "ticket_comments"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    ticket_id = Column(String, ForeignKey("tickets.id"), index=True, nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Workflow(Base):
    __tablename__ = "workflows"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    company_id = Column(String, ForeignKey("company_tenants.id"), nullable=True)
    # pending/running/paused/completed/failed
    status = Column(String, default="pending")
    current_step = Column(Integer, default=0)
    steps_json = Column(Text, nullable=False)  # JSON array of step definitions
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


class WorkflowStep(Base):
    __tablename__ = "workflow_steps"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_id = Column(String, ForeignKey("workflows.id"), index=True, nullable=False)
    step_name = Column(String, nullable=False)
    # ticket/notification/approval/condition
    step_type = Column(String, nullable=False)
    # pending/running/completed/failed/skipped
    status = Column(String, default="pending")
    input_json = Column(Text, nullable=True)
    output_json = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
