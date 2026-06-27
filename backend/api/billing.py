"""
Billing API endpoints for generating invoices, recording usage events,
and marking invoices as paid. This module handles PDF generation,
email notifications, and usage tracking for billing reconciliation.
"""

import logging
import os
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from backend.db.linear_engine import get_swarm_db
from agents.outreach.email_engine import EmailTools

router = APIRouter(prefix="/api/billing", tags=["Billing"])
logger = logging.getLogger("Billing")

# Output directory for invoice PDFs
_DEFAULT_OUT = Path(__file__).resolve().parents[2] / "output"
_out_env = os.getenv("SWARM_OUTPUT_DIR", "").strip()
OUT_DIR = (Path(_out_env) if _out_env else _DEFAULT_OUT) / "invoices"
OUT_DIR.mkdir(parents=True, exist_ok=True)


class InvoicePayload(BaseModel):
    """Payload for invoice creation."""

    project_id: str
    customer_email: str
    amount_cents: int
    description: str | None = None


@router.post("/invoice")
async def create_invoice(payload: InvoicePayload):
    """
    Create an invoice PDF, record a usage event, and optionally email the invoice.

    Args:
        payload (InvoicePayload): Invoice metadata and billing details.

    Returns:
        dict: Invoice ID and file path.
    """
    db = get_swarm_db()
    invoice_id = uuid.uuid4().hex[:12].upper()
    filename = OUT_DIR / f"invoice_{invoice_id}.pdf"

    # Generate PDF invoice
    try:
        pdf = canvas.Canvas(str(filename), pagesize=letter)
        _, height = letter

        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawString(72, height - 72, "SwarmOS Invoice")

        pdf.setFont("Helvetica", 12)
        pdf.drawString(72, height - 100, f"Invoice ID: {invoice_id}")
        pdf.drawString(72, height - 120, f"Project ID: {payload.project_id}")
        pdf.drawString(72, height - 140, f"Customer: {payload.customer_email}")
        pdf.drawString(
            72,
            height - 160,
            f"Amount: ${payload.amount_cents / 100:.2f}",
        )

        if payload.description:
            pdf.drawString(72, height - 180, f"Description: {payload.description}")

        pdf.drawString(72, height - 220, "Thank you for using SwarmOS.")
        pdf.showPage()
        pdf.save()

    except Exception as exc:
        logger.exception("Failed to create invoice PDF")
        raise HTTPException(
            status_code=500,
            detail="Invoice generation failed",
        ) from exc

    # Record usage event
    try:
        db.record_usage(
            payload.project_id,
            event_type="invoice_created",
            amount=str(payload.amount_cents),
            metadata={
                "invoice_id": invoice_id,
                "description": payload.description,
            },
        )
    except Exception as exc:
        logger.exception("Failed to record usage event: %s", exc)

    # Email invoice (best effort) — track delivery outcome
    email_delivered = False
    email_error: str | None = None
    try:
        emailer = EmailTools()
        subject = f"Invoice {invoice_id} from SwarmOS"
        body = (
            f"<p>Dear {payload.customer_email},</p>"
            f"<p>Your invoice <strong>{invoice_id}</strong> for "
            f"${payload.amount_cents / 100:.2f} is ready.</p>"
            f"<p>{payload.description or ''}</p>"
            "<p>Thank you for using SwarmOS.</p>"
        )
        emailer.send_email(payload.customer_email, subject, body)
        email_delivered = True
        logger.info("Invoice email sent to %s for invoice %s", payload.customer_email, invoice_id)
    except Exception as exc:
        email_error = str(exc)
        logger.exception("Failed to send invoice email: %s", exc)

    # Record email delivery status
    try:
        db.record_usage(
            payload.project_id,
            event_type="invoice_email_sent" if email_delivered else "invoice_email_failed",
            amount=None,
            metadata={
                "invoice_id": invoice_id,
                "recipient": payload.customer_email,
                "error": email_error,
            },
        )
    except Exception as exc:
        logger.exception("Failed to record email delivery event: %s", exc)

    return {
        "invoice_id": invoice_id,
        "path": str(filename),
        "email_delivered": email_delivered,
    }


@router.post("/mark_paid/{invoice_id}")
async def mark_invoice_paid(invoice_id: str):
    """
    Mark an invoice as paid by recording a usage event.

    Args:
        invoice_id (str): The invoice identifier.

    Returns:
        dict: Status and invoice ID.
    """
    db = get_swarm_db()

    try:
        db.record_usage(
            None,
            event_type="invoice_paid",
            amount=None,
            metadata={"invoice_id": invoice_id},
        )
    except Exception as exc:
        logger.exception("Failed to record invoice paid event: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to mark invoice paid",
        ) from exc

    return {"status": "ok", "invoice_id": invoice_id}
