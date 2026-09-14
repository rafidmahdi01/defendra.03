"""
Dynamic backup scheduler — supports runtime reconfiguration without restart.
"""

import threading
import time
from typing import Any

from app.utils.logger import get_logger

logger = get_logger("scheduler")


class BackupScheduler:
    """
    Manages an interval-based backup schedule that can be reconfigured at runtime.
    The scheduler runs in its own daemon thread.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

        self._enabled: bool = False
        self._interval_minutes: int = 60
        self._paths: list[str] = []
        self._label: str = "scheduled"

        self._last_run_at: str | None = None
        self._next_run_at: str | None = None
        self._run_count: int = 0

    # ── Public API ──────────────────────────────────────────────────────────

    def configure(
        self,
        enabled: bool,
        interval_minutes: int,
        paths: list[str] | None = None,
        label: str = "scheduled",
    ) -> dict[str, Any]:
        """Update schedule config and restart the scheduler thread if needed."""
        with self._lock:
            self._enabled = enabled
            self._interval_minutes = max(1, interval_minutes)
            self._paths = paths or []
            self._label = label or "scheduled"

        self._restart_thread()
        logger.info(
            "Scheduler configured: enabled=%s interval=%dm paths=%s",
            enabled,
            interval_minutes,
            paths,
        )
        return self.status()

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "enabled": self._enabled,
                "interval_minutes": self._interval_minutes,
                "paths": list(self._paths),
                "label": self._label,
                "last_run_at": self._last_run_at,
                "next_run_at": self._next_run_at,
                "run_count": self._run_count,
                "thread_alive": self._thread is not None and self._thread.is_alive(),
            }

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3)
        self._thread = None
        logger.info("Scheduler stopped")

    # ── Internal ─────────────────────────────────────────────────────────────

    def _restart_thread(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3)

        if not self._enabled:
            self._thread = None
            logger.info("Scheduler disabled — thread not started")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop,
            daemon=True,
            name="backup-scheduler",
        )
        self._thread.start()
        logger.info("Scheduler thread (re)started, interval=%dm", self._interval_minutes)

    def _run_loop(self) -> None:
        from app.services.backup_service import BackupService

        backup_svc = BackupService()

        while not self._stop_event.is_set():
            interval_secs = self._interval_minutes * 60
            # Sleep in small chunks so we can react to stop quickly
            elapsed = 0
            while elapsed < interval_secs and not self._stop_event.is_set():
                time.sleep(min(5, interval_secs - elapsed))
                elapsed += 5

            if self._stop_event.is_set():
                break

            with self._lock:
                paths = list(self._paths)
                label = self._label
                enabled = self._enabled

            if not enabled:
                break

            try:
                from datetime import datetime, timezone
                result = backup_svc.create_backup(paths=paths or None, label=label)
                now_iso = datetime.now(timezone.utc).isoformat()
                with self._lock:
                    self._last_run_at = now_iso
                    self._run_count += 1
                logger.info("Scheduled backup completed: %s", result.get("backup_id"))
            except Exception as exc:
                logger.error("Scheduled backup failed: %s", exc)


# Module-level singleton
_scheduler = BackupScheduler()


def get_scheduler() -> BackupScheduler:
    return _scheduler
