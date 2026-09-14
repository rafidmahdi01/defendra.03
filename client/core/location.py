"""Resolve a human-readable location string for this workstation."""

from __future__ import annotations

import logging
import time

import requests

logger = logging.getLogger("client.location")


def resolve_device_location(*, override: str = "", local_ip: str = "") -> str:
    """
    Best-effort location for dashboards.

    Priority:
      1. DEVICE_LOCATION env override
      2. Public IP geolocation (ip-api.com)
      3. OS timezone label
    """
    if override and override.strip():
        return override.strip()

    try:
        resp = requests.get(
            "http://ip-api.com/json/?fields=status,city,regionName,country,query",
            timeout=5,
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("status") == "success":
                parts = [
                    p
                    for p in (data.get("city"), data.get("regionName"), data.get("country"))
                    if p
                ]
                if parts:
                    label = ", ".join(parts)
                    ip_note = data.get("query") or local_ip
                    if ip_note and ip_note not in ("127.0.0.1", "::1"):
                        return f"{label} ({ip_note})"
                    return label
    except requests.RequestException as exc:
        logger.debug("geolocation lookup failed: %s", exc)

    tz = time.tzname[1] if time.daylight and len(time.tzname) > 1 else time.tzname[0]
    if tz:
        return f"{tz.replace('_', ' ')}"
    return "Unknown location"
