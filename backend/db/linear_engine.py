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
