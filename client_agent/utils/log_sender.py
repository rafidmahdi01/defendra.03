import os
from typing import Any

import requests

from utils.config import load_all_configs

load_all_configs()

MARIA_API_URL = os.getenv("MARIA_API_URL", os.getenv("BACKEND_URL", "http://127.0.0.1:8000"))


def _build_headers() -> dict:
    from utils.device_manager import _get_token
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
    from utils.device_manager import get_device_id, register_or_get_device

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
        return resp.status_code in (200, 201)
    except requests.RequestException:
        return False
