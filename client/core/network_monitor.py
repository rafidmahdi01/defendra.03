"""Monitor network/server connectivity and trigger offline sync."""

from __future__ import annotations

import logging
import threading
import time
from typing import Callable

from config.settings import get_settings
from core.api_client import DefendraClient

logger = logging.getLogger("client.network")


class NetworkMonitor:
    """Tracks internet + server reachability; syncs queue when back online."""

    def __init__(
        self,
        client: DefendraClient,
        *,
        on_online: Callable[[], None] | None = None,
        on_offline: Callable[[], None] | None = None,
    ) -> None:
        self.client = client
        self.settings = get_settings()
        self.on_online = on_online
        self.on_offline = on_offline
        self._was_online = client.is_server_reachable()
        self._stop = threading.Event()

    def run(self) -> None:
        logger.info("Network monitor started (interval=%ss)", self.settings.network_check_interval)
        while not self._stop.is_set():
            online = self.client.is_internet_available() and self.client.is_server_reachable()
            if online and not self._was_online:
                logger.info("Connection restored — syncing offline queue")
                self.client.sync_offline_queue()
                if self.on_online:
                    self.on_online()
            elif not online and self._was_online:
                logger.warning("Connection lost — entering offline mode")
                if self.on_offline:
                    self.on_offline()
            self._was_online = online
            self._stop.wait(self.settings.network_check_interval)

    def stop(self) -> None:
        self._stop.set()
