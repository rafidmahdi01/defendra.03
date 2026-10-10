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
    from modules.isolation_handler import IsolationHandler

logger = logging.getLogger("client.commands")


class CommandHandler:
    """
    Uses fetch_commands() to react to server status or local test commands.

    Supported: isolate, recover, limp_mode, scan, backup
    """

    def __init__(
        self,
        client: DefendraClient,
        alerts: AlertSystem,
        backup: BackupManager,
        isolation: IsolationHandler,
    ) -> None:
        self.client = client
        self.alerts = alerts
        self.backup = backup
        self.isolation = isolation
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
            # Extract isolation parameters from command payload
            isolation_type = cmd.get("isolation_type", "network_only")
            grace_period = cmd.get("grace_period", 10)
            reason = cmd.get("reason", "Security incident")
            isolated_by = cmd.get("isolated_by", "admin")
            
            self._isolated = True
            self._handled.add(key)
            
            # Execute actual isolation via IsolationHandler
            self.isolation.execute_isolation(
                isolation_type=isolation_type,
                grace_period=grace_period,
                reason=reason,
                isolated_by=isolated_by,
            )

        elif cmd_type == "recover":
            self._handled.add(key)
            logger.critical("RECOVER command received — removing firewall quarantine")
            ok = self.isolation.execute_recovery()
            if ok:
                self._isolated = False
                self.alerts.notify(
                    "Device Recovered",
                    "Firewall quarantine has been removed by admin. Normal connectivity restored.",
                    severity="info",
                    rule_name="command_handler",
                )
            else:
                self.alerts.notify(
                    "Recovery Failed",
                    "Failed to remove firewall quarantine — manual intervention required.",
                    severity="critical",
                    rule_name="command_handler",
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
