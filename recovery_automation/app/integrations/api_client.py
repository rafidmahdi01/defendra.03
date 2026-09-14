"""
Reusable HTTP client for the existing Defendra backend APIs.

Maps spec endpoints to actual Defendra routes:
  GET  /api/devices          -> list devices (device lookup by id)
  GET  /api/logs             -> fetch logs
  POST /api/alerts           -> send_alert / report_incident
  POST /api/threats/report   -> fallback to POST /api/alerts
  POST /api/dashboard/update -> fallback to POST /api/logs (audit trail)
"""

import time
from typing import Any

import requests

from app.utils.config import get_settings
from app.utils.logger import get_logger

logger = get_logger("api_client")


class DefendraAPIError(Exception):
    """Raised when Defendra API returns an error or is unreachable."""


class DefendraAPIClient:
    """Authenticated client for Defendra core backend."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.base_url = self.settings.defendra_api_url.rstrip("/")
        self._token: str | None = self.settings.defendra_api_token or None
        self._token_obtained_at: float = 0.0
        self.timeout = 15

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        token = self._get_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def _get_token(self) -> str:
        now = time.time()
        if self._token and (now - self._token_obtained_at) < 3000:
            return self._token

        email = self.settings.defendra_api_email
        password = self.settings.defendra_api_password
        if email and password:
            try:
                resp = requests.post(
                    f"{self.base_url}/api/auth/login",
                    json={"email": email, "password": password},
                    timeout=self.timeout,
                )
                if resp.status_code == 200:
                    self._token = resp.json().get("access_token", "")
                    self._token_obtained_at = now
                    logger.info("Obtained JWT from Defendra auth API")
                    return self._token or ""
            except requests.RequestException as exc:
                logger.warning("Defendra login failed: %s", exc)

        return self._token or ""

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        require_auth: bool = True,
    ) -> Any:
        url = f"{self.base_url}{path}"
        logger.debug("API %s %s", method, url)
        try:
            resp = requests.request(
                method,
                url,
                json=json,
                params=params,
                headers=self._headers() if require_auth else {"Content-Type": "application/json"},
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            logger.error("Defendra API unreachable: %s %s — %s", method, path, exc)
            raise DefendraAPIError(str(exc)) from exc

        if resp.status_code >= 400:
            logger.error(
                "Defendra API error %s %s -> HTTP %s: %s",
                method,
                path,
                resp.status_code,
                resp.text[:500],
            )
            raise DefendraAPIError(f"HTTP {resp.status_code}: {resp.text[:200]}")

        if resp.status_code == 204 or not resp.content:
            return {}
        return resp.json()

    # ── Spec-aligned helpers ─────────────────────────────────────────────────

    def get_devices(self) -> list[dict[str, Any]]:
        """GET /api/devices"""
        result = self._request("GET", "/api/devices")
        return result if isinstance(result, list) else []

    def fetch_device(self, device_id: str) -> dict[str, Any] | None:
        """
        GET /api/device/{id} — implemented via device list filter
        (Defendra exposes GET /api/devices, not per-id route).
        """
        for device in self.get_devices():
            if str(device.get("id")) == device_id or device.get("hostname") == device_id:
                return device
        logger.warning("Device not found: %s", device_id)
        return None

    def get_logs(self, limit: int = 50) -> list[dict[str, Any]]:
        """GET /api/logs"""
        result = self._request("GET", "/api/logs", params={"limit": limit})
        return result if isinstance(result, list) else []

    def send_alert(
        self,
        *,
        title: str,
        description: str,
        severity: str = "high",
        device_id: str | None = None,
        rule_name: str = "recovery_automation",
    ) -> dict[str, Any]:
        """POST /api/alerts"""
        payload: dict[str, Any] = {
            "title": title,
            "description": description,
            "severity": severity,
            "status": "open",
            "rule_name": rule_name,
        }
        if device_id:
            payload["device_id"] = device_id
        result = self._request("POST", "/api/alerts", json=payload)
        logger.info("Alert sent to Defendra: %s", title)
        return result if isinstance(result, dict) else {}

    def report_incident(
        self,
        *,
        device_id: str,
        threat_type: str,
        severity: str,
        details: str,
    ) -> dict[str, Any]:
        """
        POST /api/threats/report — mapped to alerts + recovery log entry.
        """
        alert = self.send_alert(
            title=f"Incident: {threat_type}",
            description=details,
            severity=severity,
            device_id=device_id,
            rule_name=f"threat_{threat_type}",
        )
        self._post_recovery_log(
            device_id=device_id,
            message=f"Incident reported: {threat_type} — {details}",
            severity=severity,
        )
        return {"alert": alert, "threat_type": threat_type}

    def update_dashboard(
        self,
        *,
        event: str,
        device_id: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        POST /api/dashboard/update — mapped to POST /api/logs for audit visibility.
        Dashboard WebSocket updates occur when alerts are created on the main backend.
        """
        message = f"Recovery dashboard event: {event}"
        if payload:
            message = f"{message} | {payload}"
        return self._post_recovery_log(
            device_id=device_id or "recovery-module",
            message=message,
            severity="info",
            raw_payload={"event": event, **(payload or {})},
        )

    def _post_recovery_log(
        self,
        *,
        device_id: str,
        message: str,
        severity: str = "info",
        raw_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """POST /api/logs — no auth required on Defendra ingestion endpoint."""
        body = {
            "device_id": device_id,
            "category": "recovery",
            "severity": severity,
            "source": "recovery_automation",
            "message": message,
            "raw_payload": raw_payload or {},
        }
        try:
            return self._request(
                "POST",
                "/api/logs",
                json=body,
                require_auth=False,
            )
        except DefendraAPIError as exc:
            logger.warning("Could not post recovery log (non-fatal): %s", exc)
            return {}


# Module-level singleton for services
_client: DefendraAPIClient | None = None


def get_api_client() -> DefendraAPIClient:
    global _client
    if _client is None:
        _client = DefendraAPIClient()
    return _client
