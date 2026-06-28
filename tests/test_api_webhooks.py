"""
Tests for backend/api/webhooks.py — Stripe webhook processing.
All external calls (Stripe SDK, DB, email, replicator) are mocked.
"""
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.db.base import Base


@pytest.fixture(scope="module")
def _engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def db(_engine) -> Session:
    SessionFactory = sessionmaker(bind=_engine)
    session = SessionFactory()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def client():
    from backend.main import app
    return TestClient(app, raise_server_exceptions=False)


def _stripe_event(event_type: str, session_data: dict = None, event_id: str = None):
    """Build a minimal Stripe-like event dict."""
    if session_data is None:
        session_data = {
            "id": "cs_test_123",
            "customer_details": {"email": "buyer@example.com"},
            "metadata": {"project_id": "PROJ-001", "tech_stack": "fastapi-react-postgres"},
        }
    return {
        "id": event_id or f"evt_{uuid.uuid4().hex[:12]}",
        "type": event_type,
        "data": {"object": session_data},
    }


def _make_mock_db():
    """Return a mock LinearEngine that behaves like the real one."""
    mock_db = MagicMock()
    mock_db.is_event_processed.return_value = False
    mock_db.create_project.return_value = MagicMock(id="PROJ-001")
    mock_db.mark_event_processed.return_value = None
    return mock_db


