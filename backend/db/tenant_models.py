"""SQLAlchemy models for multi-tenant company boxes."""

from datetime import datetime

from sqlalchemy import Column, DateTime, String, Text
from sqlalchemy.orm import declarative_base

TenantBase = declarative_base()


class CompanyTenant(TenantBase):
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
