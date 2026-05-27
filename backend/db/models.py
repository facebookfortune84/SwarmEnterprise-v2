import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
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
    status = Column(String, default="queued") # queued, in_progress, success, failed, rolled_back
    strategy = Column(String) # blue-green, canary, rolling
    version = Column(String)
    metadata_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
