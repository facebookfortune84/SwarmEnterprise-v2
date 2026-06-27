"""
Notification service — creates DB notifications and dispatches real-time pushes.
"""
import json
import logging
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from backend.db.models import Notification, User

logger = logging.getLogger("NotificationService")


class NotificationService:
    """Create and manage user notifications."""

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------ #
    # Core creation                                                        #
    # ------------------------------------------------------------------ #

    def create_notification(
        self,
        user_id: str,
        type: str,
        title: str,
        message: str,
        metadata: Optional[dict] = None,
    ) -> Notification:
        """
        Persist a notification for a user and attempt a WebSocket push.

        Args:
            user_id: Recipient user ID.
            type: One of info/warning/error/success.
            title: Short notification title.
            message: Full notification body.
            metadata: Optional dict of extra data (stored as JSON).

        Returns:
            The persisted Notification row.
        """
        notif = Notification(
            user_id=user_id,
            type=type,
            title=title,
            message=message,
            metadata_json=json.dumps(metadata) if metadata else None,
            created_at=datetime.utcnow(),
        )
        self.db.add(notif)
        self.db.commit()
        self.db.refresh(notif)

        # Best-effort real-time push
        self._ws_push(user_id, notif)
        return notif

    # ------------------------------------------------------------------ #
    # Domain-specific helpers                                              #
    # ------------------------------------------------------------------ #

    def notify_ticket_created(self, ticket) -> None:
        """Notify the ticket assignee when a ticket is created."""
        if not ticket.assignee_id:
            return
        self.create_notification(
            user_id=ticket.assignee_id,
            type="info",
            title="New ticket assigned",
            message=f'Ticket {ticket.id} — "{ticket.title}" has been assigned to you.',
            metadata={"ticket_id": ticket.id},
        )

    def notify_ticket_resolved(self, ticket) -> None:
        """Notify the reporter when a ticket is resolved."""
        if not ticket.reporter_id:
            return
        self.create_notification(
            user_id=ticket.reporter_id,
            type="success",
            title="Ticket resolved",
            message=f'Ticket {ticket.id} — "{ticket.title}" has been resolved.',
            metadata={"ticket_id": ticket.id},
        )

    def notify_task_failed(self, task_id: str, error: str) -> None:
        """
        Notify all admins when a background task fails.

        Args:
            task_id: The Celery task ID that failed.
            error: Error message / traceback excerpt.
        """
        admin_ids = self._get_admin_user_ids()
        for uid in admin_ids:
            self.create_notification(
                user_id=uid,
                type="error",
                title="Background task failed",
                message=f"Task {task_id} failed: {error}",
                metadata={"task_id": task_id, "error": error},
            )

    def broadcast_system_event(self, event_type: str, message: str) -> None:
        """
        Send an info notification to every admin user.

        Args:
            event_type: Short label for the event, e.g. 'deployment.completed'.
            message: Human-readable description.
        """
        admin_ids = self._get_admin_user_ids()
        for uid in admin_ids:
            self.create_notification(
                user_id=uid,
                type="info",
                title=f"System event: {event_type}",
                message=message,
                metadata={"event_type": event_type},
            )

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _get_admin_user_ids(self) -> list[str]:
        admins = (
            self.db.query(User.id)
            .filter(User.role.in_(["admin", "superadmin"]), User.is_active == True)
            .all()
        )
        return [row.id for row in admins]

    def _ws_push(self, user_id: str, notif: Notification) -> None:
        """Fire-and-forget WebSocket push to the connected client (if any)."""
        try:
            from backend.api.ws import manager
            import asyncio

            payload = {
                "id": notif.id,
                "type": notif.type,
                "title": notif.title,
                "message": notif.message,
                "created_at": notif.created_at.isoformat(),
            }
            # schedule on the running event loop; safe to call from sync context
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(manager.send_to_user(user_id, payload))
        except Exception:
            # WS push is best-effort; never raise
            pass
