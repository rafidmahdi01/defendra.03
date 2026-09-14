"""Local backup of important files with cloud sync logging."""

from __future__ import annotations

import json
import logging
import shutil
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from config.settings import get_settings

if TYPE_CHECKING:
    from core.api_client import DefendraClient

logger = logging.getLogger("client.backup")


class BackupManager:
    """
    Backup system with dual storage:
    1. Local backup: Copy files to backups/ folder on user's PC
    2. Cloud backup: Send backups to recovery_automation service (which pushes to cloud)
    """

    def __init__(self, client: DefendraClient) -> None:
        self.client = client
        self.settings = get_settings()
        self._stop = threading.Event()
        self.source = self.settings.data_dir / "important"
        self.backup_dir = self.settings.backup_dir
        self.cloud_marker = self.backup_dir / "cloud_sync.json"
        self.recovery_automation_url = "http://127.0.0.1:8001"  # Recovery automation service

    def run(self) -> None:
        logger.info("Backup manager started (Local + Cloud)")
        self.source.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        while not self._stop.is_set():
            self._stop.wait(self.settings.backup_interval)
            if not self._stop.is_set():
                self.run_backup(trigger="scheduled")

    def run_backup(self, trigger: str = "manual") -> dict:
        """
        Perform dual backup:
        - Local: Save to user's PC backup folder
        - Cloud: Send to recovery_automation service
        
        Returns status dict with local and cloud info.
        """
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        dest = self.backup_dir / stamp
        dest.mkdir(parents=True, exist_ok=True)

        # === LOCAL BACKUP ===
        local_copied = self._local_backup(dest)

        # === CLOUD BACKUP ===
        cloud_result = self._cloud_backup(dest, local_copied, trigger)

        # === LOG TO SERVER ===
        self._log_backup_event(dest, local_copied, cloud_result, trigger)

        result = {
            "timestamp": stamp,
            "trigger": trigger,
            "local_files": local_copied,
            "local_path": str(dest),
            "cloud_status": cloud_result.get("status", "pending"),
            "cloud_backup_id": cloud_result.get("backup_id", None),
        }
        logger.info(
            "Dual backup complete: %d local files, cloud_status=%s",
            local_copied,
            cloud_result.get("status"),
        )
        return result

    def _local_backup(self, dest: Path) -> int:
        """Copy files from important/ to local backups folder."""
        copied = 0
        if not self.source.exists():
            logger.warning("Backup source %s does not exist", self.source)
            return 0

        for src in self.source.rglob("*"):
            if src.is_file():
                try:
                    rel = src.relative_to(self.source)
                    target = dest / rel
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, target)
                    copied += 1
                except Exception as e:
                    logger.error("Failed to copy %s: %s", src, e)

        logger.info("Local backup: %d files saved to %s", copied, dest)
        return copied

    def _cloud_backup(self, local_path: Path, file_count: int, trigger: str) -> dict:
        """
        Send backup to recovery_automation service for cloud storage.
        This service will upload to S3/cloud and manage centralized backups.
        """
        try:
            import requests

            device_id = self._get_device_id()
            payload = {
                "paths": [str(local_path)],
                "label": f"{trigger}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
                "device_id": device_id,
            }

            # POST to recovery_automation backup endpoint
            response = requests.post(
                f"{self.recovery_automation_url}/backup/create",
                json=payload,
                timeout=30,
            )

            if response.status_code == 201:
                data = response.json()
                logger.info("Cloud backup created: %s", data.get("backup_id"))
                return {
                    "status": "success",
                    "backup_id": data.get("backup_id"),
                    "s3_uri": data.get("s3_uri"),
                }
            else:
                logger.warning(
                    "Cloud backup failed (status=%d): %s",
                    response.status_code,
                    response.text,
                )
                return {"status": "failed", "error": response.text}

        except Exception as e:
            logger.error("Cloud backup error: %s", e)
            return {"status": "error", "error": str(e)}

    def _get_device_id(self) -> str:
        """Retrieve device ID from device_id.txt."""
        try:
            if self.settings.device_id_file.exists():
                return self.settings.device_id_file.read_text(encoding="utf-8").strip()
        except Exception as e:
            logger.error("Failed to read device ID: %s", e)
        return "unknown"

    def _log_backup_event(self, dest: Path, local_count: int, cloud_result: dict, trigger: str) -> None:
        """Log backup event to Defendra server."""
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "trigger": trigger,
            "local_path": str(dest),
            "local_files": local_count,
            "cloud_backup_id": cloud_result.get("backup_id"),
            "cloud_status": cloud_result.get("status"),
            "s3_uri": cloud_result.get("s3_uri"),
        }

        # Update history file
        history: list = []
        if self.cloud_marker.exists():
            try:
                history = json.loads(self.cloud_marker.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                history = []
        history.append(record)
        self.cloud_marker.write_text(json.dumps(history[-100:], indent=2), encoding="utf-8")

        # Send to Defendra API
        try:
            self.client.send_log(
                f"Dual backup: {local_count} files local, cloud_id={cloud_result.get('backup_id')}",
                category="backup",
                severity="info",
                source="backup_manager",
                raw_payload=record,
            )
        except Exception as e:
            logger.error("Failed to log backup event: %s", e)

    def stop(self) -> None:
        self._stop.set()
