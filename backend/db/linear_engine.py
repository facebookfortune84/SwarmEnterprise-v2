import uuid
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

class LinearEngine:
    """Ticket persistence for the swarm"""
    def __init__(self):
        self.engine = create_engine("sqlite:////mnt/c/SwarmEnterprise_v2/pg_data/swarm_tickets.db")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def create_ticket(self, project_id, dept, title, instruction):
        session = self.Session()
        t = Ticket(id=uuid.uuid4().hex[:8].upper(), project_id=project_id, department=dept, title=title, instruction=instruction)
        session.add(t)
        session.commit()
        session.close()

swarm_db = LinearEngine()
