"""Send alerts to the Defendra dashboard (optional local pop-ups disabled by default)."""

from __future__ import annotations

import logging
import queue
import threading
from typing import TYPE_CHECKING

from config.settings import get_settings

if TYPE_CHECKING:
    from core.api_client import DefendraClient

logger = logging.getLogger("client.alerts")


class AlertSystem:
    """
    Routes agent notifications to the Defendra web dashboard via REST.

    Local tkinter pop-ups are off by default (ENABLE_POPUP_ALERTS=false).
    """

    def __init__(self, client: DefendraClient) -> None:
        self.client = client
        self.settings = get_settings()
        self._queue: queue.Queue[tuple[str, str, str]] = queue.Queue()
        self._stop = threading.Event()
        self._ui_thread: threading.Thread | None = None

    def start(self) -> None:
        if self.settings.enable_popup_alerts and self._ui_thread is None:
            logger.warning(
                "Local pop-up alerts enabled — set ENABLE_POPUP_ALERTS=false for dashboard-only"
            )
            self._ui_thread = threading.Thread(
                target=self._ui_loop, daemon=True, name="alert-ui"
            )
            self._ui_thread.start()

    def notify(
        self,
        title: str,
        message: str,
        *,
        severity: str = "high",
        rule_name: str = "client_agent",
        popup: bool = False,
        send_to_server: bool = True,
    ) -> None:
        """Send alert to Defendra dashboard; optional local popup if explicitly enabled."""
        if send_to_server:
            ok = self.client.send_alert(
                title, message, severity=severity, rule_name=rule_name
            )
            if ok:
                logger.info("Alert sent to dashboard: %s", title)
            else:
                logger.info("Alert queued for dashboard sync: %s", title)

        self.client.send_log(
            f"{title}: {message}",
            category="alert",
            severity=severity,
            source=rule_name,
        )

        if popup and self.settings.enable_popup_alerts:
            self._queue.put((title, message, severity))

    def _ui_loop(self) -> None:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()

        while not self._stop.is_set():
            try:
                title, message, severity = self._queue.get(timeout=0.5)
            except queue.Empty:
                root.update()
                continue

            root.attributes("-topmost", True)
            if severity in ("critical", "high"):
                messagebox.showwarning(title, message, parent=root)
            else:
                messagebox.showinfo(title, message, parent=root)
            root.update()

        root.destroy()

    def stop(self) -> None:
        self._stop.set()
