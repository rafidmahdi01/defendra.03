"""Connect the client server to the Defendra backend on startup."""

from __future__ import annotations

import ctypes
import logging
import os
import sys
import time
from typing import TYPE_CHECKING

import requests

from config.settings import get_settings

if TYPE_CHECKING:
    from core.api_client import DefendraClient

logger = logging.getLogger("client.bootstrap")


def is_running_as_admin() -> bool:
    """Check if the process has administrator/root privileges."""
    try:
        if os.name == 'nt':  # Windows
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        else:  # Linux/Unix
            return os.geteuid() == 0
    except Exception:
        return False


def check_admin_privileges() -> None:
    """Verify admin privileges and exit if not running with elevated permissions."""
    if not is_running_as_admin():
        logger.error("Client agent must run with administrator/root privileges for isolation features")
        print("\n" + "="*70)
        print("ERROR: This agent requires elevated privileges")
        print("="*70)
        if os.name == 'nt':
            print("Windows: Right-click and select 'Run as Administrator'")
        else:
            print("Linux/macOS: Run with sudo (e.g., sudo python main.py)")
        print("="*70 + "\n")
        sys.exit(1)


def wait_for_backend(server_url: str | None = None, timeout: int = 90) -> bool:
    """Poll GET /health until the backend responds or timeout."""
    settings = get_settings()
    base = (server_url or settings.server_url).rstrip("/")
    health_url = f"{base}/health"
    deadline = time.time() + timeout

    while time.time() < deadline:
        try:
            resp = requests.get(health_url, timeout=4)
            if resp.status_code == 200:
                return True
        except requests.RequestException:
            pass
        time.sleep(2)

    return False


def bootstrap_admin(server_url: str | None = None) -> bool:
    """
    Ensure the default admin account exists (idempotent).

    Uses the same credentials as client/.env so login works on first run.
    """
    settings = get_settings()
    base = (server_url or settings.server_url).rstrip("/")
    email = settings.api_email or "admin@defendra.com"
    password = settings.api_password or "Admin@1234"

    try:
        resp = requests.post(
            f"{base}/api/auth/bootstrap-admin",
            json={
                "email": email,
                "full_name": "Defendra Admin",
                "password": password,
                "role": "admin",
            },
            timeout=10,
        )
        if resp.status_code in (200, 201):
            logger.info("Admin account ready: %s", email)
            return True
        if resp.status_code in (403, 409):
            logger.debug("Admin account already configured")
            return True
        logger.warning("bootstrap-admin HTTP %s: %s", resp.status_code, resp.text[:200])
    except requests.RequestException as exc:
        logger.warning("bootstrap-admin failed: %s", exc)
    return False


def connect_to_backend(client: DefendraClient, *, wait_timeout: int = 90) -> bool:
    """
    Full connection handshake:
      1. Wait for backend /health
      2. Bootstrap admin (first run)
      3. Login + register/link device
      4. Sync offline queue + send heartbeat
    """
    settings = client.settings
    logger.info("Connecting to Defendra backend at %s ...", settings.server_url)

    if not wait_for_backend(settings.server_url, timeout=wait_timeout):
        logger.error(
            "Backend not reachable at %s — start the Defendra API first (port 8000)",
            settings.server_url,
        )
        return False

    logger.info("Backend online")

    bootstrap_admin(settings.server_url)

    device_id = client.ensure_device()
    if not device_id:
        logger.error(
            "Could not register device — verify API_EMAIL/API_PASSWORD in client/.env "
            "(default: admin@defendra.com / Admin@1234)"
        )
        return False

    logger.info("Linked to backend as device_id=%s", device_id)

    synced = client.sync_offline_queue()
    if synced:
        logger.info("Synced %s queued log/alert item(s)", synced)

    if client.send_heartbeat():
        logger.info("Heartbeat OK — device will appear on the dashboard")
    else:
        logger.warning("Heartbeat failed after registration")

    ok = client.send_log(
        "Defendra client server connected to backend",
        category="agent",
        severity="info",
        source="bootstrap",
    )
    if ok:
        logger.info("Backend connection verified — logs and alerts will sync to the dashboard")
    else:
        logger.warning("Connected but log test did not reach server (may be queued)")

    return True
