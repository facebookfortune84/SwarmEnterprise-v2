"""
GDPR compliance endpoints.

Provides data export (Article 20 — portability) and account deletion
(Article 17 — erasure) for authenticated users.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.auth.middleware import get_current_active_user
from backend.db.models import APIKey, UsageEvent, User
from backend.db.session import get_db

router = APIRouter(prefix="/api/user", tags=["GDPR"])
logger = logging.getLogger("SwarmOS.gdpr")


# ---------------------------------------------------------------------------
# GET /api/user/export
# ---------------------------------------------------------------------------


@router.get(
    "/export",
    summary="Export all personal data (GDPR Art. 20 — portability)",
    status_code=status.HTTP_200_OK,
)
def export_user_data(
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Return a complete JSON dump of all personal data held for the
    authenticated user.

    Includes:
    - User profile (password hash excluded)
    - All API keys linked to the account
    - All usage events linked to the account

    Returns:
        dict: Structured personal-data export.
    """
    user_id: str = current_user["id"]

    user: User | None = db.query(User).filter(User.id == user_id).first()
    if user is None:
        # Should be unreachable — get_current_active_user already verifies existence.
        from fastapi import HTTPException

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    api_keys: List[APIKey] = db.query(APIKey).filter(APIKey.user_id == user_id).all()
    usage_events: List[UsageEvent] = (
        db.query(UsageEvent).filter(UsageEvent.project_id == user_id).all()
    )

    def _key_to_dict(k: APIKey) -> Dict[str, Any]:
        return {
            "id": k.id,
            "name": k.name,
            "scope": k.scope,
            "is_active": k.is_active,
            "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
            "expires_at": k.expires_at.isoformat() if k.expires_at else None,
            "created_at": k.created_at.isoformat() if k.created_at else None,
        }

    def _event_to_dict(e: UsageEvent) -> Dict[str, Any]:
        return {
            "id": e.id,
            "event_type": e.event_type,
            "amount": e.amount,
            "metadata_json": e.metadata_json,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }

    return {
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "subscription_tier": user.subscription_tier,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None,
        },
        "api_keys": [_key_to_dict(k) for k in api_keys],
        "usage_events": [_event_to_dict(e) for e in usage_events],
    }


# ---------------------------------------------------------------------------
# DELETE /api/user/account
# ---------------------------------------------------------------------------


@router.delete(
    "/account",
    summary="Delete account and all personal data (GDPR Art. 17 — erasure)",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_user_account(
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> None:
    """
    Permanently delete the authenticated user's account and all cascade records:

    - All ``APIKey`` rows for this user
    - All ``UsageEvent`` rows linked to this user
    - The ``User`` row itself

    Returns HTTP 204 No Content on success.

    Note: Stripe payment records (``Project`` model) are retained for 7 years
    per US tax-record obligations and are not deleted by this endpoint.
    """
    user_id: str = current_user["id"]

    # Delete cascade records first to respect FK constraints.
    db.query(APIKey).filter(APIKey.user_id == user_id).delete(synchronize_session=False)
    db.query(UsageEvent).filter(UsageEvent.project_id == user_id).delete(synchronize_session=False)
    db.query(User).filter(User.id == user_id).delete(synchronize_session=False)

    db.commit()
    logger.info("GDPR erasure: user %s deleted", user_id)
