import logging
from datetime import datetime, timezone

from fastapi import Request
from google.api_core import exceptions as google_exceptions
from google.cloud.firestore import Client

from models.models import UserDoc

logger = logging.getLogger(__name__)


def record_audit(
    db: Client,
    action: str,
    user: UserDoc | None = None,
    request: Request | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
) -> None:
    """
    Best-effort audit write. Failures must not block auth or primary flows —
    quotas on Firestore writes are common during spikes.
    """
    try:
        db.collection("audit_logs").document().set(
            {
                "user_id": user.id if user else None,
                "user_email": user.email if user else None,
                "user_full_name": user.full_name if user else None,
                "user_role": user.role if user else None,
                "action": action,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "ip_address": request.client.host if request and request.client else None,
                "user_agent": request.headers.get("user-agent") if request else None,
                "created_at": datetime.now(timezone.utc),
            }
        )
    except google_exceptions.GoogleAPICallError as exc:
        logger.warning("Audit log skipped (%s): %s", action, exc)
