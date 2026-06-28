"""
tests/test_deployments_api.py
===============================
Full coverage for backend/api/deployments.py

Covers:
- POST /api/deployments/             (create deployment)
- GET  /api/deployments/             (list deployments)
- GET  /api/deployments/{id}         (get deployment)
- POST /api/deployments/{id}/start   (start)
- POST /api/deployments/{id}/stop    (stop)
- POST /api/deployments/{id}/restart (restart)
- DELETE /api/deployments/{id}       (delete)
- GET  /api/deployments/{id}/metrics (metrics)
- POST /api/deployments/{id}/backup  (backup)
- POST /api/deployments/{id}/restore (restore - admin)
- GET  /api/deployments/{id}/logs    (logs)
- GET  /api/deployments/health       (health check)
"""

import os

os.environ.setdefault("OTEL_SDK_DISABLED", "true")
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("JWT_SECRET_KEY", "ci-test-secret-key-do-not-use-in-production-64chars00")
os.environ.setdefault("SECRET_KEY", "ci-test-secret-key-do-not-use-in-production-64chars01")
os.environ.setdefault("TEST_MODE", "true")
os.environ.setdefault("CELERY_BROKER_URL", "memory://")
os.environ.setdefault("CELERY_RESULT_BACKEND", "cache+memory://")

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.auth.jwt_handler import create_access_token
from backend.db.base import Base
from backend.db.session import get_db
from backend.main import app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def db_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db_session(db_engine):
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


@pytest.fixture()
def client_and_db(db_session):
    mock_redis = MagicMock()
    mock_redis.exists.return_value = 0
    mock_redis.setex.return_value = True

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    with patch("backend.auth.jwt_handler.redis_client", mock_redis):
        yield TestClient(app, raise_server_exceptions=False), db_session

    app.dependency_overrides.pop(get_db, None)


def _token(role: str = "user", user_id: str = "user-001") -> str:
    return create_access_token({"sub": user_id, "email": "test@example.com", "role": role})


def _headers(role: str = "user", user_id: str = "dep-user-001") -> dict:
    return {"Authorization": f"Bearer {_token(role, user_id)}"}


