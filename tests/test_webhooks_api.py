"""
tests/test_webhooks_api.py
============================
Comprehensive coverage for backend/api/webhooks.py

Covers:
- POST /api/webhooks/stripe (missing signature header)
- POST /api/webhooks/stripe (invalid signature)
- POST /api/webhooks/stripe (invalid payload)
- POST /api/webhooks/stripe (duplicate event idempotency)
- POST /api/webhooks/stripe (checkout.session.completed - ZIP delivery)
- POST /api/webhooks/stripe (checkout.session.completed - HOSTED delivery)
- POST /api/webhooks/stripe (checkout.session.completed - project creation retries)
- POST /api/webhooks/stripe (non-checkout event type)
"""

import os

os.environ.setdefault("OTEL_SDK_DISABLED", "true")
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("JWT_SECRET_KEY", "ci-test-secret-key-do-not-use-in-production-64chars00")
os.environ.setdefault("SECRET_KEY", "ci-test-secret-key-do-not-use-in-production-64chars01")
os.environ.setdefault("TEST_MODE", "true")
os.environ.setdefault("CELERY_BROKER_URL", "memory://")
os.environ.setdefault("CELERY_RESULT_BACKEND", "cache+memory://")

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import stripe
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture()
def client():
    return TestClient(app, raise_server_exceptions=False)


def _make_event(event_type="checkout.session.completed", event_id="evt_001"):
    session = {
        "id": "cs_test_001",
        "customer_details": {"email": "buyer@example.com"},
        "metadata": {
            "project_id": "PROJ001",
            "delivery_type": "ZIP",
            "tech_stack": "fastapi-react-postgres",
        },
    }
    return {
        "id": event_id,
        "type": event_type,
        "data": {"object": session},
    }


def _mock_db():
    db = MagicMock()
    db.is_event_processed.return_value = False
    db.mark_event_processed.return_value = None
    db.create_project.return_value = None
    db.record_usage.return_value = None
    return db


# ---------------------------------------------------------------------------
# Tests: Signature validation
# ---------------------------------------------------------------------------


