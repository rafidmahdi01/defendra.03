"""Process and resource behavior monitoring."""

from __future__ import annotations

import logging
import threading
import time
from typing import TYPE_CHECKING

import psutil

from config.settings import get_settings

if TYPE_CHECKING:
    from core.api_client import DefendraClient
    from modules.alert_system import AlertSystem

logger = logging.getLogger("client.behavior")

BUILTIN_WHITELIST = {
    "system idle process",
    "system",
    "svchost.exe",
    "explorer.exe",
    "python.exe",
    "pythonw.exe",
    "cmd.exe",
    "powershell.exe",
    "pwsh.exe",
    "code.exe",
    "cursor.exe",
    "chrome.exe",
    "msedge.exe",
    "firefox.exe",
    "node.exe",
    "winlogon.exe",
    "lsass.exe",
    "services.exe",
    "csrss.exe",
    "smss.exe",
}


class BehaviorMonitor:
    """Detects high CPU usage and unknown processes."""

    def __init__(self, client: DefendraClient, alerts: AlertSystem) -> None:
        self.client = client
        self.alerts = alerts
        self.settings = get_settings()
        self._stop = threading.Event()
        self._alerted_processes: set[int] = set()
        self._last_cpu_alert = 0.0

    def run(self) -> None:
        logger.info("Behavior monitor started")
        while not self._stop.is_set():
            self._check_cpu()
            self._check_processes()
            self._stop.wait(self.settings.behavior_interval)

    def _check_cpu(self) -> None:
        cpu = psutil.cpu_percent(interval=1.0)
        if cpu < self.settings.cpu_alert_threshold:
            return

        now = time.time()
        if now - self._last_cpu_alert < 120:
            return

        self._last_cpu_alert = now
        msg = f"High CPU usage detected: {cpu:.1f}%"
        self.client.send_log(msg, category="behavior", severity="warning", source="behavior_monitor")
        self.alerts.notify(
            "High CPU Usage",
            msg,
            severity="high",
            rule_name="behavior_monitor",
            popup=False,
        )

    def _check_processes(self) -> None:
        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "exe"]):
            try:
                info = proc.info
                name = (info.get("name") or "").lower()
                pid = info["pid"]
                if not name or name in BUILTIN_WHITELIST:
                    continue
                if pid in self._alerted_processes:
                    continue

                cpu = info.get("cpu_percent") or 0.0
                exe = info.get("exe") or ""
                suspicious = cpu > 40 and not exe

                if suspicious or (name.endswith(".scr") or "miner" in name):
                    self._alerted_processes.add(pid)
                    detail = f"Unknown/suspicious process: {name} (PID {pid}, CPU {cpu:.1f}%)"
                    self.client.send_log(
                        detail,
                        category="behavior",
                        severity="high",
                        source="behavior_monitor",
                        raw_payload={"pid": pid, "name": name, "exe": exe},
                    )
                    self.alerts.notify(
                        "Suspicious Process",
                        detail,
                        severity="high",
                        rule_name="behavior_monitor",
                    )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

    def stop(self) -> None:
        self._stop.set()
