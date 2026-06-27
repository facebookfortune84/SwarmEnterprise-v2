"""
Celery application — full configuration for SwarmEnterprise v2.

Queues
------
default          General-purpose tasks.
high_priority    Time-sensitive work (notifications, escalations).
low_priority     Background / bulk operations.
tickets          All ticket processing tasks.
notifications    Notification delivery tasks.
dlq              Dead-letter queue — tasks that exhausted retries.

Beat schedule
-------------
check_sla_breaches     Every 30 minutes — SLA watchdog.
escalate_overdue       Every hour — escalation sweep.
"""
import os
from celery import Celery
from celery.schedules import crontab
from kombu import Exchange, Queue

_TEST_MODE = os.getenv("TEST_MODE", "").lower() in ("true", "1", "yes")
_CELERY_BROKER = os.getenv("CELERY_BROKER_URL", os.getenv("REDIS_URL", "redis://localhost:6379/0"))
_CELERY_BACKEND = os.getenv(
    "CELERY_RESULT_BACKEND", os.getenv("REDIS_URL", "redis://localhost:6379/0")
)

# In test mode use in-memory transport so no Redis connection is attempted
if _TEST_MODE:
    _CELERY_BROKER = "memory://"
    _CELERY_BACKEND = "cache+memory://"

# ─────────────────────────────────────────────────────────────────────────────
# Application
# ─────────────────────────────────────────────────────────────────────────────
celery_app = Celery(
    "swarm",
    broker=_CELERY_BROKER,
    backend=_CELERY_BACKEND,
    include=[
        "backend.tasks.ticket_tasks",
        "backend.tasks.notification_tasks",
        "backend.tasks.workflow_tasks",
    ],
)

# ─────────────────────────────────────────────────────────────────────────────
# Queue / exchange definitions
# ─────────────────────────────────────────────────────────────────────────────
default_exchange = Exchange("default", type="direct")
priority_exchange = Exchange("priority", type="direct")

celery_app.conf.task_queues = (
    Queue("default", default_exchange, routing_key="default"),
    Queue("high_priority", priority_exchange, routing_key="high"),
    Queue("low_priority", priority_exchange, routing_key="low"),
    Queue("tickets", default_exchange, routing_key="tickets"),
    Queue("notifications", default_exchange, routing_key="notifications"),
    Queue("dlq", default_exchange, routing_key="dlq"),
)

celery_app.conf.task_default_queue = "default"
celery_app.conf.task_default_exchange = "default"
celery_app.conf.task_default_routing_key = "default"

# ─────────────────────────────────────────────────────────────────────────────
# Task routing
# ─────────────────────────────────────────────────────────────────────────────
celery_app.conf.task_routes = {
    # Ticket tasks
    "backend.tasks.ticket_tasks.process_ticket": {"queue": "tickets"},
    "backend.tasks.ticket_tasks.check_sla_breaches": {"queue": "high_priority"},
    "backend.tasks.ticket_tasks.escalate_overdue_tickets": {"queue": "high_priority"},
    # Notification tasks
    "backend.tasks.notification_tasks.send_notification": {"queue": "notifications"},
    "backend.tasks.notification_tasks.send_email_notification": {"queue": "notifications"},
    "backend.tasks.notification_tasks.broadcast_event": {"queue": "notifications"},
    # Workflow tasks
    "backend.tasks.workflow_tasks.execute_workflow_step": {"queue": "default"},
    "backend.tasks.workflow_tasks.handle_step_failure": {"queue": "default"},
    "backend.tasks.workflow_tasks.advance_workflow": {"queue": "default"},
    # Legacy
    "swarm.create_bundle": {"queue": "default"},
}

# ─────────────────────────────────────────────────────────────────────────────
# Serialisation & timeouts
# ─────────────────────────────────────────────────────────────────────────────
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,  # acknowledge only after completion
    task_reject_on_worker_lost=True,  # re-queue if worker crashes
    worker_prefetch_multiplier=1,  # one task per worker at a time
    result_expires=3600,  # result TTL: 1 hour
    task_soft_time_limit=300,  # 5-minute soft limit
    task_time_limit=600,  # 10-minute hard limit
)

# ─────────────────────────────────────────────────────────────────────────────
# Beat periodic schedule
# ─────────────────────────────────────────────────────────────────────────────
celery_app.conf.beat_schedule = {
    "check-sla-breaches": {
        "task": "backend.tasks.ticket_tasks.check_sla_breaches",
        "schedule": 1800.0,  # every 30 minutes
        "options": {"queue": "high_priority"},
    },
    "escalate-overdue-tickets": {
        "task": "backend.tasks.ticket_tasks.escalate_overdue_tickets",
        "schedule": crontab(minute=0),  # top of every hour
        "options": {"queue": "high_priority"},
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# Dead-letter / error handling
# ─────────────────────────────────────────────────────────────────────────────
@celery_app.task(bind=True, name="swarm.dead_letter")
def dead_letter_handler(self, task_name: str, args, kwargs, exc_info: str):
    """Receives tasks that have exhausted all retries."""
    import logging

    logging.getLogger("Celery.DLQ").error(
        "Dead-letter: task=%s args=%s kwargs=%s error=%s",
        task_name,
        args,
        kwargs,
        exc_info,
    )
    # Fire event so the event bus can create an incident ticket
    try:
        from backend.services.event_bus import event_bus

        event_bus.publish("task.failed", {"task_id": task_name, "error": exc_info})
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# Legacy task — preserved from Phase 1
# ─────────────────────────────────────────────────────────────────────────────
@celery_app.task(name="swarm.create_bundle")
def create_bundle_task(project_id: str, customer_email: str = None):
    from backend.replicator import SwarmReplicator

    return SwarmReplicator.create_company_bundle(project_id, customer_email=customer_email)
