"""
Notifications API — list, mark-read, and delete user notifications.
"""
import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.db.session import get_db
from backend.db.models import Notification
from backend.auth.middleware import get_current_active_user

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])


def _serialize(n: Notification) -> dict:
    return {
        "id": n.id,
        "user_id": n.user_id,
        "type": n.type,
        "title": n.title,
        "message": n.message,
        "is_read": n.is_read,
        "metadata": json.loads(n.metadata_json) if n.metadata_json else None,
        "created_at": n.created_at.isoformat() if n.created_at else None,
    }


@router.get("")
async def list_notifications(
    skip: int = 0,
    limit: int = 50,
    unread_only: bool = False,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    List notifications for the authenticated user (paginated).

    Query params:
        skip: Offset for pagination.
        limit: Max results (1-200).
        unread_only: If true, return only unread notifications.
    """
    limit = min(max(limit, 1), 200)
    q = db.query(Notification).filter(Notification.user_id == current_user["id"])
    if unread_only:
        q = q.filter(Notification.is_read == False)
    total = q.count()
    items = q.order_by(Notification.created_at.desc()).offset(skip).limit(limit).all()
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": [_serialize(n) for n in items],
    }


@router.post("/read/{notification_id}", status_code=status.HTTP_200_OK)
async def mark_read(
    notification_id: str,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Mark a single notification as read."""
    notif = (
        db.query(Notification)
        .filter(
            Notification.id == notification_id,
            Notification.user_id == current_user["id"],
        )
        .first()
    )
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    notif.is_read = True
    db.commit()
    return {"ok": True}


@router.post("/read-all", status_code=status.HTTP_200_OK)
async def mark_all_read(
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Mark every notification for the current user as read."""
    db.query(Notification).filter(
        Notification.user_id == current_user["id"],
        Notification.is_read == False,
    ).update({"is_read": True})
    db.commit()
    return {"ok": True}


@router.delete("/{notification_id}", status_code=status.HTTP_200_OK)
async def delete_notification(
    notification_id: str,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Delete a notification belonging to the current user."""
    notif = (
        db.query(Notification)
        .filter(
            Notification.id == notification_id,
            Notification.user_id == current_user["id"],
        )
        .first()
    )
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    db.delete(notif)
    db.commit()
    return {"ok": True}