class TestStripeWebhookSignature:
    def test_missing_signature_header(self, client):
        resp = client.post(
            "/api/webhooks/stripe",
            content=b'{"type": "test"}',
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 400
        assert "signature" in resp.json()["detail"].lower()

    def test_invalid_signature(self, client):
        with patch("stripe.Webhook.construct_event") as mock_construct:
            mock_construct.side_effect = stripe.error.SignatureVerificationError(
                "Invalid signature", "sig_header"
            )
            resp = client.post(
                "/api/webhooks/stripe",
                content=b'{"type": "test"}',
                headers={
                    "Content-Type": "application/json",
                    "Stripe-Signature": "bad_sig",
                },
            )
        assert resp.status_code == 400
        assert "signature" in resp.json()["detail"].lower()

    def test_invalid_payload(self, client):
        with patch("stripe.Webhook.construct_event") as mock_construct:
            mock_construct.side_effect = Exception("Malformed JSON")
            resp = client.post(
                "/api/webhooks/stripe",
                content=b"not-json",
                headers={
                    "Content-Type": "application/octet-stream",
                    "Stripe-Signature": "sig",
                },
            )
        assert resp.status_code == 400
        assert "payload" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Tests: Idempotency
# ---------------------------------------------------------------------------


class TestStripeWebhookIdempotency:
    def test_duplicate_event_already_processed(self, client):
        mock_db = _mock_db()
        mock_db.is_event_processed.return_value = True
        event = _make_event()

        with (
            patch("stripe.Webhook.construct_event", return_value=event),
            patch("backend.api.webhooks.DB", mock_db),
        ):
            resp = client.post(
                "/api/webhooks/stripe",
                content=b"payload",
                headers={"Stripe-Signature": "sig"},
            )
        assert resp.status_code == 200
        assert resp.json()["note"] == "already_processed"


# ---------------------------------------------------------------------------
# Tests: checkout.session.completed — ZIP delivery
# ---------------------------------------------------------------------------


class TestStripeCheckoutZip:
    def test_checkout_completed_zip_delivery(self, client):
        event = _make_event()
        mock_db = _mock_db()

        with (
            patch("stripe.Webhook.construct_event", return_value=event),
            patch("backend.api.webhooks.DB", mock_db),
            patch(
                "backend.api.webhooks.replicator_engine.create_company_bundle",
                return_value={"download_url": "https://example.com/bundle.zip"},
            ),
            patch(
                "backend.services.company_generator.CompanyGenerator.generate_company",
                new_callable=AsyncMock,
                return_value={"id": "c001", "status": "completed"},
            ),
            patch("backend.api.webhooks.EmailTools") as mock_emailer,
        ):
            mock_emailer.return_value.send_email.return_value = None
            resp = client.post(
                "/api/webhooks/stripe",
                content=b"payload",
                headers={"Stripe-Signature": "sig"},
            )

        assert resp.status_code == 200
        assert resp.json()["status"] == "success"

    def test_checkout_completed_no_project_id_in_metadata(self, client):
        """When project_id is missing from metadata, a UUID is auto-generated."""
        event = {
            "id": "evt_002",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_002",
                    "customer_details": {"email": "anon@example.com"},
                    "metadata": {"delivery_type": "ZIP"},
                }
            },
        }
        mock_db = _mock_db()

        with (
            patch("stripe.Webhook.construct_event", return_value=event),
            patch("backend.api.webhooks.DB", mock_db),
            patch(
                "backend.services.company_generator.CompanyGenerator.generate_company",
                new_callable=AsyncMock,
                return_value={"id": "auto", "status": "completed"},
            ),
            patch(
                "backend.api.webhooks.replicator_engine.create_company_bundle",
                return_value={"download_url": "https://example.com/bundle.zip"},
            ),
            patch("backend.api.webhooks.EmailTools") as mock_emailer,
        ):
            mock_emailer.return_value.send_email.return_value = None
            resp = client.post(
                "/api/webhooks/stripe",
                content=b"payload",
                headers={"Stripe-Signature": "sig"},
            )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Tests: checkout.session.completed — HOSTED delivery
# ---------------------------------------------------------------------------


class TestStripeCheckoutHosted:
    def test_checkout_completed_hosted_delivery(self, client):
        session = {
            "id": "cs_hosted",
            "customer_details": {"email": "host@example.com"},
            "metadata": {
                "project_id": "PROJ-HOSTED",
                "delivery_type": "HOSTED",
                "tech_stack": "fastapi-react-postgres",
            },
        }
        event = {
            "id": "evt_hosted",
            "type": "checkout.session.completed",
            "data": {"object": session},
        }
        mock_db = _mock_db()

        with (
            patch("stripe.Webhook.construct_event", return_value=event),
            patch("backend.api.webhooks.DB", mock_db),
            patch(
                "backend.services.company_generator.CompanyGenerator.generate_company",
                new_callable=AsyncMock,
                return_value={"id": "hc", "status": "completed"},
            ),
            patch(
                "backend.services.deployment_service.DeploymentService.create_deployment",
                new_callable=AsyncMock,
                return_value={"id": "dep-001", "status": "pending"},
            ),
            patch("backend.api.webhooks.EmailTools") as mock_emailer,
        ):
            mock_emailer.return_value.send_email.return_value = None
            resp = client.post(
                "/api/webhooks/stripe",
                content=b"payload",
                headers={"Stripe-Signature": "sig"},
            )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Tests: project creation retry
# ---------------------------------------------------------------------------


