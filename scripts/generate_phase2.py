import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _paths import output_dir, output_src_dir, repo_root  # noqa: E402

BASE_DIR = repo_root()
OUT = output_dir().replace("\\", "/")
OUT_SRC = output_src_dir().replace("\\", "/")


def write_file(path, content):
    full_path = os.path.join(BASE_DIR, path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content.strip() + "\n")
    print(f"[OK] Generated: {path}")


def generate_phase2():
    print("==========================================")
    print(" SWARM OS GENERATOR: PHASE 2 (MONETIZATION)")
    print("==========================================")

    write_file(
        "backend/replicator.py",
        f"""
import logging
import os
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Optional

logger = logging.getLogger("Replicator")
_OUTPUT = Path(os.getenv("SWARM_OUTPUT_DIR", "{OUT}"))


class SwarmReplicator:
    @staticmethod
    def create_company_bundle(project_id: str, customer_email: Optional[str] = None):
        pkg_id = uuid.uuid4().hex[:6].upper()
        zip_name = f"SwarmOS_{{project_id}}_{{pkg_id}}"
        src_dir = _OUTPUT / "src" / project_id
        zip_base = _OUTPUT / zip_name
        temp_dir = Path(tempfile.mkdtemp(prefix=f"swarm_{{pkg_id}}_"))
        try:
            if not src_dir.is_dir():
                raise FileNotFoundError(f"Project output not found: {{src_dir}}")
            shutil.copytree(src_dir, temp_dir, dirs_exist_ok=True)
            shutil.make_archive(str(zip_base), "zip", str(temp_dir))
            shutil.rmtree(temp_dir, ignore_errors=True)
            url = f"https://corp.realms2riches.com/api/download/{{zip_name}}.zip"
            logger.info("BUNDLE READY: %s", url)
            return {{"status": "success", "download_url": url}}
        except Exception as e:
            logger.error("Replication failed: %s", e)
            shutil.rmtree(temp_dir, ignore_errors=True)
            return {{"status": "error", "message": str(e)}}


replicator_engine = SwarmReplicator()
""",
    )

    write_file(
        "backend/api/webhooks.py",
        """
import os
import stripe
import logging
from fastapi import APIRouter, Request, Header, HTTPException
from backend.replicator import replicator_engine
from agents.outreach.email_engine import EmailTools

router = APIRouter(prefix="/api/webhooks", tags=["Monetization"])
logger = logging.getLogger("SwarmWebhooks")

stripe.api_key = os.getenv("STRIPE_API_KEY", "sk_test_placeholder")
webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "whsec_placeholder")


@router.post("/stripe")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None)):
    payload = await request.body()
    try:
        event = stripe.Webhook.construct_event(payload, stripe_signature, webhook_secret)
    except Exception as e:
        logger.error("Stripe signature failed: %s", e)
        raise HTTPException(status_code=400, detail="Invalid signature") from e

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        customer_email = session.get("customer_details", {}).get("email")
        project_id = session.get("metadata", {}).get("project_id", "DEFAULT")
        bundle = replicator_engine.create_company_bundle(project_id, customer_email=customer_email)
        if bundle["status"] == "success" and customer_email:
            body = (
                "<h1>Your SwarmOS Box is Ready</h1>"
                f"<p>Download: <a href='{bundle['download_url']}'>Here</a></p>"
            )
            EmailTools().send_email(customer_email, "Your Programmable Company Delivery", body)
    return {"status": "success"}
""",
    )

    write_file(
        "agents/outreach/email_engine.py",
        """
import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger("EmailEngine")


class EmailTools:
    def __init__(self):
        self.server = os.getenv("SMTP_SERVER", "smtp.realms2riches.com")
        self.port = int(os.getenv("SMTP_PORT", "587"))
        self.user = os.getenv("SMTP_USER", "sales@realms2riches.com")
        self.password = os.getenv("SMTP_PASS", "")

    def send_email(self, to_email: str, subject: str, html_body: str):
        if not self.password:
            logger.warning("SMTP not configured. Mocking email to %s: %s", to_email, subject)
            return "SUCCESS (MOCKED)"
        msg = MIMEMultipart()
        msg["From"] = self.user
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(html_body, "html"))
        try:
            with smtplib.SMTP(self.server, self.port) as smtp:
                smtp.starttls()
                smtp.login(self.user, self.password)
                smtp.send_message(msg)
            logger.info("Email delivered to %s", to_email)
            return "SUCCESS"
        except Exception as e:
            logger.error("Email delivery failed: %s", e)
            return f"ERROR: {e}"
""",
    )

    write_file(
        "agents/marketing/content_creator.py",
        """
from crewai import Agent
from agents.llm_config import LOCAL_BRAIN


class MarketingContentCreator:
    def __init__(self):
        self.agent = Agent(
            role="Marketing Director",
            goal="Write a 1-page sales spec for the newly built autonomous app.",
            backstory="You translate code features into value propositions.",
            llm=LOCAL_BRAIN,
            verbose=True,
        )
""",
    )

    os.makedirs(OUT_SRC, exist_ok=True)
    print("\n[OK] PHASE 2 GENERATION COMPLETE.")


if __name__ == "__main__":
    generate_phase2()
