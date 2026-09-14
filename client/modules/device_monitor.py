"""Device identity, heartbeat, and online/offline status reporting."""

from __future__ import annotations

import logging
import platform
import socket
import threading
import time
from typing import TYPE_CHECKING

from config.settings import get_settings

if TYPE_CHECKING:
    from core.api_client import DefendraClient

logger = logging.getLogger("client.device")


def collect_device_info(settings) -> dict[str, str]:
    """Gather hostname, IP, and OS for registration / status logs."""
    hostname = settings.device_name or socket.gethostname()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
    except OSError:
        ip = "127.0.0.1"

    return {
        "hostname": hostname,
        "ip_address": ip,
        "os_name": f"{platform.system()} {platform.release()} ({platform.machine()})",
        "agent_version": settings.agent_version,
    }


class DeviceMonitor:
    """Registers device and sends periodic heartbeats with CPU/RAM metrics."""

    def __init__(self, client: DefendraClient) -> None:
        self.client = client
        self.settings = get_settings()
        self._stop = threading.Event()
        self._online = True

    @property
    def is_online(self) -> bool:
        return self._online

    def run(self) -> None:
        logger.info("Device monitor started")
        info = collect_device_info(self.settings)
        logger.info(
            "Host=%s IP=%s OS=%s",
            info["hostname"],
            info["ip_address"],
            info["os_name"],
        )

        device_id = self.client.ensure_device()
        if device_id:
            self.client.send_log(
                f"Agent online on {info['hostname']} ({info['ip_address']})",
                category="device",
                severity="info",
                raw_payload=info,
            )
        else:
            logger.warning("Device registration failed — logs will queue until auth works")

        while not self._stop.is_set():
            reachable = self.client.is_server_reachable()
            if reachable:
                if not self.client.device_id:
                    device_id = self.client.ensure_device()
                    if device_id:
                        self.client.sync_offline_queue()
                        self.client.send_log(
                            f"Device registered: {device_id}",
                            category="device",
                            severity="info",
                        )
                ok = self.client.send_heartbeat()
                if ok and not self._online:
                    self.client.send_log("Device back online", category="device", severity="info")
                self._online = ok
            else:
                if self._online:
                    self.client.send_log(
                        "Server unreachable — operating in offline mode",
                        category="device",
                        severity="warning",
                    )
                self._online = False

            self._stop.wait(self.settings.heartbeat_interval)

    def stop(self) -> None:
        self._stop.set()
