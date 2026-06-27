import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.db.base import Base
from backend.db.models import User, CompanyTenant, Ticket, Deployment
from backend.auth.user_service import UserService, UserCreate

# Use in-memory SQLite for testing
SQLALCHEMY_DATABASE_URL = "sqlite://"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_user_creation_persistence(db):
    user_service = UserService(db)
    user_data = UserCreate(
        email="test@example.com", password="SecurePass123!", full_name="Test User"
    )
    user_service.create_user(user_data)

    # Query directly from DB
    db_user = db.query(User).filter(User.email == "test@example.com").first()
    assert db_user is not None
    assert db_user.full_name == "Test User"
    assert user_service.verify_password("SecurePass123!", db_user.password_hash)


def test_tenant_and_deployment_persistence(db):
    tenant = CompanyTenant(
        id="TEN-123",
        slug="test-tenant",
        name="Test Company",
        subdomain="test.example.tech",
        status="running",
    )
    db.add(tenant)
    db.commit()

    deployment = Deployment(
        tenant_id="TEN-123", status="success", strategy="blue-green", version="1.0.0"
    )
    db.add(deployment)
    db.commit()

    db_tenant = db.query(CompanyTenant).filter_by(id="TEN-123").first()
    assert db_tenant is not None
    assert db_tenant.slug == "test-tenant"

    db_deployment = db.query(Deployment).filter_by(tenant_id="TEN-123").first()
    assert db_deployment is not None
    assert db_deployment.strategy == "blue-green"


def test_ticket_persistence(db):
    ticket = Ticket(
        project_id="PROJ-001",
        department="Engineering",
        title="Test Task",
        instruction="Do something",
    )
    db.add(ticket)
    db.commit()

    db_ticket = db.query(Ticket).filter_by(project_id="PROJ-001").first()
    assert db_ticket is not None
    assert db_ticket.title == "Test Task"
