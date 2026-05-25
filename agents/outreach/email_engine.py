import smtplib
import os
import logging
import time
from threading import Lock
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger("EmailEngine")


class EmailTools:
    """Handles Cold Outreach and Product Delivery via SMTP with retries, rate limiting, and provider fallback"""

    # Shared rate-limiting state across instances
    _lock = Lock()
    _last_sent_ts = 0.0

    def __init__(self):
        # Primary provider
        primary = {
            "server": os.getenv("SMTP_SERVER", "smtp.realms2riches.com"),
            "port": int(os.getenv("SMTP_PORT", 587)),
            "user": os.getenv("SMTP_USER", "sales@realms2riches.com"),
            "password": os.getenv("SMTP_PASS", ""),
        }

        # Parse fallbacks from env: comma-separated server:port:user:pass
        fallbacks = []
        fb_raw = os.getenv("SMTP_FALLBACKS", "").strip()
        if fb_raw:
            for part in fb_raw.split(","):
                try:
                    server, port, user, password = part.split(":", 3)
                    fallbacks.append(
                        {"server": server, "port": int(port), "user": user, "password": password}
                    )
                except ValueError:
                    logger.warning(f"Invalid SMTP_FALLBACKS entry skipped: {part}")

        # Combine primary then fallbacks
        self.providers = [primary] + fallbacks

        # messages per minute
        self.rate_per_min = int(os.getenv("SMTP_RATE_LIMIT_PER_MIN", 60))
        self.min_interval = 60.0 / max(1, self.rate_per_min)
        # retry policy per provider
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
        # If no provider has a password configured, operate in mock mode
        if not any(p.get("password") for p in self.providers):
            logger.warning(
                f"No SMTP credentials configured. Mocking email to {to_email}: {subject}"
            )
            return "SUCCESS (MOCKED)"

        msg = MIMEMultipart()
        msg["From"] = self.providers[0]["user"]
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(html_body, "html"))

        # Try each provider in order, with retries per provider
        last_error = None
        for provider in self.providers:
            server = provider["server"]
            port = provider.get("port", 587)
            user = provider.get("user")
            password = provider.get("password")

            attempt = 0
            while attempt < self.max_retries:
                attempt += 1
                try:
                    # Rate limiting slot
                    self._acquire_rate_slot()

                    with smtplib.SMTP(server, port, timeout=30) as s:
                        s.starttls()
                        if user and password:
                            s.login(user, password)
                        s.send_message(msg)
                    logger.info(f"Email delivered to {to_email} via {server} (attempt {attempt})")
                    return "SUCCESS"
                except (smtplib.SMTPException, OSError) as e:
                    last_error = e
                    backoff = self.base_backoff * (2 ** (attempt - 1))
                    logger.warning(
                        f"SMTP attempt {attempt} failed for provider {server}: {e}. Backing off {backoff}s"
                    )
                    time.sleep(backoff)
                except Exception as e:
                    logger.exception(f"Unexpected error sending email via provider {server}: {e}")
                    last_error = e
                    break

            logger.info(f"Provider {server} exhausted, trying next provider if available")

        logger.error(f"All providers failed to deliver email to {to_email}: {last_error}")
        return f"ERROR: {last_error or 'all_providers_failed'}"
