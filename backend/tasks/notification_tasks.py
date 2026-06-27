"""
Notification-related Celery tasks.
"""
import logging
from backend.celery_app import celery_app

logger = logging.getLogger("tasks.notifications")


@celery_app.task(
    name="backend.tasks.notification_tasks.send_notification",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def send_notification(self, user_id: str, notification_data: dict):
    """
    Async notification delivery — persists to DB and pushes via WebSocket.

    Args:
        user_id: Target user ID.
        notification_data: Dict with keys: type, title, message, metadata (opt).
    """
    from backend.db.session import SessionLocal
    from backend.services.notification_service import NotificationService

    db = SessionLocal()
    try:
        svc = NotificationService(db)
        notif = svc.create_notification(
            user_id=user_id,
            type=notification_data.get("type", "info"),
            title=notification_data.get("title", ""),
            message=notification_data.get("message", ""),
            metadata=notification_data.get("metadata"),
        )
        logger.info("Delivered notification %s to user %s", notif.id, user_id)
        return {"ok": True, "notification_id": notif.id}
    except Exception as exc:
        logger.exception("send_notification failed for user %s", user_id)
        raise self.retry(exc=exc)
    finally:
        db.close()


@celery_app.task(
    name="backend.tasks.notification_tasks.send_email_notification",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_email_notification(self, email: str, subject: str, body: str):
    """
    Email delivery via SMTP or a configured provider.

    Falls back to a log warning when no SMTP host is configured so that
    the task never hard-fails in environments without email configured.

    Args:
        email: Recipient address.
        subject: Email subject line.
        body: Plain-text email body.
    """
    import os
    import smtplib
    from email.mime.text import MIMEText

    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    from_addr = os.getenv("SMTP_FROM", smtp_user or "noreply@swarm.local")

    if not smtp_host:
        logger.warning("SMTP_HOST not set — skipping email to %s: %s", email, subject)
        return {"ok": False, "reason": "smtp_not_configured"}

    try:
        msg = MIMEText(body, "plain")
        msg["Subject"] = subject
        msg["From"] = from_addr
        msg["To"] = email

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.ehlo()
            server.starttls()
            if smtp_user and smtp_pass:
                server.login(smtp_user, smtp_pass)
            server.sendmail(from_addr, [email], msg.as_string())

        logger.info("Email sent to %s: %s", email, subject)
        return {"ok": True}
    except Exception as exc:
        logger.exception("send_email_notification failed: %s", exc)
        raise self.retry(exc=exc)


@celery_app.task(
    name="backend.tasks.notification_tasks.broadcast_event",
    bind=True,
    max_retries=2,
    default_retry_delay=15,
)
def broadcast_event(self, event_type: str, data: dict):
    """
    Fanout a system event notification to all admin users.

    Args:
        event_type: Short event label, e.g. 'deployment.completed'.
        data: Additional data dict (stringified into the message body).
    """
    from backend.db.session import SessionLocal
    from backend.services.notification_service import NotificationService

    db = SessionLocal()
    try:
        svc = NotificationService(db)
        svc.broadcast_system_event(
            event_type=event_type,
            message=str(data),
        )
        logger.info("Broadcast event '%s' to all admins", event_type)
        return {"ok": True}
    except Exception as exc:
        logger.exception("broadcast_event failed for '%s'", event_type)
        raise self.retry(exc=exc)
    finally:
        db.close()
