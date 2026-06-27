"""
tests/test_billing_api.py
===========================
Full coverage for backend/api/billing.py

Covers:
- POST /api/billing/invoice    (create invoice PDF + email)
- POST /api/billing/mark_paid/{invoice_id}  (mark invoice paid)
"""

import os

os.environ.setdefault("OTEL_SDK_DISABLED", "true")
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("JWT_SECRET_KEY", "ci-test-secret-key-do-not-use-in-production-64chars00")
os.environ.setdefault("SECRET_KEY", "ci-test-secret-key-do-not-use-in-production-64chars01")
os.environ.setdefault("TEST_MODE", "true")
os.environ.setdefault("CELERY_BROKER_URL", "memory://")
os.environ.setdefault("CELERY_RESULT_BACKEND", "cache+memory://")

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture()
def client():
    return TestClient(app, raise_server_exceptions=False)


def _mock_db():
    """Return a mock SwarmDB instance."""
    db = MagicMock()
    db.record_usage.return_value = None
    return db


# ---------------------------------------------------------------------------
# Tests: POST /api/billing/invoice
# ---------------------------------------------------------------------------


class TestCreateInvoice:
    def test_create_invoice_success(self, client, tmp_path):
        """Happy path: PDF created, usage recorded, email sent."""
        with (
            patch("backend.api.billing.get_swarm_db", return_value=_mock_db()),
            patch("backend.api.billing.OUT_DIR", tmp_path),
            patch("backend.api.billing.EmailTools") as mock_emailer,
        ):
            mock_emailer.return_value.send_email.return_value = None
            resp = client.post(
                "/api/billing/invoice",
                json={
                    "project_id": "PROJ-001",
                    "customer_email": "customer@example.com",
                    "amount_cents": 4999,
                    "description": "Test invoice",
                },
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "invoice_id" in data
        assert data["email_delivered"] is True

    def test_create_invoice_email_fails(self, client, tmp_path):
        """Email delivery failure: invoice still created, email_delivered=False."""
        with (
            patch("backend.api.billing.get_swarm_db", return_value=_mock_db()),
            patch("backend.api.billing.OUT_DIR", tmp_path),
            patch("backend.api.billing.EmailTools") as mock_emailer,
        ):
            mock_emailer.return_value.send_email.side_effect = Exception("SMTP error")
            resp = client.post(
                "/api/billing/invoice",
                json={
                    "project_id": "PROJ-002",
                    "customer_email": "bad@example.com",
                    "amount_cents": 9900,
                },
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["email_delivered"] is False

    def test_create_invoice_no_description(self, client, tmp_path):
        """Invoice without description field."""
        with (
            patch("backend.api.billing.get_swarm_db", return_value=_mock_db()),
            patch("backend.api.billing.OUT_DIR", tmp_path),
            patch("backend.api.billing.EmailTools") as mock_emailer,
        ):
            mock_emailer.return_value.send_email.return_value = None
            resp = client.post(
                "/api/billing/invoice",
                json={
                    "project_id": "PROJ-003",
                    "customer_email": "nodesc@example.com",
                    "amount_cents": 100,
                },
            )
        assert resp.status_code == 200

    def test_create_invoice_pdf_error(self, client, tmp_path):
        """PDF generation failure raises 500."""
        with (
            patch("backend.api.billing.get_swarm_db", return_value=_mock_db()),
            patch("backend.api.billing.OUT_DIR", tmp_path),
            patch("reportlab.pdfgen.canvas.Canvas.__init__", side_effect=Exception("PDF error")),
        ):
            resp = client.post(
                "/api/billing/invoice",
                json={
                    "project_id": "PROJ-004",
                    "customer_email": "err@example.com",
                    "amount_cents": 500,
                },
            )
        assert resp.status_code == 500

    def test_create_invoice_usage_record_fails(self, client, tmp_path):
        """Usage recording failure is non-fatal — invoice still returned."""
        mock_db = _mock_db()
        mock_db.record_usage.side_effect = Exception("DB down")
        with (
            patch("backend.api.billing.get_swarm_db", return_value=mock_db),
            patch("backend.api.billing.OUT_DIR", tmp_path),
            patch("backend.api.billing.EmailTools") as mock_emailer,
        ):
            mock_emailer.return_value.send_email.return_value = None
            resp = client.post(
                "/api/billing/invoice",
                json={
                    "project_id": "PROJ-005",
                    "customer_email": "usage@example.com",
                    "amount_cents": 200,
                },
            )
        assert resp.status_code == 200

    def test_create_invoice_validation_error(self, client):
        """Missing required fields returns 422."""
        resp = client.post(
            "/api/billing/invoice",
            json={"project_id": "P1"},  # missing customer_email, amount_cents
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Tests: POST /api/billing/mark_paid/{invoice_id}
# ---------------------------------------------------------------------------


class TestMarkInvoicePaid:
    def test_mark_paid_success(self, client):
        """Mark invoice paid records usage event."""
        with patch("backend.api.billing.get_swarm_db", return_value=_mock_db()):
            resp = client.post("/api/billing/mark_paid/INV-001")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["invoice_id"] == "INV-001"

    def test_mark_paid_db_error(self, client):
        """DB error during mark_paid raises 500."""
        mock_db = _mock_db()
        mock_db.record_usage.side_effect = Exception("DB write failed")
        with patch("backend.api.billing.get_swarm_db", return_value=mock_db):
            resp = client.post("/api/billing/mark_paid/INV-ERROR")
        assert resp.status_code == 500

    def test_mark_paid_any_invoice_id(self, client):
        """Any invoice ID string is accepted."""
        with patch("backend.api.billing.get_swarm_db", return_value=_mock_db()):
            resp = client.post("/api/billing/mark_paid/12345ABCDEF")
        assert resp.status_code == 200
        assert resp.json()["invoice_id"] == "12345ABCDEF"
