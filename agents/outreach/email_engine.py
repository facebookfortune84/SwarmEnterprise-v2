import smtplib
import os
import logging
import time
from threading import Lock
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


logger = logging.getLogger("EmailEngine")

class EmailTools:
    """Handles Cold Outreach and Product Delivery via SMTP with retries and simple rate limiting"""
    # Shared rate-limiting state across instances
    _lock = Lock()
    _last_sent_ts = 0.0

    def __init__(self):
        self.server = os.getenv("SMTP_SERVER", "smtp.realms2riches.com")
        self.port = int(os.getenv("SMTP_PORT", 587))
        self.user = os.getenv("SMTP_USER", "sales@realms2riches.com")
        self.password = os.getenv("SMTP_PASS", "")
        # messages per minute
        self.rate_per_min = int(os.getenv("SMTP_RATE_LIMIT_PER_MIN", 60))
        self.min_interval = 60.0 / max(1, self.rate_per_min)
        # retry policy
        self.max_retries = int(os.getenv("SMTP_MAX_RETRIES", 3))
        self.base_backoff = float(os.getenv("SMTP_BACKOFF_BASE", 1.0))

    def _acquire_rate_slot(self):
        # Ensure spacing between messages to honor rate limit
        with EmailTools._lock:
            now = time.time()
            elapsed = now - EmailTools._last_sent_ts
            if elapsed < self.min_interval:
                to_sleep = self.min_interval - elapsed
                logger.debug(f"Rate limiting in effect, sleeping {to_sleep:.2f}s")
                time.sleep(to_sleep)
            EmailTools._last_sent_ts = time.time()

    def send_email(self, to_email: str, subject: str, html_body: str):
        if not self.password:
            logger.warning(f"SMTP not configured. Mocking email to {to_email}: {subject}")
            return "SUCCESS (MOCKED)"

        msg = MIMEMultipart()
        msg['From'] = self.user
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(html_body, 'html'))

        attempt = 0
        while attempt < self.max_retries:
            attempt += 1
            try:
                # Rate limiting slot
                self._acquire_rate_slot()

                with smtplib.SMTP(self.server, self.port, timeout=30) as s:
                    s.starttls()
                    s.login(self.user, self.password)
                    s.send_message(msg)
                logger.info(f"Email delivered to {to_email} (attempt {attempt})")
                return "SUCCESS"
            except (smtplib.SMTPException, OSError) as e:
                backoff = self.base_backoff * (2 ** (attempt - 1))
                logger.warning(f"SMTP attempt {attempt} failed: {e}. Backing off {backoff}s")
                time.sleep(backoff)
            except Exception as e:
                logger.exception(f"Unexpected error sending email: {e}")
                return f"ERROR: {e}"

        logger.error(f"Failed to deliver email to {to_email} after {self.max_retries} attempts")
        return f"ERROR: max_retries_exceeded"