class TestStripeProjectRetry:
    def test_project_creation_all_retries_fail(self, client):
        event = _make_event(event_id="evt_retry")
        mock_db = _mock_db()
        mock_db.create_project.side_effect = Exception("DB down")

        with (
            patch("stripe.Webhook.construct_event", return_value=event),
            patch("backend.api.webhooks.DB", mock_db),
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            resp = client.post(
                "/api/webhooks/stripe",
                content=b"payload",
                headers={"Stripe-Signature": "sig"},
            )
        assert resp.status_code == 500

    def test_project_creation_succeeds_on_second_attempt(self, client):
        event = _make_event(event_id="evt_retry2")
        mock_db = _mock_db()
        call_count = {"n": 0}

        def _create_project(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] < 2:
                raise Exception("transient error")

        mock_db.create_project.side_effect = _create_project

        with (
            patch("stripe.Webhook.construct_event", return_value=event),
            patch("backend.api.webhooks.DB", mock_db),
            patch("asyncio.sleep", new_callable=AsyncMock),
            patch(
                "backend.services.company_generator.CompanyGenerator.generate_company",
                new_callable=AsyncMock,
                return_value={"id": "c2", "status": "completed"},
            ),
            patch(
                "backend.api.webhooks.replicator_engine.create_company_bundle",
                return_value={"download_url": "https://example.com/b.zip"},
            ),
            patch("backend.api.webhooks.EmailTools") as mock_emailer,
        ):
            mock_emailer.return_value.send_email.return_value = None
            resp = client.post(
                "/api/webhooks/stripe",
                content=b"payload",
                headers={"Stripe-Signature": "sig"},
            )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Tests: non-checkout event type
# ---------------------------------------------------------------------------


class TestStripeNonCheckoutEvent:
    def test_non_checkout_event_processed_silently(self, client):
        event = _make_event(event_type="customer.subscription.updated", event_id="evt_sub")
        mock_db = _mock_db()

        with (
            patch("stripe.Webhook.construct_event", return_value=event),
            patch("backend.api.webhooks.DB", mock_db),
        ):
            resp = client.post(
                "/api/webhooks/stripe",
                content=b"payload",
                headers={"Stripe-Signature": "sig"},
            )
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"
        mock_db.mark_event_processed.assert_called_once_with("evt_sub")


# ---------------------------------------------------------------------------
# Tests: generate_company retry inside webhook
# ---------------------------------------------------------------------------


class TestStripeGenerateRetry:
    def test_generate_company_retries_and_succeeds(self, client):
        event = _make_event(event_id="evt_gen_retry")
        mock_db = _mock_db()
        call_count = {"n": 0}

        async def _generate(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] < 2:
                raise Exception("LLM timeout")
            return {"id": "g1", "status": "completed"}

        with (
            patch("stripe.Webhook.construct_event", return_value=event),
            patch("backend.api.webhooks.DB", mock_db),
            patch("asyncio.sleep", new_callable=AsyncMock),
            patch(
                "backend.services.company_generator.CompanyGenerator.generate_company",
                side_effect=_generate,
            ),
            patch(
                "backend.api.webhooks.replicator_engine.create_company_bundle",
                return_value={"download_url": "https://example.com/b.zip"},
            ),
            patch("backend.api.webhooks.EmailTools") as mock_emailer,
        ):
            mock_emailer.return_value.send_email.return_value = None
            resp = client.post(
                "/api/webhooks/stripe",
                content=b"payload",
                headers={"Stripe-Signature": "sig"},
            )
        assert resp.status_code == 200

    def test_generate_company_all_retries_fail_continues(self, client):
        """When generate_company fails all retries, delivery fails but
        project was already persisted — no 500 from the outer handler."""
        event = _make_event(event_id="evt_gen_fail")
        mock_db = _mock_db()

        with (
            patch("stripe.Webhook.construct_event", return_value=event),
            patch("backend.api.webhooks.DB", mock_db),
            patch("asyncio.sleep", new_callable=AsyncMock),
            patch(
                "backend.services.company_generator.CompanyGenerator.generate_company",
                new_callable=AsyncMock,
                side_effect=Exception("All LLM attempts failed"),
            ),
        ):
            resp = client.post(
                "/api/webhooks/stripe",
                content=b"payload",
                headers={"Stripe-Signature": "sig"},
            )
        # Exception in delivery block is swallowed — success returned
        assert resp.status_code == 200
