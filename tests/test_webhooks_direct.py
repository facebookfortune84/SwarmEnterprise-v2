"""
tests/test_webhooks_direct.py
================================
Direct unit tests for backend/api/webhooks.py that call the async function
directly to work around coverage measurement issues with async endpoints.
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
    return db


def _make_request(body=b"payload", signature="t=1,v1=sig"):
    """Create a mock FastAPI request."""
    req = MagicMock()
    req.body = AsyncMock(return_value=body)
    req.headers = {"stripe-signature": signature} if signature else {}
    return req


class TestStripeWebhookDirect:
    """Direct unit tests calling stripe_webhook() function to get proper coverage."""

    @pytest.mark.asyncio
    async def test_missing_signature_raises_400(self):
        from backend.api.webhooks import stripe_webhook

        req = _make_request(signature=None)
        req.headers = {}

        with pytest.raises(Exception) as exc_info:
            await stripe_webhook(req)

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_invalid_signature_raises_400(self):
        from backend.api.webhooks import stripe_webhook

        req = _make_request(signature="bad_sig")

        with patch(
            "stripe.Webhook.construct_event",
            side_effect=stripe.error.SignatureVerificationError("Invalid", "bad"),
        ):
            with pytest.raises(Exception) as exc_info:
                await stripe_webhook(req)

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_malformed_payload_raises_400(self):
        from backend.api.webhooks import stripe_webhook

        req = _make_request(signature="sig")

        with patch("stripe.Webhook.construct_event", side_effect=Exception("Parse error")):
            with pytest.raises(Exception) as exc_info:
                await stripe_webhook(req)

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_duplicate_event_returns_already_processed(self):
        from backend.api.webhooks import stripe_webhook

        req = _make_request()
        event = _make_event(event_id="evt_dup")
        mock_db = _mock_db()
        mock_db.is_event_processed.return_value = True

        with (
            patch("stripe.Webhook.construct_event", return_value=event),
            patch("backend.api.webhooks.DB", mock_db),
        ):
            result = await stripe_webhook(req)

        assert result["note"] == "already_processed"

    @pytest.mark.asyncio
    async def test_non_checkout_event_succeeds(self):
        from backend.api.webhooks import stripe_webhook

        req = _make_request()
        event = _make_event(event_type="customer.subscription.updated", event_id="evt_sub")
        mock_db = _mock_db()

        with (
            patch("stripe.Webhook.construct_event", return_value=event),
            patch("backend.api.webhooks.DB", mock_db),
        ):
            result = await stripe_webhook(req)

        assert result["status"] == "success"
        mock_db.mark_event_processed.assert_called_once_with("evt_sub")

    @pytest.mark.asyncio
    async def test_checkout_zip_delivery_success(self):
        from backend.api.webhooks import stripe_webhook

        req = _make_request()
        event = _make_event()
        mock_db = _mock_db()

        with (
            patch("stripe.Webhook.construct_event", return_value=event),
            patch("backend.api.webhooks.DB", mock_db),
            patch("asyncio.sleep", new_callable=AsyncMock),
            patch(
                "backend.services.company_generator.CompanyGenerator.generate_company",
                new_callable=AsyncMock,
                return_value={"id": "c1", "status": "completed"},
            ),
            patch(
                "backend.api.webhooks.replicator_engine.create_company_bundle",
                return_value={"download_url": "https://example.com/b.zip"},
            ),
            patch("backend.api.webhooks.EmailTools") as mock_emailer,
        ):
            mock_emailer.return_value.send_email.return_value = None
            result = await stripe_webhook(req)

        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_checkout_hosted_delivery_success(self):
        from backend.api.webhooks import stripe_webhook

        session = {
            "id": "cs_hosted",
            "customer_details": {"email": "host@example.com"},
            "metadata": {
                "project_id": "PROJ-H",
                "delivery_type": "HOSTED",
                "tech_stack": "fastapi-react-postgres",
            },
        }
        event = {
            "id": "evt_hosted",
            "type": "checkout.session.completed",
            "data": {"object": session},
        }
        req = _make_request()
        mock_db = _mock_db()

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
                "backend.services.deployment_service.DeploymentService.create_deployment",
                new_callable=AsyncMock,
                return_value={"id": "dep-001"},
            ),
            patch("backend.api.webhooks.EmailTools") as mock_emailer,
        ):
            mock_emailer.return_value.send_email.return_value = None
            result = await stripe_webhook(req)

        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_project_creation_all_retries_fail_raises_500(self):
        from backend.api.webhooks import stripe_webhook

        req = _make_request()
        event = _make_event(event_id="evt_retry_fail")
        mock_db = _mock_db()
        mock_db.create_project.side_effect = Exception("DB down")

        with (
            patch("stripe.Webhook.construct_event", return_value=event),
            patch("backend.api.webhooks.DB", mock_db),
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            with pytest.raises(Exception) as exc_info:
                await stripe_webhook(req)

        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_project_creation_retry_succeeds_on_second_attempt(self):
        from backend.api.webhooks import stripe_webhook

        req = _make_request()
        event = _make_event(event_id="evt_retry_ok")
        mock_db = _mock_db()
        call_count = {"n": 0}

        def _create(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] < 2:
                raise Exception("transient")

        mock_db.create_project.side_effect = _create

        with (
            patch("stripe.Webhook.construct_event", return_value=event),
            patch("backend.api.webhooks.DB", mock_db),
            patch("asyncio.sleep", new_callable=AsyncMock),
            patch(
                "backend.services.company_generator.CompanyGenerator.generate_company",
                new_callable=AsyncMock,
                return_value={"id": "c3", "status": "completed"},
            ),
            patch(
                "backend.api.webhooks.replicator_engine.create_company_bundle",
                return_value={"download_url": "https://example.com/b.zip"},
            ),
            patch("backend.api.webhooks.EmailTools") as mock_emailer,
        ):
            mock_emailer.return_value.send_email.return_value = None
            result = await stripe_webhook(req)

        assert result["status"] == "success"
        assert call_count["n"] == 2

    @pytest.mark.asyncio
    async def test_generate_company_all_retries_fail_non_fatal(self):
        """When generate_company fails all retries, delivery error is swallowed."""
        from backend.api.webhooks import stripe_webhook

        req = _make_request()
        event = _make_event(event_id="evt_gen_fail")
        mock_db = _mock_db()

        with (
            patch("stripe.Webhook.construct_event", return_value=event),
            patch("backend.api.webhooks.DB", mock_db),
            patch("asyncio.sleep", new_callable=AsyncMock),
            patch(
                "backend.services.company_generator.CompanyGenerator.generate_company",
                new_callable=AsyncMock,
                side_effect=Exception("LLM down"),
            ),
        ):
            result = await stripe_webhook(req)

        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_mark_event_processed_error_is_swallowed(self):
        """Error marking event processed doesn't fail the response."""
        from backend.api.webhooks import stripe_webhook

        req = _make_request()
        event = _make_event(event_type="invoice.paid", event_id="evt_mark_fail")
        mock_db = _mock_db()
        mock_db.mark_event_processed.side_effect = Exception("DB write error")

        with (
            patch("stripe.Webhook.construct_event", return_value=event),
            patch("backend.api.webhooks.DB", mock_db),
        ):
            result = await stripe_webhook(req)

        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_checkout_no_project_id_in_metadata(self):
        """Checkout session without project_id auto-generates one."""
        from backend.api.webhooks import stripe_webhook

        session = {
            "id": "cs_no_meta",
            "customer_details": {"email": "a@b.com"},
            "metadata": {"delivery_type": "ZIP"},
        }
        event = {
            "id": "evt_no_meta",
            "type": "checkout.session.completed",
            "data": {"object": session},
        }
        req = _make_request()
        mock_db = _mock_db()

        with (
            patch("stripe.Webhook.construct_event", return_value=event),
            patch("backend.api.webhooks.DB", mock_db),
            patch("asyncio.sleep", new_callable=AsyncMock),
            patch(
                "backend.services.company_generator.CompanyGenerator.generate_company",
                new_callable=AsyncMock,
                return_value={"id": "auto", "status": "completed"},
            ),
            patch(
                "backend.api.webhooks.replicator_engine.create_company_bundle",
                return_value={"download_url": "https://example.com/b.zip"},
            ),
            patch("backend.api.webhooks.EmailTools") as mock_emailer,
        ):
            mock_emailer.return_value.send_email.return_value = None
            result = await stripe_webhook(req)

        assert result["status"] == "success"
