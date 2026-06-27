"""
In-process event bus — publish/subscribe for domain events.

Subscribers are plain callables or coroutines registered at import time.
Events fire synchronously in the same thread; async subscribers are
scheduled onto the running event loop with asyncio.ensure_future.
"""
import asyncio
import logging
from typing import Callable

logger = logging.getLogger("EventBus")


class EventBus:
    """
    Lightweight publish/subscribe dispatcher.

    Supported events
    ----------------
    ticket.created      — payload: {"ticket": <Ticket>}
    ticket.resolved     — payload: {"ticket": <Ticket>}
    ticket.escalated    — payload: {"ticket": <Ticket>}
    task.completed      — payload: {"task_id": str, "result": any}
    task.failed         — payload: {"task_id": str, "error": str}
    workflow.completed  — payload: {"workflow_id": str}
    workflow.failed     — payload: {"workflow_id": str, "error": str}
    """

    def __init__(self):
        self._subscribers: dict[str, list[Callable]] = {}

    def subscribe(self, event: str, handler: Callable) -> None:
        """
        Register a handler for an event.

        Args:
            event: Event name, e.g. 'ticket.resolved'.
            handler: Sync or async callable that accepts (payload: dict).
        """
        self._subscribers.setdefault(event, []).append(handler)
        logger.debug("Subscribed %s to '%s'", handler.__name__, event)

    def publish(self, event: str, payload: dict) -> None:
        """
        Dispatch payload to all registered handlers for event.

        Args:
            event: Event name.
            payload: Data dict passed to every handler.
        """
        handlers = self._subscribers.get(event, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.ensure_future(handler(payload))
                    else:
                        loop.run_until_complete(handler(payload))
                else:
                    handler(payload)
            except Exception:
                logger.exception("Event handler %s raised on event '%s'", handler.__name__, event)


# Singleton
event_bus = EventBus()


# ─────────────────────────────────────────────────────────────────────────────
# Built-in event handlers
# ─────────────────────────────────────────────────────────────────────────────


def _on_ticket_resolved(payload: dict) -> None:
    """Send resolution notification to the reporter."""
    ticket = payload.get("ticket")
    if not ticket:
        return
    try:
        from backend.db.session import SessionLocal
        from backend.services.notification_service import NotificationService
        from backend.db.ticket_history import record_change

        db = SessionLocal()
        try:
            ns = NotificationService(db)
            ns.notify_ticket_resolved(ticket)
            record_change(db, ticket.id, "resolved_event_fired")
        finally:
            db.close()
    except Exception:
        logger.exception("_on_ticket_resolved handler failed")


def _on_task_failed(payload: dict) -> None:
    """Create an incident ticket and notify admins on task failure."""
    task_id = payload.get("task_id", "unknown")
    error = payload.get("error", "")
    try:
        from backend.db.session import SessionLocal
        from backend.services.notification_service import NotificationService
        from backend.services.ticket_service import TicketService

        db = SessionLocal()
        try:
            ts = TicketService(db)
            ts.create_ticket(
                title=f"Incident: task {task_id} failed",
                instruction=error,
                priority="high",
                tags="incident,auto-created",
            )
            ns = NotificationService(db)
            ns.notify_task_failed(task_id=task_id, error=error)
        finally:
            db.close()
    except Exception:
        logger.exception("_on_task_failed handler failed")


def _on_workflow_completed(payload: dict) -> None:
    """Advance any dependent workflows when one completes."""
    workflow_id = payload.get("workflow_id")
    if not workflow_id:
        return
    try:
        from backend.db.session import SessionLocal
        from backend.services.notification_service import NotificationService

        db = SessionLocal()
        try:
            ns = NotificationService(db)
            ns.broadcast_system_event(
                "workflow.completed",
                f"Workflow {workflow_id} completed successfully.",
            )
        finally:
            db.close()
    except Exception:
        logger.exception("_on_workflow_completed handler failed")


def _on_workflow_failed(payload: dict) -> None:
    """Notify admins on workflow failure."""
    workflow_id = payload.get("workflow_id", "unknown")
    error = payload.get("error", "")
    try:
        from backend.db.session import SessionLocal
        from backend.services.notification_service import NotificationService

        db = SessionLocal()
        try:
            ns = NotificationService(db)
            ns.broadcast_system_event(
                "workflow.failed",
                f"Workflow {workflow_id} failed: {error}",
            )
        finally:
            db.close()
    except Exception:
        logger.exception("_on_workflow_failed handler failed")


# Wire up built-in handlers
event_bus.subscribe("ticket.resolved", _on_ticket_resolved)
event_bus.subscribe("task.failed", _on_task_failed)
event_bus.subscribe("workflow.completed", _on_workflow_completed)
event_bus.subscribe("workflow.failed", _on_workflow_failed)
