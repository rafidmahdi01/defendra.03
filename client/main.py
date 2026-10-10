#!/usr/bin/env python3
"""
Defendra Client Server — endpoint security detection layer.

Runs modular monitors in background threads and reports to the Defendra backend.
"""

from __future__ import annotations

import logging
import sys
import threading
from pathlib import Path

# Ensure imports resolve when run as `python main.py` from client/
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from config.settings import get_settings
from core.api_client import DefendraClient
from core.network_monitor import NetworkMonitor
from core.offline_queue import OfflineQueue
from modules.alert_system import AlertSystem
from modules.backup_manager import BackupManager
from modules.behavior_monitor import BehaviorMonitor
from modules.command_handler import CommandHandler
from modules.device_monitor import DeviceMonitor
from modules.email_scanner import EmailScanner
from modules.isolation_handler import IsolationHandler
from modules.usb_scanner import USBScanner


def setup_logging() -> None:
    settings = get_settings()
    settings.logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = settings.logs_dir / "agent.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file, encoding="utf-8"),
        ],
    )


def _run_module(name: str, target) -> None:
    """Run a module loop; log uncaught errors instead of killing the thread."""
    logger = logging.getLogger("client.main")
    try:
        target()
    except Exception:
        logger.exception("Module %s crashed", name)


def main() -> None:
    setup_logging()
    logger = logging.getLogger("client.main")
    settings = get_settings()

    # Check for admin privileges before proceeding
    from core.bootstrap import check_admin_privileges
    check_admin_privileges()

    logger.info("=" * 60)
    logger.info("Defendra Client Server v%s", settings.agent_version)
    logger.info("Server: %s", settings.server_url)
    logger.info("=" * 60)

    queue = OfflineQueue()
    client = DefendraClient(queue=queue)

    from core.bootstrap import connect_to_backend

    if connect_to_backend(client):
        logger.info("Backend connection established")
    else:
        logger.warning(
            "Running in offline mode — data will sync when %s is available",
            settings.server_url,
        )

    alerts = AlertSystem(client)
    alerts.start()

    backup = BackupManager(client)
    isolation = IsolationHandler(client, alerts)
    command_handler = CommandHandler(client, alerts, backup, isolation)

    modules: list[tuple[str, threading.Thread]] = [
        ("device-monitor", threading.Thread(target=_run_module, args=("device-monitor", DeviceMonitor(client).run), daemon=True)),
        ("network-monitor", threading.Thread(target=_run_module, args=("network-monitor", NetworkMonitor(client).run), daemon=True)),
        ("usb-scanner", threading.Thread(target=_run_module, args=("usb-scanner", USBScanner(client, alerts).run), daemon=True)),
        ("email-scanner", threading.Thread(target=_run_module, args=("email-scanner", EmailScanner(client, alerts).run), daemon=True)),
        ("behavior-monitor", threading.Thread(target=_run_module, args=("behavior-monitor", BehaviorMonitor(client, alerts).run), daemon=True)),
        ("backup-manager", threading.Thread(target=_run_module, args=("backup-manager", backup.run), daemon=True)),
        ("command-handler", threading.Thread(target=_run_module, args=("command-handler", command_handler.run), daemon=True)),
    ]

    pending_logs, pending_alerts = queue.pending_counts()
    if pending_logs or pending_alerts:
        logger.info(
            "Offline queue pending: %s logs, %s alerts — will sync when online",
            pending_logs,
            pending_alerts,
        )

    for name, thread in modules:
        thread.name = name
        thread.start()
        logger.info("Started %s", name)

    client.send_log(
        "Defendra client server started",
        category="agent",
        severity="info",
        source="main",
    )

    try:
        while True:
            threading.Event().wait(3600)
    except KeyboardInterrupt:
        logger.info("Shutdown requested (Ctrl+C)")
        alerts.stop()


if __name__ == "__main__":
    main()
