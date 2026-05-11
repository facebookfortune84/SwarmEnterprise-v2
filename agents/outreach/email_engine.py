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
