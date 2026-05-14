import os
import uuid
from pathlib import Path
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

class Ticket(Base):
    __tablename__ = 'tickets'
    id = Column(String, primary_key=True)
    project_id = Column(String)
    department = Column(String)
    title = Column(String)
    instruction = Column(Text)
    status = Column(String, default="OPEN")
    created_at = Column(DateTime, default=datetime.utcnow)

class Project(Base):
    __tablename__ = 'projects'
    id = Column(String, primary_key=True)
    stripe_session = Column(String, nullable=True)
    customer_email = Column(String, nullable=True)
    product_id = Column(String, nullable=True)
    price_id = Column(String, nullable=True)
    metadata_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Lead(Base):
    __tablename__ = 'leads'
    id = Column(String, primary_key=True)
    email = Column(String, index=True)
    name = Column(String, nullable=True)
    company = Column(String, nullable=True)
    status = Column(String, default='NEW')
    metadata_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class UsageEvent(Base):
    __tablename__ = 'usage_events'
    id = Column(String, primary_key=True)
    project_id = Column(String, index=True, nullable=True)
    event_type = Column(String)
    amount = Column(String, nullable=True)
    metadata_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class ProcessedEvent(Base):
    __tablename__ = 'processed_events'
    id = Column(String, primary_key=True)
    event_id = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class LinearEngine:
    """Ticket persistence for the swarm"""
    def __init__(self):
        # Use configurable data directory (env or repo-relative)
        db_dir = Path(os.getenv("SWARM_PG_DIR", Path(__file__).resolve().parents[2] / "pg_data"))
        db_dir.mkdir(parents=True, exist_ok=True)
        db_path = db_dir / "swarm_tickets.db"
        self.engine = create_engine(f"sqlite:///{db_path.as_posix()}")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def create_ticket(self, project_id, dept, title, instruction):
        session = self.Session()
        t = Ticket(id=uuid.uuid4().hex[:8].upper(), project_id=project_id, department=dept, title=title, instruction=instruction)
        session.add(t)
        session.commit()
        session.close()

    def create_project(self, project_id, stripe_session=None, customer_email=None, product_id=None, price_id=None, metadata=None):
        session = self.Session()
        p = Project(id=project_id, stripe_session=stripe_session, customer_email=customer_email, product_id=product_id, price_id=price_id, metadata_json=metadata)
        session.add(p)
        session.commit()
        session.close()

    def create_lead(self, email: str, name: str = None, company: str = None, metadata: dict = None) -> str:
        session = self.Session()
        lead_id = uuid.uuid4().hex[:8].upper()
        l = Lead(id=lead_id, email=email, name=name, company=company, metadata_json=str(metadata) if metadata else None)
        session.add(l)
        session.commit()
        session.close()

        # Attempt immediate sync to external CRMs if configured
        try:
            properties = {"name": name or email, "company": company}
            from backend.connectors import hubspot, close, sheets
            # Best-effort, do not fail on errors
            try:
                hubspot.create_contact(email, properties)
            except Exception:
                logger = logging.getLogger("HubSpotConnector")
                logger.exception("HubSpot sync failed")
            try:
                close.create_lead(email, properties)
            except Exception:
                logger = logging.getLogger("CloseConnector")
                logger.exception("Close sync failed")
            try:
                sheets.push_row({"email": email, "name": name, "company": company, "lead_id": lead_id})
            except Exception:
                logger = logging.getLogger("SheetsConnector")
                logger.exception("Sheets push failed")
        except Exception:
            # Ignore sync errors to avoid breaking lead creation
            pass

        return lead_id

    def list_leads(self, limit: int = 100):
        session = self.Session()
        rows = session.query(Lead).order_by(Lead.created_at.desc()).limit(limit).all()
        result = []
        for r in rows:
            result.append({
                'id': r.id,
                'email': r.email,
                'name': r.name,
                'company': r.company,
                'status': r.status,
                'metadata': r.metadata_json,
                'created_at': r.created_at.isoformat() if r.created_at else None
            })
        session.close()
        return result

    def get_lead(self, lead_id: str):
        session = self.Session()
        r = session.query(Lead).filter(Lead.id == lead_id).first()
        if not r:
            session.close()
            return None
        result = {
            'id': r.id,
            'email': r.email,
            'name': r.name,
            'company': r.company,
            'status': r.status,
            'metadata': r.metadata_json,
            'created_at': r.created_at.isoformat() if r.created_at else None
        }
        session.close()
        return result

    def record_usage(self, project_id: str | None, event_type: str, amount: str | None = None, metadata: dict | None = None) -> str:
        session = self.Session()
        uid = uuid.uuid4().hex[:12]
        u = UsageEvent(id=uid, project_id=project_id, event_type=event_type, amount=str(amount) if amount else None, metadata_json=str(metadata) if metadata else None)
        session.add(u)
        session.commit()
        session.close()
        return uid

    def list_usage(self, project_id: str | None = None, limit: int = 100):
        session = self.Session()
        q = session.query(UsageEvent).order_by(UsageEvent.created_at.desc())
        if project_id:
            q = q.filter(UsageEvent.project_id == project_id)
        rows = q.limit(limit).all()
        result = []
        for r in rows:
            result.append({
                'id': r.id,
                'project_id': r.project_id,
                'event_type': r.event_type,
                'amount': r.amount,
                'metadata': r.metadata_json,
                'created_at': r.created_at.isoformat() if r.created_at else None
            })
        session.close()
        return result

    def get_lead(self, lead_id: str):
        session = self.Session()
        r = session.query(Lead).filter(Lead.id == lead_id).first()
        if not r:
            session.close()
            return None
        result = {
            'id': r.id,
            'email': r.email,
            'name': r.name,
            'company': r.company,
            'status': r.status,
            'metadata': r.metadata_json,
            'created_at': r.created_at.isoformat() if r.created_at else None
        }
        session.close()
        return result

    def is_event_processed(self, event_id: str) -> bool:
        session = self.Session()
        try:
            r = session.query(ProcessedEvent).filter(ProcessedEvent.event_id == event_id).first()
            return bool(r)
        finally:
            session.close()

    def mark_event_processed(self, event_id: str):
        session = self.Session()
        try:
            exists = session.query(ProcessedEvent).filter(ProcessedEvent.event_id == event_id).first()
            if not exists:
                e = ProcessedEvent(id=uuid.uuid4().hex[:12], event_id=event_id)
                session.add(e)
                session.commit()
        finally:
            session.close()

    def list_projects(self, limit: int = 100):
        session = self.Session()
        rows = session.query(Project).order_by(Project.created_at.desc()).limit(limit).all()
        result = []
        for r in rows:
            result.append({
                'id': r.id,
                'stripe_session': r.stripe_session,
                'customer_email': r.customer_email,
                'product_id': r.product_id,
                'price_id': r.price_id,
                'metadata': r.metadata_json,
                'created_at': r.created_at.isoformat() if r.created_at else None
            })
        session.close()
        return result

    def get_project(self, project_id: str):
        session = self.Session()
        r = session.query(Project).filter(Project.id == project_id).first()
        if not r:
            session.close()
            return None
        result = {
            'id': r.id,
            'stripe_session': r.stripe_session,
            'customer_email': r.customer_email,
            'product_id': r.product_id,
            'price_id': r.price_id,
            'metadata': r.metadata_json,
            'created_at': r.created_at.isoformat() if r.created_at else None
        }
        session.close()
        return result

# Lazy singleton factory to avoid import-time DB creation
_swarm_db = None

def get_swarm_db():
    global _swarm_db
    if _swarm_db is None:
        _swarm_db = LinearEngine()
    return _swarm_db