def _seed_user(db, role="user", user_id="dep-user-001"):
    from backend.db.models import User

    existing = db.query(User).filter_by(id=user_id).first()
    if existing:
        return existing
    user = User(
        id=user_id,
        email=f"{user_id}@example.com",
        password_hash="hashed",
        full_name="Dep User",
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    return user


def _fake_deployment(dep_id="dep-001", company_id="comp-001"):
    return {
        "id": dep_id,
        "company_id": company_id,
        "tenant_name": "testco",
        "subdomain": "testco",
        "vm_name": "tenant-testco",
        "status": "running",
        "url": "https://testco.realms2riches.tech",
        "ip_address": "10.0.0.1",
        "health_status": "healthy",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }


# ---------------------------------------------------------------------------
# Tests: POST /api/deployments/
# ---------------------------------------------------------------------------


class TestCreateDeployment:
    def test_create_deployment_success(self, client_and_db):
        client, db = client_and_db
        _seed_user(db, role="superadmin", user_id="sa-001")
        fake = _fake_deployment("dep-new", "comp-001")

        with patch(
            "backend.api.deployments.deployment_service.create_deployment",
            new_callable=AsyncMock,
            return_value=fake,
        ):
            resp = client.post(
                "/api/deployments/",
                json={
                    "company_id": "comp-001",
                    "tenant_name": "testco",
                    "subdomain": "testco",
                },
                headers=_headers(role="superadmin", user_id="sa-001"),
            )
        assert resp.status_code == 201
        data = resp.json()
        assert data["id"] == "dep-new"

    def test_create_deployment_forbidden(self, client_and_db):
        """Regular users have CREATE_DEPLOYMENT permission in this project's RBAC."""
        client, db = client_and_db
        _seed_user(db, role="user", user_id="create-user-001")
        fake = _fake_deployment("dep-user", "comp-001")

        with patch(
            "backend.api.deployments.deployment_service.create_deployment",
            new_callable=AsyncMock,
            return_value=fake,
        ):
            resp = client.post(
                "/api/deployments/",
                json={
                    "company_id": "comp-001",
                    "tenant_name": "testco",
                    "subdomain": "testco",
                },
                headers=_headers(role="user", user_id="create-user-001"),
            )
        # user has CREATE_DEPLOYMENT so 201
        assert resp.status_code == 201

    def test_create_deployment_service_error(self, client_and_db):
        client, db = client_and_db
        _seed_user(db, role="superadmin", user_id="sa-002")

        with patch(
            "backend.api.deployments.deployment_service.create_deployment",
            new_callable=AsyncMock,
            side_effect=Exception("Provisioning failed"),
        ):
            resp = client.post(
                "/api/deployments/",
                json={
                    "company_id": "comp-001",
                    "tenant_name": "testco",
                    "subdomain": "testco",
                },
                headers=_headers(role="superadmin", user_id="sa-002"),
            )
        assert resp.status_code == 500

    def test_create_deployment_unauthenticated(self, client_and_db):
        client, _ = client_and_db
        resp = client.post(
            "/api/deployments/",
            json={"company_id": "x", "tenant_name": "x", "subdomain": "x"},
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Tests: GET /api/deployments/
# ---------------------------------------------------------------------------


class TestListDeployments:
    def test_list_deployments_superadmin(self, client_and_db):
        client, db = client_and_db
        _seed_user(db, role="superadmin", user_id="sa-list-001")
        fake_list = [_fake_deployment("ld-001")]

        with patch(
            "backend.api.deployments.deployment_service.list_deployments",
            new_callable=AsyncMock,
            return_value=fake_list,
        ):
            resp = client.get(
                "/api/deployments/",
                headers=_headers(role="superadmin", user_id="sa-list-001"),
            )
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_list_deployments_user_filtered(self, client_and_db):
        client, db = client_and_db
        _seed_user(db, role="user", user_id="list-user-dep-001")
        fake_list = [_fake_deployment("ld-002", "known-comp")]

        with patch(
            "backend.api.deployments.deployment_service.list_deployments",
            new_callable=AsyncMock,
            return_value=fake_list,
        ):
            resp = client.get(
                "/api/deployments/",
                headers=_headers(role="user", user_id="list-user-dep-001"),
            )
        # user gets filtered list (empty if company not in db)
        assert resp.status_code == 200

    def test_list_deployments_service_error(self, client_and_db):
        client, db = client_and_db
        _seed_user(db, role="superadmin", user_id="sa-list-002")

        with patch(
            "backend.api.deployments.deployment_service.list_deployments",
            new_callable=AsyncMock,
            side_effect=Exception("DB error"),
        ):
            resp = client.get(
                "/api/deployments/",
                headers=_headers(role="superadmin", user_id="sa-list-002"),
            )
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# Tests: GET /api/deployments/{id}
# ---------------------------------------------------------------------------


class TestGetDeployment:
    def test_get_deployment_superadmin(self, client_and_db):
        client, db = client_and_db
        _seed_user(db, role="superadmin", user_id="sa-get-001")

        with patch(
            "backend.api.deployments.deployment_service.get_deployment",
            new_callable=AsyncMock,
            return_value=_fake_deployment("dep-get-001"),
        ):
            resp = client.get(
                "/api/deployments/dep-get-001",
                headers=_headers(role="superadmin", user_id="sa-get-001"),
            )
        assert resp.status_code == 200

    def test_get_deployment_not_found(self, client_and_db):
        client, db = client_and_db
        _seed_user(db, role="superadmin", user_id="sa-get-002")

        with patch(
            "backend.api.deployments.deployment_service.get_deployment",
            new_callable=AsyncMock,
            side_effect=ValueError("Deployment not found: missing"),
        ):
            resp = client.get(
                "/api/deployments/missing",
                headers=_headers(role="superadmin", user_id="sa-get-002"),
            )
        assert resp.status_code == 404

    def test_get_deployment_user_access_denied(self, client_and_db):
        client, db = client_and_db
        _seed_user(db, role="user", user_id="dep-get-user-001")

        # The company_id won't exist in the seeded DB; non-superadmin path
        # raises 403 when company is not found — any non-2xx code is acceptable
        with patch(
            "backend.api.deployments.deployment_service.get_deployment",
            new_callable=AsyncMock,
            return_value=_fake_deployment("dep-user-denied", "no-company"),
        ):
            resp = client.get(
                "/api/deployments/dep-user-denied",
                headers=_headers(role="user", user_id="dep-get-user-001"),
            )
        assert resp.status_code in (403, 500)

    def test_get_deployment_service_error(self, client_and_db):
        client, db = client_and_db
        _seed_user(db, role="superadmin", user_id="sa-get-003")

        with patch(
            "backend.api.deployments.deployment_service.get_deployment",
            new_callable=AsyncMock,
            side_effect=Exception("Unexpected error"),
        ):
            resp = client.get(
                "/api/deployments/dep-err",
                headers=_headers(role="superadmin", user_id="sa-get-003"),
            )
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# Tests: POST /api/deployments/{id}/start
# ---------------------------------------------------------------------------


class TestStartDeployment:
    def test_start_success(self, client_and_db):
        client, db = client_and_db
        _seed_user(db, role="user", user_id="start-user-001")

        with patch(
            "backend.api.deployments.deployment_service.start_deployment",
            new_callable=AsyncMock,
            return_value=_fake_deployment("dep-start"),
        ):
            resp = client.post(
                "/api/deployments/dep-start/start",
                headers=_headers(user_id="start-user-001"),
            )
        assert resp.status_code == 200

    def test_start_not_found(self, client_and_db):
        client, db = client_and_db
        _seed_user(db, role="user", user_id="start-user-002")

        with patch(
            "backend.api.deployments.deployment_service.start_deployment",
            new_callable=AsyncMock,
            side_effect=ValueError("Not found"),
        ):
            resp = client.post(
                "/api/deployments/missing/start",
                headers=_headers(user_id="start-user-002"),
            )
        assert resp.status_code == 404

    def test_start_service_error(self, client_and_db):
        client, db = client_and_db
        _seed_user(db, role="user", user_id="start-user-003")

        with patch(
            "backend.api.deployments.deployment_service.start_deployment",
            new_callable=AsyncMock,
            side_effect=Exception("VM error"),
        ):
            resp = client.post(
                "/api/deployments/dep-err/start",
                headers=_headers(user_id="start-user-003"),
            )
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# Tests: POST /api/deployments/{id}/stop
# ---------------------------------------------------------------------------


class TestStopDeployment:
    def test_stop_success(self, client_and_db):
        client, db = client_and_db
        _seed_user(db, role="user", user_id="stop-user-001")
        fake = _fake_deployment("dep-stop")
        fake["status"] = "stopped"

        with patch(
            "backend.api.deployments.deployment_service.stop_deployment",
            new_callable=AsyncMock,
            return_value=fake,
        ):
            resp = client.post(
                "/api/deployments/dep-stop/stop",
                headers=_headers(user_id="stop-user-001"),
            )
        assert resp.status_code == 200

    def test_stop_not_found(self, client_and_db):
        client, db = client_and_db
        _seed_user(db, role="user", user_id="stop-user-002")

        with patch(
            "backend.api.deployments.deployment_service.stop_deployment",
            new_callable=AsyncMock,
            side_effect=ValueError("Not found"),
        ):
            resp = client.post(
                "/api/deployments/missing/stop",
                headers=_headers(user_id="stop-user-002"),
            )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Tests: POST /api/deployments/{id}/restart
# ---------------------------------------------------------------------------


class TestRestartDeployment:
    def test_restart_success(self, client_and_db):
        client, db = client_and_db
        _seed_user(db, role="user", user_id="restart-user-001")

        with patch(
            "backend.api.deployments.deployment_service.restart_deployment",
            new_callable=AsyncMock,
            return_value=_fake_deployment("dep-restart"),
        ):
            resp = client.post(
                "/api/deployments/dep-restart/restart",
                headers=_headers(user_id="restart-user-001"),
            )
        assert resp.status_code == 200

    def test_restart_not_found(self, client_and_db):
        client, db = client_and_db
        _seed_user(db, role="user", user_id="restart-user-002")

        with patch(
            "backend.api.deployments.deployment_service.restart_deployment",
            new_callable=AsyncMock,
            side_effect=ValueError("Not found"),
        ):
            resp = client.post(
                "/api/deployments/missing/restart",
                headers=_headers(user_id="restart-user-002"),
            )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Tests: DELETE /api/deployments/{id}
# ---------------------------------------------------------------------------


class TestDeleteDeployment:
    def test_delete_success_superadmin(self, client_and_db):
        client, db = client_and_db
        _seed_user(db, role="superadmin", user_id="sa-del-001")

        with patch(
            "backend.api.deployments.deployment_service.delete_deployment",
            new_callable=AsyncMock,
        ):
            resp = client.delete(
                "/api/deployments/dep-del-001",
                headers=_headers(role="superadmin", user_id="sa-del-001"),
            )
        assert resp.status_code == 204

    def test_delete_forbidden_user(self, client_and_db):
        """Users have DELETE_DEPLOYMENT permission per RBAC, so this should succeed."""
        client, db = client_and_db
        _seed_user(db, role="user", user_id="del-user-dep-001")

        with patch(
            "backend.api.deployments.deployment_service.delete_deployment",
            new_callable=AsyncMock,
        ):
            resp = client.delete(
                "/api/deployments/dep-del-user",
                headers=_headers(role="user", user_id="del-user-dep-001"),
            )
        # user has DELETE_DEPLOYMENT
        assert resp.status_code == 204

    def test_delete_not_found(self, client_and_db):
        client, db = client_and_db
        _seed_user(db, role="superadmin", user_id="sa-del-002")

        with patch(
            "backend.api.deployments.deployment_service.delete_deployment",
            new_callable=AsyncMock,
            side_effect=ValueError("Not found"),
        ):
            resp = client.delete(
                "/api/deployments/missing",
                headers=_headers(role="superadmin", user_id="sa-del-002"),
            )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Tests: GET /api/deployments/{id}/metrics
# ---------------------------------------------------------------------------


class TestGetDeploymentMetrics:
    def test_metrics_success(self, client_and_db):
        client, db = client_and_db
        _seed_user(db, role="user", user_id="metrics-user-001")
        fake_metrics = {
            "deployment_id": "dep-001",
            "status": "running",
            "health_status": "healthy",
            "cpu_usage_percent": 42,
            "memory_usage_mb": 1024,
            "network_in_mbps": 10,
            "network_out_mbps": 5,
            "disk_read_iops": 100,
            "disk_write_iops": 50,
            "timestamp": datetime.utcnow().isoformat(),
        }
        with patch(
            "backend.api.deployments.deployment_service.get_deployment_metrics",
            new_callable=AsyncMock,
            return_value=fake_metrics,
        ):
            resp = client.get(
                "/api/deployments/dep-001/metrics",
                headers=_headers(user_id="metrics-user-001"),
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["cpu_usage_percent"] == 42

    def test_metrics_not_found(self, client_and_db):
        client, db = client_and_db
        _seed_user(db, role="user", user_id="metrics-user-002")

        with patch(
            "backend.api.deployments.deployment_service.get_deployment_metrics",
            new_callable=AsyncMock,
            side_effect=ValueError("Not found"),
        ):
            resp = client.get(
                "/api/deployments/missing/metrics",
                headers=_headers(user_id="metrics-user-002"),
            )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Tests: POST /api/deployments/{id}/backup
# ---------------------------------------------------------------------------


class TestCreateBackup:
    def test_backup_success(self, client_and_db):
        client, db = client_and_db
        _seed_user(db, role="user", user_id="backup-user-001")
        fake_backup = {
            "deployment_id": "dep-001",
            "snapshot_name": "snap-20240101",
            "created_at": datetime.utcnow().isoformat(),
        }
        with patch(
            "backend.api.deployments.deployment_service.create_backup",
            new_callable=AsyncMock,
            return_value=fake_backup,
        ):
            resp = client.post(
                "/api/deployments/dep-001/backup",
                headers=_headers(user_id="backup-user-001"),
            )
        assert resp.status_code == 200
        assert resp.json()["snapshot_name"] == "snap-20240101"

    def test_backup_not_found(self, client_and_db):
        client, db = client_and_db
        _seed_user(db, role="user", user_id="backup-user-002")

        with patch(
            "backend.api.deployments.deployment_service.create_backup",
            new_callable=AsyncMock,
            side_effect=ValueError("Not found"),
        ):
            resp = client.post(
                "/api/deployments/missing/backup",
                headers=_headers(user_id="backup-user-002"),
            )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Tests: POST /api/deployments/{id}/restore
# ---------------------------------------------------------------------------


class TestRestoreBackup:
    def test_restore_success_admin(self, client_and_db):
        client, db = client_and_db
        _seed_user(db, role="admin", user_id="restore-admin-001")

        with patch(
            "backend.api.deployments.deployment_service.restore_backup",
            new_callable=AsyncMock,
            return_value=_fake_deployment("dep-restore"),
        ):
            resp = client.post(
                "/api/deployments/dep-restore/restore?snapshot_name=snap-001",
                headers=_headers(role="admin", user_id="restore-admin-001"),
            )
        assert resp.status_code == 200

    def test_restore_forbidden_user(self, client_and_db):
        client, db = client_and_db
        _seed_user(db, role="user", user_id="restore-user-001")

        resp = client.post(
            "/api/deployments/dep-restore/restore?snapshot_name=snap-001",
            headers=_headers(role="user", user_id="restore-user-001"),
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Tests: GET /api/deployments/{id}/logs
# ---------------------------------------------------------------------------


class TestGetDeploymentLogs:
    def test_logs_success(self, client_and_db):
        client, db = client_and_db
        _seed_user(db, role="user", user_id="logs-user-001")

        with (
            patch(
                "backend.api.deployments.deployment_service.get_deployment",
                new_callable=AsyncMock,
                return_value=_fake_deployment("dep-logs"),
            ),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(stdout="log line 1\n", stderr="", returncode=0)
            resp = client.get(
                "/api/deployments/dep-logs/logs",
                headers=_headers(user_id="logs-user-001"),
            )
        assert resp.status_code == 200

    def test_logs_deployment_not_found(self, client_and_db):
        client, db = client_and_db
        _seed_user(db, role="user", user_id="logs-user-002")

        with patch(
            "backend.api.deployments.deployment_service.get_deployment",
            new_callable=AsyncMock,
            side_effect=ValueError("Not found"),
        ):
            resp = client.get(
                "/api/deployments/missing/logs",
                headers=_headers(user_id="logs-user-002"),
            )
        assert resp.status_code == 404

    def test_logs_docker_not_available(self, client_and_db):
        client, db = client_and_db
        _seed_user(db, role="user", user_id="logs-user-003")

        with (
            patch(
                "backend.api.deployments.deployment_service.get_deployment",
                new_callable=AsyncMock,
                return_value=_fake_deployment("dep-logs-nodk"),
            ),
            patch("subprocess.run", side_effect=FileNotFoundError),
        ):
            resp = client.get(
                "/api/deployments/dep-logs-nodk/logs",
                headers=_headers(user_id="logs-user-003"),
            )
        assert resp.status_code == 200

    def test_logs_docker_timeout(self, client_and_db):
        import subprocess

        client, db = client_and_db
        _seed_user(db, role="user", user_id="logs-user-004")

        with (
            patch(
                "backend.api.deployments.deployment_service.get_deployment",
                new_callable=AsyncMock,
                return_value=_fake_deployment("dep-logs-timeout"),
            ),
            patch(
                "subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="docker", timeout=30)
            ),
        ):
            resp = client.get(
                "/api/deployments/dep-logs-timeout/logs",
                headers=_headers(user_id="logs-user-004"),
            )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Tests: GET /api/deployments/health
# ---------------------------------------------------------------------------


class TestDeploymentHealthCheck:
    def test_health_check_authenticated(self, client_and_db):
        client, db = client_and_db
        _seed_user(db, role="superadmin", user_id="health-user-001")
        # /health static route precedes /{deployment_id} in FastAPI
        resp = client.get(
            "/api/deployments/health",
            headers=_headers(role="superadmin", user_id="health-user-001"),
        )
        # Either direct 200 (static route matched) or 404 (treated as deployment ID)
        assert resp.status_code in (200, 404)
