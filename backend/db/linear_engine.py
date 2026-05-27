import logging
import os
import uuid
from pathlib import Path
from datetime import datetime
from sqlalchemy.orm import Session
from backend.db.models import Ticket, Project, Lead, UsageEvent, ProcessedEvent
from backend.db.session import SessionLocal

logger = logging.getLogger("LinearEngine")


class LinearEngine:
    """Ticket persistence for the swarm"""

    def __init__(self, db: Session = None):
        self.db = db or SessionLocal()

    def create_ticket(self, project_id, dept, title, instruction):
        t = Ticket(
            project_id=project_id,
            department=dept,
            title=title,
            instruction=instruction,
        )
        self.db.add(t)
        self.db.commit()
        return t

    def create_project(
        self,
        project_id,
        stripe_session=None,
        customer_email=None,
        product_id=None,
        price_id=None,
        metadata=None,
    ):
        p = Project(
            id=project_id,
            stripe_session=stripe_session,
            customer_email=customer_email,
            product_id=product_id,
            price_id=price_id,
            metadata_json=metadata,
        )
        self.db.add(p)
        self.db.commit()
        return p

    def create_lead(
        self, email: str, name: str = None, company: str = None, metadata: dict = None
    ) -> str:
        lead = Lead(
            email=email,
            name=name,
            company=company,
            metadata_json=str(metadata) if metadata else None,
        )
        self.db.add(lead)
        self.db.commit()
        self.db.refresh(lead)
        lead_id = lead.id

        # Attempt immediate sync to external CRMs if configured
        try:
            properties = {"name": name or email, "company": company}
            from backend.connectors import hubspot, close, sheets

            # Best-effort, do not fail on errors
            try:
                hubspot.create_contact(email, properties)
            except Exception:
                logger.exception("HubSpot sync failed")
            try:
                close.create_lead(email, properties)
            except Exception:
                logger.exception("Close sync failed")
            try:
                sheets.push_row(
                    {"email": email, "name": name, "company": company, "lead_id": lead_id}
                )
            except Exception:
                logger.exception("Sheets push failed")
        except Exception:
            # Ignore sync errors to avoid breaking lead creation
            pass

        return lead_id

    def list_leads(self, limit: int = 100):
        rows = self.db.query(Lead).order_by(Lead.created_at.desc()).limit(limit).all()
        result = []
        for r in rows:
            result.append(
                {
                    "id": r.id,
                    "email": r.email,
                    "name": r.name,
                    "company": r.company,
                    "status": r.status,
                    "metadata": r.metadata_json,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
            )
        return result

    def get_lead(self, lead_id: str):
        r = self.db.query(Lead).filter(Lead.id == lead_id).first()
        if not r:
            return None
        return {
            "id": r.id,
            "email": r.email,
            "name": r.name,
            "company": r.company,
            "status": r.status,
            "metadata": r.metadata_json,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }

    def record_usage(
        self,
        project_id: str | None,
        event_type: str,
        amount: str | None = None,
        metadata: dict | None = None,
    ) -> str:
        u = UsageEvent(
            project_id=project_id,
            event_type=event_type,
            amount=str(amount) if amount else None,
            metadata_json=str(metadata) if metadata else None,
        )
        self.db.add(u)
        self.db.commit()
        self.db.refresh(u)
        return u.id

    def list_usage(self, project_id: str | None = None, limit: int = 100):
        q = self.db.query(UsageEvent).order_by(UsageEvent.created_at.desc())
        if project_id:
            q = q.filter(UsageEvent.project_id == project_id)
        rows = q.limit(limit).all()
        result = []
        for r in rows:
            result.append(
                {
                    "id": r.id,
                    "project_id": r.project_id,
                    "event_type": r.event_type,
                    "amount": r.amount,
                    "metadata": r.metadata_json,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
            )
        return result

    def is_event_processed(self, event_id: str) -> bool:
        r = self.db.query(ProcessedEvent).filter(ProcessedEvent.event_id == event_id).first()
        return bool(r)

    def mark_event_processed(self, event_id: str):
        exists = (
            self.db.query(ProcessedEvent).filter(ProcessedEvent.event_id == event_id).first()
        )
        if not exists:
            e = ProcessedEvent(event_id=event_id)
            self.db.add(e)
            self.db.commit()

    def list_projects(self, limit: int = 100):
        rows = self.db.query(Project).order_by(Project.created_at.desc()).limit(limit).all()
        result = []
        for r in rows:
            result.append(
                {
                    "id": r.id,
                    "stripe_session": r.stripe_session,
                    "customer_email": r.customer_email,
                    "product_id": r.product_id,
                    "price_id": r.price_id,
                    "metadata": r.metadata_json,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
            )
        return result

    def get_project(self, project_id: str):
        r = self.db.query(Project).filter(Project.id == project_id).first()
        if not r:
            return None
        return {
            "id": r.id,
            "stripe_session": r.stripe_session,
            "customer_email": r.customer_email,
            "product_id": r.product_id,
            "price_id": r.price_id,
            "metadata": r.metadata_json,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }

    def close(self):
        self.db.close()


# Lazy singleton factory to avoid import-time DB creation
_swarm_db = None


def get_swarm_db():
    global _swarm_db
    if _swarm_db is None:
        _swarm_db = LinearEngine()
    return _swarm_db
