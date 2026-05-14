from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.db.linear_engine import get_swarm_db
from agents.outreach.email_engine import EmailTools
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from pathlib import Path
import uuid
import os
import logging

router = APIRouter(prefix="/api/billing", tags=["Billing"])
logger = logging.getLogger("Billing")

OUT_DIR = Path(os.getenv("SWARM_OUTPUT_DIR", "/mnt/c/SwarmEnterprise_v2/output")) / "invoices"
OUT_DIR.mkdir(parents=True, exist_ok=True)

class InvoicePayload(BaseModel):
    project_id: str
    customer_email: str
    amount_cents: int
    description: str | None = None


@router.post("/invoice")
async def create_invoice(payload: InvoicePayload):
    """Create an invoice PDF for a project and record a usage event. This is an offline, self-hosted billing flow (FOSS).

    The resulting PDF is stored in the repo output directory and (optionally) emailed using configured SMTP.
    """
    db = get_swarm_db()
    invoice_id = uuid.uuid4().hex[:12].upper()
    filename = OUT_DIR / f"invoice_{invoice_id}.pdf"

    # Generate a simple PDF invoice
    try:
        c = canvas.Canvas(str(filename), pagesize=letter)
        width, height = letter
        c.setFont("Helvetica-Bold", 16)
        c.drawString(72, height - 72, "SwarmOS Invoice")
        c.setFont("Helvetica", 12)
        c.drawString(72, height - 100, f"Invoice ID: {invoice_id}")
        c.drawString(72, height - 120, f"Project ID: {payload.project_id}")
        c.drawString(72, height - 140, f"Customer: {payload.customer_email}")
        c.drawString(72, height - 160, f"Amount: ${payload.amount_cents / 100:.2f}")
        if payload.description:
            c.drawString(72, height - 180, f"Description: {payload.description}")
        c.drawString(72, height - 220, "Thank you for using SwarmOS.")
        c.showPage()
        c.save()
    except Exception as e:
        logger.exception("Failed to create invoice PDF")
        raise HTTPException(status_code=500, detail="Invoice generation failed")

    # Record usage event for billing reconciliation
    try:
        db.record_usage(payload.project_id, event_type="invoice_created", amount=str(payload.amount_cents), metadata={"invoice_id": invoice_id, "description": payload.description})
    except Exception:
        logger.exception("Failed to record usage event")

    # Email invoice if SMTP configured
    try:
        emailer = EmailTools()
        subject = f"Invoice {invoice_id} from SwarmOS"
        body = f"<p>Please find your invoice attached: {filename.name}</p>"
        # EmailTools currently sends HTML body only; attach link to output directory
        emailer.send_email(payload.customer_email, subject, body)
    except Exception:
        logger.exception("Failed to send invoice email (best-effort)")

    return {"invoice_id": invoice_id, "path": str(filename)}


@router.post("/mark_paid/{invoice_id}")
async def mark_invoice_paid(invoice_id: str):
    # Find usage events with invoice_id metadata and mark as paid
    db = get_swarm_db()
    # This is a simple implementation: record a usage event marking payment
    try:
        db.record_usage(None, event_type="invoice_paid", amount=None, metadata={"invoice_id": invoice_id})
    except Exception:
        logger.exception("Failed to record invoice paid event")
        raise HTTPException(status_code=500, detail="Failed to mark invoice paid")
    return {"status": "ok", "invoice_id": invoice_id}
