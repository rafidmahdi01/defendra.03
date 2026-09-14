"""Notification routes."""

from fastapi import APIRouter, status

from app.models.schemas import NotificationRequest
from app.services.notification_service import NotificationService
from app.utils.logger import get_logger

logger = get_logger("notification_routes")

router = APIRouter(prefix="/notify", tags=["Notifications"])

_notifications = NotificationService()


@router.post("/send", response_model=dict, status_code=status.HTTP_200_OK)
def send_notification(payload: NotificationRequest) -> dict:
    """Send notification via console, email, and/or Telegram."""
    return _notifications.send(
        subject=payload.subject,
        message=payload.message,
        channels=payload.channels,
        metadata=payload.metadata,
    )
