"""Persist logs/alerts locally when the server is unreachable."""

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config.settings import get_settings


class OfflineQueue:
    """Thread-safe JSON queue for offline log and alert payloads."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._path: Path = get_settings().offline_queue_file
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._write({"logs": [], "alerts": []})

    def _read(self) -> dict[str, list]:
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            return {
                "logs": list(data.get("logs") or []),
                "alerts": list(data.get("alerts") or []),
            }
        except (OSError, json.JSONDecodeError):
            return {"logs": [], "alerts": []}

    def _write(self, data: dict[str, list]) -> None:
        self._path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def enqueue_log(self, payload: dict[str, Any]) -> None:
        with self._lock:
            data = self._read()
            entry = {**payload, "queued_at": datetime.now(timezone.utc).isoformat()}
            data["logs"].append(entry)
            self._write(data)

    def enqueue_alert(self, payload: dict[str, Any]) -> None:
        with self._lock:
            data = self._read()
            entry = {**payload, "queued_at": datetime.now(timezone.utc).isoformat()}
            data["alerts"].append(entry)
            self._write(data)

    def pending_counts(self) -> tuple[int, int]:
        with self._lock:
            data = self._read()
            return len(data["logs"]), len(data["alerts"])

    def drain_logs(self) -> list[dict[str, Any]]:
        with self._lock:
            data = self._read()
            logs = list(data["logs"])
            data["logs"] = []
            self._write(data)
            return logs

    def drain_alerts(self) -> list[dict[str, Any]]:
        with self._lock:
            data = self._read()
            alerts = list(data["alerts"])
            data["alerts"] = []
            self._write(data)
            return alerts
