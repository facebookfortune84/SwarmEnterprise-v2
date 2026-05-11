import os

BASE_DIR = "/mnt/c/SwarmEnterprise_v2"

def write_file(path, content):
    full_path = os.path.join(BASE_DIR, path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(content.strip() + "\n")
    print(f"[✓] Generated: {path}")

def generate_phase2():
    print("==========================================")
    print(" SWARM OS GENERATOR: PHASE 2 (MONETIZATION)")
    print("==========================================")

    # 1. REPLICATOR (The Box Builder)
    write_file("backend/replicator.py", r"""
import os
import shutil
import uuid
import logging

logger = logging.getLogger("Replicator")

class SwarmReplicator:
    """Packages the generated code into a sovereign downloadable asset."""
    
    @staticmethod
    def create_company_bundle(project_id: str):
        pkg_id = uuid.uuid4().hex[:6].upper()
        zip_name = f"SwarmOS_{project_id}_{pkg_id}"
        zip_output_path = f"/mnt/c/SwarmEnterprise_v2/output/{zip_name}"
        temp_dir = f"/tmp/{pkg_id}"
        
        try:
            if os.path.exists(temp_dir): shutil.rmtree(temp_dir)
            # Copies the generated project output
            shutil.copytree(f"/mnt/c/SwarmEnterprise_v2/output/src/{project_id}", temp_dir)
            
            # Zip it up
            shutil.make_archive(zip_output_path, 'zip', temp_dir)
            shutil.rmtree(temp_dir)
            
            download_url = f"https://corp.realms2riches.com/api/download/{zip_name}.zip"
            logger.info(f"BUNDLE READY: {download_url}")
            return {"status": "success", "download_url": download_url}
        except Exception as e:
            logger.error(f"Replication failed: {e}")
            return {"status": "error", "message": str(e)}

replicator_engine = SwarmReplicator()
""")

    # 2. STRIPE WEBHOOKS
    write_file("backend/api/webhooks.py", r"""
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
        logger.error(f"Stripe signature failed: {e}")
        raise HTTPException(status_code=400, detail="Invalid signature")

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        customer_email = session.get('customer_details', {}).get('email')
        project_id = session.get('metadata', {}).get('project_id', 'DEFAULT')
        
        logger.info(f"PAYMENT RECEIVED from {customer_email}. Delivering Box...")
        
        # Trigger Replicator
        bundle = replicator_engine.create_company_bundle(project_id)
        
        if bundle['status'] == 'success':
            email_sender = EmailTools()
            body = f"<h1>Your SwarmOS Box is Ready</h1><p>Download: <a href='{bundle['download_url']}'>Here</a></p>"
            email_sender.send_email(customer_email, "Your Programmable Company Delivery", body)
            
    return {"status": "success"}
""")

    # 3. EMAIL ENGINE (Outreach & Delivery)
    write_file("agents/outreach/email_engine.py", r"""
import smtplib
import os
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger("EmailEngine")

class EmailTools:
    """Handles Cold Outreach and Product Delivery via SMTP"""
    def __init__(self):
        self.server = os.getenv("SMTP_SERVER", "smtp.realms2riches.com")
        self.port = int(os.getenv("SMTP_PORT", 587))
        self.user = os.getenv("SMTP_USER", "sales@realms2riches.com")
        self.password = os.getenv("SMTP_PASS", "")

    def send_email(self, to_email: str, subject: str, html_body: str):
        if not self.password:
            logger.warning(f"SMTP not configured. Mocking email to {to_email}: {subject}")
            return "SUCCESS (MOCKED)"
            
        msg = MIMEMultipart()
        msg['From'] = self.user
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(html_body, 'html'))

        try:
            with smtplib.SMTP(self.server, self.port) as s:
                s.starttls()
                s.login(self.user, self.password)
                s.send_message(msg)
            logger.info(f"Email delivered to {to_email}")
            return "SUCCESS"
        except Exception as e:
            logger.error(f"Email delivery failed: {e}")
            return f"ERROR: {e}"
""")

    # 4. MARKETING AGENT
    write_file("agents/marketing/content_creator.py", r"""
from crewai import Agent
from agents.llm_config import LOCAL_BRAIN

class MarketingContentCreator:
    """Reads finished projects and writes high-converting sales copy"""
    def __init__(self):
        self.agent = Agent(
            role="Marketing Director",
            goal="Write a 1-page sales spec for the newly built autonomous app.",
            backstory="You are a brilliant SaaS marketer. You analyze code features and translate them into $49,999 value propositions.",
            llm=LOCAL_BRAIN,
            verbose=True
        )
""")

    print("\n[✓] PHASE 2 GENERATION COMPLETE.")

if __name__ == "__main__":
    generate_phase2()