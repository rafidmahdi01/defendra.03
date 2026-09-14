"""Resolve human-readable device locations from IP addresses."""

from __future__ import annotations

import ipaddress
import logging

import requests

logger = logging.getLogger(__name__)

_GEO_FIELDS = "status,message,city,regionName,country,query"


def _is_private_ip(ip: str | None) -> bool:
    if not ip:
        return True
    try:
        addr = ipaddress.ip_address(ip.strip())
        return bool(addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved)
    except ValueError:
        return True


def _format_geo(data: dict) -> str | None:
    if data.get("status") != "success":
        return None
    parts = [p for p in (data.get("city"), data.get("regionName"), data.get("country")) if p]
    return ", ".join(parts) if parts else None


def _lookup_ip(ip: str) -> str | None:
    try:
        resp = requests.get(
            f"http://ip-api.com/json/{ip}?fields={_GEO_FIELDS}",
            timeout=5,
        )
        if resp.status_code == 200:
            return _format_geo(resp.json())
    except requests.RequestException as exc:
        logger.debug("IP geolocation failed for %s: %s", ip, exc)
    return None


def _lookup_public_ip() -> tuple[str | None, str | None]:
    """Return (location label, public IP) for this machine's egress address."""
    try:
        resp = requests.get(
            f"http://ip-api.com/json/?fields={_GEO_FIELDS}",
            timeout=5,
        )
        if resp.status_code == 200:
            data = resp.json()
            label = _format_geo(data)
            return label, data.get("query")
    except requests.RequestException as exc:
        logger.debug("Public IP geolocation failed: %s", exc)
    return None, None


def resolve_device_location(
    *,
    ip_address: str | None = None,
    provided: str | None = None,
    request_ip: str | None = None,
) -> str:
    """
    Resolve the best location label we can for a device.

    Priority:
      1. Client-provided location string
      2. Geolocate a public device IP
      3. Geolocate the heartbeat/request source IP
      4. Public egress geolocation + LAN IP note
      5. Local network label from private IP
    """
    if provided and provided.strip():
        return provided.strip()

    for candidate in (ip_address, request_ip):
        if candidate and not _is_private_ip(candidate):
            label = _lookup_ip(candidate.strip())
            if label:
                return f"{label} ({candidate.strip()})"

    ip = (ip_address or "").strip()
    public_label, public_ip = _lookup_public_ip()

    if ip and _is_private_ip(ip) and ip not in ("127.0.0.1", "::1"):
        if public_label:
            suffix = public_ip or public_label
            return f"{public_label} · LAN {ip} ({suffix})"
        return f"Local network · {ip}"

    if public_label:
        if public_ip:
            return f"{public_label} ({public_ip})"
        return public_label

    if ip:
        return f"Local network · {ip}"

    return "Location unavailable"