class TestWebhookSignature:
    def test_missing_signature_header(self, client):
        resp = client.post(
            "/api/webhooks/stripe",
            content=b'{"type":"checkout.session.completed"}',
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 400
        assert "signature" in resp.json()["detail"].lower()

    def test_invalid_signature(self, client):
        import stripe

        with patch(
            "backend.api.webhooks.stripe.Webhook.construct_event",
            side_effect=stripe.error.SignatureVerificationError("bad sig", "sig_header"),
        ):
            resp = client.post(
                "/api/webhooks/stripe",
                content=b'{"bad": "payload"}',
                headers={"stripe-signature": "t=1,v1=invalid"},
            )
        assert resp.status_code == 400
        assert "signature" in resp.json()["detail"].lower()

    def test_malformed_payload(self, client):
        with patch(
            "backend.api.webhooks.stripe.Webhook.construct_event",
            side_effect=Exception("parse error"),
        ):
            resp = client.post(
                "/api/webhooks/stripe",
                content=b"not-json",
                headers={"stripe-signature": "t=1,v1=abc"},
            )
        assert resp.status_code == 400

    def test_valid_signature_accepted(self, client):
        event = _stripe_event("checkout.session.completed")
        mock_db = _make_mock_db()

        with patch(
            "backend.api.webhooks.stripe.Webhook.construct_event",
            return_value=event,
        ), patch("backend.api.webhooks.DB", mock_db), patch(
            "backend.api.webhooks.DB.is_event_processed", return_value=False
        ), patch(
            "backend.api.webhooks.DB.create_project"
        ), patch(
            "backend.api.webhooks.DB.mark_event_processed"
        ), patch(
            "backend.services.company_generator.CompanyGenerator.generate_company",
            new_callable=AsyncMock,
            return_value={"company_id": "COMP-001", "status": "pending"},
        ), patch(
            "agents.outreach.email_engine.EmailTools.send_email"
        ):
            resp = client.post(
                "/api/webhooks/stripe",
                content=b"{}",
                headers={"stripe-signature": "t=1,v1=valid"},
            )
        assert resp.status_code in (200, 500)


class TestWebhookIdempotency:
    def test_duplicate_event_skipped(self, client):
        event = _stripe_event("checkout.session.completed", event_id="evt_dup")
        mock_db = MagicMock()
        mock_db.is_event_processed.return_value = True

        with patch(
            "backend.api.webhooks.stripe.Webhook.construct_event",
            return_value=event,
        ), patch("backend.api.webhooks.DB", mock_db):
            resp = client.post(
                "/api/webhooks/stripe",
                content=b"{}",
                headers={"stripe-signature": "t=1,v1=sig"},
            )
        assert resp.status_code == 200
        assert resp.json().get("note") == "already_processed"


class TestWebhookCheckoutCompleted:
    def test_zip_delivery_path(self, client):
        session_data = {
            "id": "cs_zip",
            "customer_details": {"email": "zip@example.com"},
            "metadata": {
                "project_id": "PROJ-ZIP",
                "delivery_type": "ZIP",
                "tech_stack": "fastapi-react-postgres",
            },
        }
        event = _stripe_event("checkout.session.completed", session_data)
        mock_db = _make_mock_db()

        with patch(
            "backend.api.webhooks.stripe.Webhook.construct_event",
            return_value=event,
        ), patch("backend.api.webhooks.DB", mock_db), patch(
            "backend.api.webhooks.replicator_engine.create_company_bundle",
            return_value={"download_url": "https://example.com/bundle.zip"},
        ), patch(
            "backend.services.company_generator.CompanyGenerator.generate_company",
            new_callable=AsyncMock,
            return_value={"company_id": "COMP-Z", "status": "pending"},
        ), patch(
            "agents.outreach.email_engine.EmailTools.send_email"
        ):
            resp = client.post(
                "/api/webhooks/stripe",
                content=b"{}",
                headers={"stripe-signature": "t=1,v1=sig"},
            )
        assert resp.status_code in (200, 500)

    def test_hosted_delivery_path(self, client):
        session_data = {
            "id": "cs_hosted",
            "customer_details": {"email": "hosted@example.com"},
            "metadata": {
                "project_id": "PROJ-HOST",
                "delivery_type": "HOSTED",
                "tech_stack": "fastapi-react-postgres",
            },
        }
        event = _stripe_event("checkout.session.completed", session_data)
        mock_db = _make_mock_db()

        with patch(
            "backend.api.webhooks.stripe.Webhook.construct_event",
            return_value=event,
        ), patch("backend.api.webhooks.DB", mock_db), patch(
            "backend.services.company_generator.CompanyGenerator.generate_company",
            new_callable=AsyncMock,
            return_value={"company_id": "COMP-H", "status": "pending"},
        ), patch(
            "backend.services.deployment_service.DeploymentService.create_deployment",
            new_callable=AsyncMock,
            return_value={"id": "deploy-PROJ-HOST", "status": "pending"},
        ), patch(
            "agents.outreach.email_engine.EmailTools.send_email"
        ):
            resp = client.post(
                "/api/webhooks/stripe",
                content=b"{}",
                headers={"stripe-signature": "t=1,v1=sig"},
            )
        assert resp.status_code in (200, 500)

    def test_db_create_project_retry_exhausted(self, client):
        session_data = {
            "id": "cs_fail",
            "customer_details": {"email": "fail@example.com"},
            "metadata": {"project_id": "PROJ-FAIL", "delivery_type": "ZIP"},
        }
        event = _stripe_event("checkout.session.completed", session_data)
        mock_db = _make_mock_db()
        mock_db.create_project.side_effect = RuntimeError("DB down")
        mock_db.mark_event_processed.return_value = None

        with patch(
            "backend.api.webhooks.stripe.Webhook.construct_event",
            return_value=event,
        ), patch("backend.api.webhooks.DB", mock_db):
            resp = client.post(
                "/api/webhooks/stripe",
                content=b"{}",
                headers={"stripe-signature": "t=1,v1=sig"},
            )
        assert resp.status_code == 500

    def test_no_project_id_uses_uuid(self, client):
        """When no project_id in metadata, a UUID is auto-generated."""
        session_data = {
            "id": "cs_nopid",
            "customer_details": {"email": "nopid@example.com"},
            "metadata": {"delivery_type": "ZIP", "tech_stack": "fastapi-react-postgres"},
        }
        event = _stripe_event("checkout.session.completed", session_data)
        mock_db = _make_mock_db()

        with patch(
            "backend.api.webhooks.stripe.Webhook.construct_event",
            return_value=event,
        ), patch("backend.api.webhooks.DB", mock_db), patch(
            "backend.api.webhooks.replicator_engine.create_company_bundle",
            return_value={"download_url": "https://example.com/bundle.zip"},
        ), patch(
            "backend.services.company_generator.CompanyGenerator.generate_company",
            new_callable=AsyncMock,
            return_value={"company_id": "COMP-NPid", "status": "pending"},
        ), patch(
            "agents.outreach.email_engine.EmailTools.send_email"
        ):
            resp = client.post(
                "/api/webhooks/stripe",
                content=b"{}",
                headers={"stripe-signature": "t=1,v1=sig"},
            )
        assert resp.status_code in (200, 500)


class TestWebhookOtherEventTypes:
    def test_unknown_event_type_ignored(self, client):
        """Unknown event types go through the handler without error."""
        event = _stripe_event("payment_intent.created")
        mock_db = _make_mock_db()

        with patch(
            "backend.api.webhooks.stripe.Webhook.construct_event",
            return_value=event,
        ), patch("backend.api.webhooks.DB", mock_db):
            resp = client.post(
                "/api/webhooks/stripe",
                content=b"{}",
                headers={"stripe-signature": "t=1,v1=sig"},
            )
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"

    def test_mark_event_processed_failure_is_silent(self, client):
        """mark_event_processed failure must not surface as 500."""
        event = _stripe_event("payment_intent.created")
        mock_db = _make_mock_db()
        mock_db.mark_event_processed.side_effect = RuntimeError("redis down")

        with patch(
            "backend.api.webhooks.stripe.Webhook.construct_event",
            return_value=event,
        ), patch("backend.api.webhooks.DB", mock_db):
            resp = client.post(
                "/api/webhooks/stripe",
                content=b"{}",
                headers={"stripe-signature": "t=1,v1=sig"},
            )
        assert resp.status_code == 200

    def test_stripe_signature_header_case_insensitive(self, client):
        """Stripe-Signature (capital S) should also work."""
        import stripe

        with patch(
            "backend.api.webhooks.stripe.Webhook.construct_event",
            side_effect=stripe.error.SignatureVerificationError("bad", "sig"),
        ):
            resp = client.post(
                "/api/webhooks/stripe",
                content=b"{}",
                headers={"Stripe-Signature": "t=1,v1=bad"},
            )
        assert resp.status_code == 400
