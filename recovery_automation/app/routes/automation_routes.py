"""Automated incident response routes."""

from fastapi import APIRouter, HTTPException, status

from app.models.schemas import ThreatDetectedRequest
from app.services.automation_service import AutomationService
from app.utils.logger import get_logger

logger = get_logger("automation_routes")

router = APIRouter(prefix="/automation", tags=["Automation"])

_automation = AutomationService()


@router.post("/threat-detected", response_model=dict)
def threat_detected(payload: ThreatDetectedRequest) -> dict:
    """
    Threat-triggered recovery workflow.

    Orchestrates: log → alert → backup → isolation → notify → dashboard update.
    """
    try:
        return _automation.handle_threat_detected(
            device_id=payload.device_id,
            threat_type=payload.threat_type,
            severity=payload.severity,
            enable_limp_mode=payload.enable_limp_mode,
        )
    except Exception as exc:
        logger.exception("Automation workflow failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
