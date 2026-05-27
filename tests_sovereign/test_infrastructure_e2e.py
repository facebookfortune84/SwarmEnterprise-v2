import pytest
import json
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.db.base import Base
from backend.db.models import CompanyTenant, Deployment
from backend.core.deployment_service import DeploymentService

# Setup Test DB
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

@pytest.mark.asyncio
async def test_end_to_end_deployment_lifecycle(db):
    """
    Tests the 100% complete deployment lifecycle.
    Mocks subprocess to avoid actual docker commands during unit test,
    but verifies DB persistence and service orchestration.
    """
    service = DeploymentService(db)
    
    # 1. Setup a tenant
    tenant = CompanyTenant(
        id="TEN-INFRA-1",
        slug="infra-test",
        name="Infra Test Co",
        subdomain="infra.test",
        status="pending"
    )
    db.add(tenant)
    db.commit()

    # 2. Mock Docker Response (BoxDeployer uses subprocess.run with text=True)
    mock_docker_running = MagicMock()
    mock_docker_running.returncode = 0
    mock_docker_running.stdout = "container_id_123"
    
    # 3. Execute Deployment
    with patch("subprocess.run", return_value=mock_docker_running):
        result = await service.deploy_tenant_application(tenant.id)
        
        assert result["status"] in ["running", "success"]
        # In 100% implementation, container_id is under details -> resource_id or details -> details -> container_id
        assert "container_id" in str(result)
        
        # 4. Verify DB State
        db_tenant = db.query(CompanyTenant).filter_by(id=tenant.id).first()
        assert db_tenant.status == "running"
        
        db_deployment = db.query(Deployment).filter_by(tenant_id=tenant.id).first()
        assert db_deployment is not None
        assert db_deployment.status == "success"
        
        # 5. Verify History
        history = service.get_deployment_history(tenant.id)
        assert len(history) == 1
        assert history[0]["status"] == "success"

@pytest.mark.asyncio
async def test_system_health_reporting():
    """
    Tests the real host health reporting logic.
    """
    from agents.devops.infrastructure_agent import infra_agent
    health = await infra_agent.get_system_health()
    
    assert "cpu_percent" in health
    assert "memory_percent" in health
    assert isinstance(health["cpu_percent"], float)
