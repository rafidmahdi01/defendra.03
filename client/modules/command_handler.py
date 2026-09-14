"""Poll server for admin commands and execute locally."""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING

from config.settings import get_settings

if TYPE_CHECKING:
    from core.api_client import DefendraClient
    from modules.alert_system import AlertSystem
    from modules.backup_manager import BackupManager

logger = logging.getLogger("client.commands")


class CommandHandler:
    """
    Uses fetch_commands() to react to server status or local test commands.

    Supported: isolate, limp_mode, scan, backup
    """

    def __init__(
        self,
        client: DefendraClient,
        alerts: AlertSystem,
        backup: BackupManager,
    ) -> None:
        self.client = client
        self.alerts = alerts
        self.backup = backup
        self.settings = get_settings()
        self._stop = threading.Event()
        self._isolated = False
        self._handled: set[str] = set()

    @property
    def is_isolated(self) -> bool:
        return self._isolated

    def run(self) -> None:
        logger.info("Command handler started")
        while not self._stop.is_set():
            commands = self.client.fetch_commands()
            for cmd in commands:
                self._execute(cmd)
            self._stop.wait(self.settings.command_poll_interval)

    def _execute(self, cmd: dict) -> None:
        cmd_type = (cmd.get("type") or "").lower()
        key = f"{cmd_type}:{cmd.get('source', '')}"
        if key in self._handled and cmd.get("source") == "server_status":
            return

        if cmd_type == "isolate":
            self._isolated = True
            self._handled.add(key)
            self.alerts.notify(
                "Device Isolated",
                "Admin requested network isolation (simulated).",
                severity="critical",
                rule_name="command_handler",
            )
            self.client.send_log(
                "Device isolation command applied",
                category="command",
                severity="critical",
                source="command_handler",
            )

        elif cmd_type in ("limp_mode", "limpmode"):
            self._handled.add(key)
            self.alerts.notify(
                "Limp Mode",
                "Reduced monitoring mode enabled by admin.",
                severity="warning",
                rule_name="command_handler",
            )
            self.client.send_log(
                "Limp mode command received",
                category="command",
                severity="warning",
                source="command_handler",
            )

        elif cmd_type == "scan":
            self._handled.add(key)
            self.client.send_log(
                "On-demand scan requested",
                category="command",
                severity="info",
                source="command_handler",
            )
            self.alerts.notify(
                "Scan Started",
                "Full endpoint scan initiated (simulated).",
                severity="info",
                rule_name="command_handler",
                send_to_server=False,
            )

        elif cmd_type == "backup":
            self._handled.add(key)
            count = self.backup.run_backup(trigger="admin_command")
            self.alerts.notify(
                "Backup Complete",
                f"Admin-triggered backup finished ({count} files).",
                severity="info",
                rule_name="command_handler",
            )

    def stop(self) -> None:
        self._stop.set()
