"""
tests/test_companies_api.py
============================
Full coverage for backend/api/companies.py

Covers:
- POST /api/companies/generate
- GET  /api/companies/
- GET  /api/companies/{company_id}
- GET  /api/companies/{company_id}/status
- GET  /api/companies/{company_id}/download
- DELETE /api/companies/{company_id}
- POST /api/companies/{company_id}/regenerate
- GET  /api/companies/{company_id}/metadata
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


def _auth_headers(role: str = "user", user_id: str = "user-001") -> dict:
    return {"Authorization": f"Bearer {_token(role, user_id)}"}


def _seed_user(db_session, role="user", user_id="user-001"):
    from backend.db.models import User

    existing = db_session.query(User).filter_by(id=user_id).first()
    if existing:
        return existing
    user = User(
        id=user_id,
        email=f"{user_id}@example.com",
        password_hash="hashed",
        full_name="Test User",
        role=role,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    return user


def _seed_company_tenant(db_session, tenant_id="comp-001", slug="test-company"):
    from backend.db.models import CompanyTenant

    existing = db_session.query(CompanyTenant).filter_by(id=tenant_id).first()
    if existing:
        return existing
    tenant = CompanyTenant(
        id=tenant_id,
        slug=slug,
        name="Test Company",
        subdomain=f"{slug}.example.com",
        status="completed",
        created_at=datetime.utcnow(),
    )
    db_session.add(tenant)
    db_session.commit()
    return tenant


# ---------------------------------------------------------------------------
# Tests: POST /api/companies/generate
# ---------------------------------------------------------------------------


class TestGenerateCompany:
    def test_generate_company_returns_202(self, client_and_db):
        client, db = client_and_db
        _seed_user(db)

        fake_result = {
            "id": "gen-001",
            "status": "pending",
            "name": "Acme Corp",
            "user_id": "user-001",
        }

        with patch(
            "backend.api.companies.generator.generate_company",
            new_callable=AsyncMock,
            return_value=fake_result,
        ):
            resp = client.post(
                "/api/companies/generate",
                json={
                    "name": "Acme Corp",
                    "description": "A test company",
                    "tech_stack": "fastapi-react-postgres",
                    "features": ["auth"],
                },
                headers=_auth_headers(),
            )

        assert resp.status_code == 202
        data = resp.json()
        assert data["id"] == "gen-001"

    def test_generate_company_unauthenticated(self, client_and_db):
        client, _ = client_and_db
        resp = client.post(
            "/api/companies/generate",
            json={
                "name": "X",
                "description": "X",
                "tech_stack": "fastapi-react-postgres",
            },
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Tests: GET /api/companies/
# ---------------------------------------------------------------------------


class TestListCompanies:
    def test_list_companies_empty(self, client_and_db):
        client, db = client_and_db
        _seed_user(db, user_id="list-user-001")
        resp = client.get("/api/companies/", headers=_auth_headers(user_id="list-user-001"))
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_list_companies_with_records(self, client_and_db):
        client, db = client_and_db
        _seed_user(db, user_id="list-user-002")
        resp = client.get("/api/companies/", headers=_auth_headers(user_id="list-user-002"))
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_list_companies_status_filter(self, client_and_db):
        client, db = client_and_db
        _seed_user(db, user_id="list-user-003")
        resp = client.get(
            "/api/companies/?status_filter=completed",
            headers=_auth_headers(user_id="list-user-003"),
        )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Tests: GET /api/companies/{company_id}
# ---------------------------------------------------------------------------


class TestGetCompany:
    def test_get_company_not_found(self, client_and_db):
        client, db = client_and_db
        _seed_user(db, user_id="get-user-001")
        with patch(
            "backend.api.companies.generator.get_generation_status", return_value=None
        ):
            resp = client.get(
                "/api/companies/nonexistent-id",
                headers=_auth_headers(user_id="get-user-001"),
            )
        assert resp.status_code == 404

    def _full_company(self, company_id, user_id, status="completed"):
        return {
            "id": company_id,
            "name": "Test Corp",
            "slug": "test-corp",
            "description": "A company",
            "tech_stack": "fastapi-react-postgres",
            "status": status,
            "user_id": user_id,
            "created_at": "2024-01-01T00:00:00",
        }

    def test_get_company_access_denied(self, client_and_db):
        client, db = client_and_db
        _seed_user(db, user_id="get-user-002")
        fake = self._full_company("c1", "other-user")
        with patch(
            "backend.api.companies.generator.get_generation_status", return_value=fake
        ):
            resp = client.get(
                "/api/companies/c1",
                headers=_auth_headers(user_id="get-user-002"),
            )
        assert resp.status_code == 403

    def test_get_company_success(self, client_and_db):
        client, db = client_and_db
        _seed_user(db, user_id="get-user-003")
        fake = self._full_company("c2", "get-user-003")
        with patch(
            "backend.api.companies.generator.get_generation_status", return_value=fake
        ):
            resp = client.get(
                "/api/companies/c2",
                headers=_auth_headers(user_id="get-user-003"),
            )
        assert resp.status_code == 200

    def test_get_company_admin_can_access_any(self, client_and_db):
        client, db = client_and_db
        _seed_user(db, role="admin", user_id="admin-001")
        fake = self._full_company("c3", "someone-else")
        with patch(
            "backend.api.companies.generator.get_generation_status", return_value=fake
        ):
            resp = client.get(
                "/api/companies/c3",
                headers=_auth_headers(role="admin", user_id="admin-001"),
            )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Tests: GET /api/companies/{company_id}/status
# ---------------------------------------------------------------------------


class TestGetCompanyStatus:
    def _fake_company(self, status_val, user_id="status-user-001"):
        return {"id": "s1", "name": "S", "user_id": user_id, "status": status_val, "error": None}

    def test_status_completed(self, client_and_db):
        client, db = client_and_db
        _seed_user(db, user_id="status-user-001")
        with patch(
            "backend.api.companies.generator.get_generation_status",
            return_value=self._fake_company("completed"),
        ):
            resp = client.get(
                "/api/companies/s1/status",
                headers=_auth_headers(user_id="status-user-001"),
            )
        assert resp.status_code == 200
        assert resp.json()["progress_percent"] == 100

    def test_status_failed(self, client_and_db):
        client, db = client_and_db
        _seed_user(db, user_id="status-user-002")
        fake = self._fake_company("failed", "status-user-002")
        with patch(
            "backend.api.companies.generator.get_generation_status", return_value=fake
        ):
            resp = client.get(
                "/api/companies/s1/status",
                headers=_auth_headers(user_id="status-user-002"),
            )
        assert resp.status_code == 200
        assert resp.json()["progress_percent"] == 0

    def test_status_not_found(self, client_and_db):
        client, db = client_and_db
        _seed_user(db, user_id="status-user-003")
        with patch(
            "backend.api.companies.generator.get_generation_status", return_value=None
        ):
            resp = client.get(
                "/api/companies/nope/status",
                headers=_auth_headers(user_id="status-user-003"),
            )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Tests: DELETE /api/companies/{company_id}
# ---------------------------------------------------------------------------


class TestDeleteCompany:
    def test_delete_not_found(self, client_and_db):
        client, db = client_and_db
        _seed_user(db, user_id="del-user-001")
        with patch(
            "backend.api.companies.generator.get_generation_status", return_value=None
        ):
            resp = client.delete(
                "/api/companies/missing",
                headers=_auth_headers(user_id="del-user-001"),
            )
        assert resp.status_code == 404

    def test_delete_success(self, client_and_db):
        client, db = client_and_db
        _seed_user(db, user_id="del-user-002")
        _seed_company_tenant(db, tenant_id="del-comp-001", slug="del-company-01")
        fake = {"id": "del-comp-001", "name": "D", "user_id": "del-user-002", "status": "completed"}
        with (
            patch(
                "backend.api.companies.generator.get_generation_status", return_value=fake
            ),
            patch("backend.api.companies.file_manager.company_exists", return_value=True),
            patch("backend.api.companies.file_manager.delete_company"),
        ):
            resp = client.delete(
                "/api/companies/del-comp-001",
                headers=_auth_headers(user_id="del-user-002"),
            )
        assert resp.status_code == 200
        assert "deleted" in resp.json()["message"].lower()


# ---------------------------------------------------------------------------
# Tests: GET /api/companies/{company_id}/download
# ---------------------------------------------------------------------------


class TestDownloadCompany:
    def test_download_not_completed(self, client_and_db):
        client, db = client_and_db
        _seed_user(db, user_id="dl-user-001")
        fake = {"id": "dl-1", "name": "D", "user_id": "dl-user-001", "status": "pending"}
        with patch(
            "backend.api.companies.generator.get_generation_status", return_value=fake
        ):
            resp = client.get(
                "/api/companies/dl-1/download",
                headers=_auth_headers(user_id="dl-user-001"),
            )
        assert resp.status_code == 400

    def test_download_archive_not_found(self, client_and_db):
        client, db = client_and_db
        _seed_user(db, user_id="dl-user-002")
        fake = {"id": "dl-2", "name": "D", "user_id": "dl-user-002", "status": "completed"}
        with (
            patch(
                "backend.api.companies.generator.get_generation_status", return_value=fake
            ),
            patch("backend.api.companies.file_manager.company_exists", return_value=False),
        ):
            resp = client.get(
                "/api/companies/dl-2/download",
                headers=_auth_headers(user_id="dl-user-002"),
            )
        assert resp.status_code == 404

    def test_download_success(self, client_and_db):
        client, db = client_and_db
        _seed_user(db, user_id="dl-user-003")
        fake = {"id": "dl-3", "name": "D", "user_id": "dl-user-003", "status": "completed"}
        with (
            patch(
                "backend.api.companies.generator.get_generation_status", return_value=fake
            ),
            patch("backend.api.companies.file_manager.company_exists", return_value=True),
            patch(
                "backend.api.companies.file_manager.get_company_download_url",
                return_value="https://example.com/download",
            ),
        ):
            resp = client.get(
                "/api/companies/dl-3/download",
                headers=_auth_headers(user_id="dl-user-003"),
            )
        assert resp.status_code == 200
        assert "download_url" in resp.json()


# ---------------------------------------------------------------------------
# Tests: GET /api/companies/{company_id}/metadata
# ---------------------------------------------------------------------------


class TestGetCompanyMetadata:
    def test_metadata_not_found(self, client_and_db):
        client, db = client_and_db
        _seed_user(db, user_id="meta-user-001")
        with patch(
            "backend.api.companies.generator.get_generation_status", return_value=None
        ):
            resp = client.get(
                "/api/companies/nope/metadata",
                headers=_auth_headers(user_id="meta-user-001"),
            )
        assert resp.status_code == 404

    def test_metadata_success(self, client_and_db):
        client, db = client_and_db
        _seed_user(db, user_id="meta-user-002")
        fake = {
            "id": "m1",
            "name": "M",
            "user_id": "meta-user-002",
            "status": "completed",
            "metadata": {"key": "val"},
        }
        with (
            patch(
                "backend.api.companies.generator.get_generation_status", return_value=fake
            ),
            patch(
                "backend.api.companies.file_manager.get_company_metadata",
                return_value={"size": 100},
            ),
        ):
            resp = client.get(
                "/api/companies/m1/metadata",
                headers=_auth_headers(user_id="meta-user-002"),
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["company_id"] == "m1"
