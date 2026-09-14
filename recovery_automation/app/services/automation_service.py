"""
Automated incident response orchestration.

Threat-triggered workflow integrates with existing Defendra APIs only.
"""

from typing import Any

from app.integrations.api_client import DefendraAPIError, get_api_client
from app.services.backup_service import BackupService
from app.services.isolation_service import IsolationService
from app.services.limp_mode_service import LimpModeService
from app.services.notification_service import NotificationService
from app.utils.logger import get_logger

logger = get_logger("automation_service")


class AutomationService:
    """
    Orchestrates the threat-detected pipeline:
    log → alert → backup → isolate → notify → dashboard update
    """

    def __init__(self) -> None:
        self.api = get_api_client()
        self.backup = BackupService()
        self.isolation = IsolationService()
        self.notifications = NotificationService()
        self.limp_mode = LimpModeService()

    def handle_threat_detected(
        self,
        *,
        device_id: str,
        threat_type: str,
        severity: str = "critical",
        enable_limp_mode: bool = False,
    ) -> dict[str, Any]:
        """
        Full automated incident response workflow.
        """
        logger.warning(
            "Threat detected — device=%s type=%s severity=%s",
            device_id,
            threat_type,
            severity,
        )

        workflow_steps: list[dict[str, Any]] = []
        errors: list[str] = []

        # 1. Log incident locally (always)
        workflow_steps.append(
            {
                "step": "log_incident",
                "status": "completed",
                "detail": f"{threat_type} on {device_id}",
            }
        )

        # 2. Verify device exists (best-effort)
        device = None
        try:
            device = self.api.fetch_device(device_id)
            workflow_steps.append(
                {"step": "fetch_device", "status": "completed", "found": device is not None}
            )
        except DefendraAPIError as exc:
            errors.append(f"fetch_device: {exc}")
            workflow_steps.append({"step": "fetch_device", "status": "failed", "error": str(exc)})

        # 3. Report to Defendra (alert + incident log)
        try:
            incident = self.api.report_incident(
                device_id=device_id,
                threat_type=threat_type,
                severity=severity,
                details=f"Automated response triggered for {threat_type}",
            )
            workflow_steps.append({"step": "report_incident", "status": "completed", "result": incident})
        except DefendraAPIError as exc:
            errors.append(f"report_incident: {exc}")
            workflow_steps.append({"step": "report_incident", "status": "failed", "error": str(exc)})

        # 4. Trigger backup
        try:
            backup_meta = self.backup.create_backup(
                label=f"threat_{threat_type}",
                device_id=device_id,
            )
            workflow_steps.append({"step": "backup", "status": "completed", "backup_id": backup_meta["backup_id"]})
        except Exception as exc:
            errors.append(f"backup: {exc}")
            workflow_steps.append({"step": "backup", "status": "failed", "error": str(exc)})

        # 5. Simulate isolation
        try:
            isolation_result = self.isolation.isolate_device(
                device_id,
                reason=f"{threat_type}:{severity}",
            )
            workflow_steps.append({"step": "isolation", "status": "completed", "result": isolation_result})
        except Exception as exc:
            errors.append(f"isolation: {exc}")
            workflow_steps.append({"step": "isolation", "status": "failed", "error": str(exc)})

        # 6. Notifications
        notify_result = self.notifications.send(
            subject=f"Threat: {threat_type} on {device_id}",
            message=(
                f"Severity: {severity}\n"
                f"Device: {device_id}\n"
                f"Automated recovery workflow executed.\n"
                f"Errors: {errors or 'none'}"
            ),
            channels=["console", "email", "telegram"],
        )
        workflow_steps.append({"step": "notification", "status": "completed", "result": notify_result})

        # 7. Dashboard / audit update
        try:
            dash = self.api.update_dashboard(
                event="threat.automated_response",
                device_id=device_id,
                payload={
                    "threat_type": threat_type,
                    "severity": severity,
                    "steps": len(workflow_steps),
                },
            )
            workflow_steps.append({"step": "dashboard_update", "status": "completed", "result": dash})
        except DefendraAPIError as exc:
            errors.append(f"dashboard_update: {exc}")
            workflow_steps.append({"step": "dashboard_update", "status": "failed", "error": str(exc)})

        # 8. Optional limp mode for critical threats
        if enable_limp_mode or severity.lower() == "critical":
            limp = self.limp_mode.enable(reason=f"{threat_type}:{device_id}")
            workflow_steps.append({"step": "limp_mode", "status": "completed", "result": limp})

        overall_status = "completed" if not errors else "completed_with_errors"
        response = {
            "status": overall_status,
            "device_id": device_id,
            "threat_type": threat_type,
            "severity": severity,
            "device": device,
            "workflow_steps": workflow_steps,
            "errors": errors,
        }
        logger.info("Threat workflow finished: %s", overall_status)
        return response
