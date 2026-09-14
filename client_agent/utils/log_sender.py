"""
Send structured DeviceLogs to the Defendra backend (POST /api/logs).

Usage:
    from utils.log_sender import send_log

    send_log(category="usb_scan", severity="info", message="USB D:\\ scanned clean.", source="usb_scanner")
    send_log(category="email_scan", severity="warning", message="Phishing email quarantined.", source="email_scanner")
    send_log(category="behavior", severity="critical", message="Ransomware pattern detected.", source="behavior_monitor")

Logs are fire-and-forget; failures are printed but do not raise exceptions.
"""

import os
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()

MARIA_API_URL = os.getenv("MARIA_API_URL", "http://127.0.0.1:8000")


def _build_headers() -> dict:
    from utils.device_manager import _get_token  # lazy import to avoid circular deps
    headers = {"Content-Type": "application/json"}
    token = _get_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def send_log(
    category: str,
    severity: str,
    message: str,
    source: str | None = None,
    raw_payload: dict[str, Any] | None = None,
) -> bool:
    """
    POST a structured log entry to /api/logs.

    Parameters
    ----------
    category    : e.g. "usb_scan", "email_scan", "behavior"
    severity    : "info" | "warning" | "error" | "critical"
    message     : human-readable log line
    source      : module name producing the log (optional)
    raw_payload : arbitrary dict attached as JSON metadata (optional)

    Returns True on HTTP 200/201, False otherwise.
    """
    from utils.device_manager import get_device_id, register_or_get_device  # lazy import

    device_id = get_device_id()
    if device_id is None:
        device_id = register_or_get_device()
    if device_id is None:
        print(f"[log_sender] Skipping log (no device_id): {message[:80]}")
        return False

    payload: dict[str, Any] = {
        "device_id": device_id,
        "category": category,
        "severity": severity,
        "message": message,
    }
    if source:
        payload["source"] = source
    if raw_payload:
        payload["raw_payload"] = raw_payload

    try:
        resp = requests.post(
            f"{MARIA_API_URL}/api/logs",
            json=payload,
            headers=_build_headers(),
            timeout=10,
        )
        if resp.status_code in (200, 201):
            return True
        print(f"[log_sender] HTTP {resp.status_code} for log: {message[:80]}")
        return False
    except requests.RequestException as e:
        print(f"[log_sender] Failed to send log (backend unreachable): {e}")
        return False
