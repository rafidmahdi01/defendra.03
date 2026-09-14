"""
Limp mode — minimal simulated operation.

Disables non-essential simulated services while keeping recovery services active.
"""

from datetime import datetime, timezone
from typing import Any

from app.utils.logger import get_logger

logger = get_logger("limp_mode_service")

_limp_state: dict[str, Any] = {
    "active": False,
    "disabled_services": [],
    "active_services": ["backup", "restore", "notification", "api_client"],
}


class LimpModeService:
    """Manage degraded-operation mode for incident recovery."""

    # Services that would be disabled in full production integration
    _NON_ESSENTIAL = [
        "analytics_collector",
        "email_scanner_worker",
        "usb_scanner_worker",
        "threat_ml_inference",
        "dashboard_animations",
    ]

    def enable(self, reason: str = "incident_response") -> dict[str, Any]:
        """Enable limp mode — simulation only."""
        _limp_state["active"] = True
        _limp_state["enabled_at"] = datetime.now(timezone.utc).isoformat()
        _limp_state["reason"] = reason
        _limp_state["disabled_services"] = list(self._NON_ESSENTIAL)
        logger.warning(
            "[LIMP MODE] Enabled — disabled simulated services: %s",
            _limp_state["disabled_services"],
        )
        return self.status()

    def disable(self) -> dict[str, Any]:
        """Disable limp mode and restore normal simulated state."""
        _limp_state["active"] = False
        _limp_state["disabled_at"] = datetime.now(timezone.utc).isoformat()
        _limp_state["disabled_services"] = []
        logger.info("[LIMP MODE] Disabled — all simulated services restored")
        return self.status()

    def status(self) -> dict[str, Any]:
        return {
            "active": _limp_state["active"],
            "reason": _limp_state.get("reason"),
            "enabled_at": _limp_state.get("enabled_at"),
            "disabled_services": _limp_state.get("disabled_services", []),
            "active_services": _limp_state.get("active_services", []),
            "simulation": True,
        }

    def is_service_allowed(self, service_name: str) -> bool:
        """Check if a service should run while in limp mode."""
        if not _limp_state["active"]:
            return True
        if service_name in _limp_state.get("active_services", []):
            return True
        return service_name not in _limp_state.get("disabled_services", [])
