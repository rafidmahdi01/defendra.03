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
        self.recovery_automation_url = self._get_recovery_url()

    def _get_recovery_url(self) -> str:
        """Resolve recovery automation URL with fallback to local or server URL."""
        if self.settings.recovery_automation_url:
            return self.settings.recovery_automation_url.rstrip("/")
        # Default local service port 8001
        return "http://127.0.0.1:8001"

    def _get_target_urls(self) -> list[str]:
        """Candidate URLs to contact for backup/recovery operations."""
        urls = []
        if self.settings.recovery_automation_url:
            urls.append(self.settings.recovery_automation_url.rstrip("/"))
        urls.append("http://127.0.0.1:8001")
        if self.settings.server_url:
            urls.append(self.settings.server_url.rstrip("/"))
        # Deduplicate preserving order
        seen = set()
        deduped = []
        for u in urls:
            if u not in seen:
                seen.add(u)
                deduped.append(u)
        return deduped

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
        This service will upload to Firebase/cloud and manage centralized backups.
        """
        try:
            import requests

            device_id = self._get_device_id()
            payload = {
                "paths": [str(local_path)],
                "label": f"{trigger}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
                "device_id": device_id,
            }

            last_error = ""
            for base_url in self._get_target_urls():
                try:
                    response = requests.post(
                        f"{base_url}/backup/create",
                        json=payload,
                        timeout=30,
                    )
                    if response.status_code == 201:
                        data = response.json()
                        logger.info("Cloud backup created via %s: %s", base_url, data.get("backup_id"))
                        return {
                            "status": "success",
                            "backup_id": data.get("backup_id"),
                            "s3_uri": data.get("s3_uri") or data.get("firebase_uri"),
                            "endpoint": base_url,
                        }
                    else:
                        last_error = f"{base_url} returned {response.status_code}: {response.text[:100]}"
                except Exception as exc:
                    last_error = str(exc)

            logger.warning("Cloud backup could not reach endpoints: %s", last_error)
            return {"status": "pending_local", "error": last_error}

        except Exception as e:
            logger.error("Cloud backup error: %s", e)
            return {"status": "error", "error": str(e)}

    def restore_backup(
        self,
        backup_id: str | None = None,
        target_dir: Path | str | None = None,
    ) -> dict:
        """
        Restore files from a backup.
        By default, restores directly into self.source (data/important) so that
        the recovered files immediately become part of the active backing-up files!
        """
        dest = Path(target_dir) if target_dir else self.source
        dest.mkdir(parents=True, exist_ok=True)
        recovered_count = 0
        method_used = "none"

        # 1. Try recovery automation service (cloud or local)
        try:
            import requests

            for base_url in self._get_target_urls():
                try:
                    resp = requests.post(
                        f"{base_url}/backup/restore",
                        json={
                            "backup_id": backup_id,
                            "target_dir": str(dest),
                            "restore_to_original": True,
                        },
                        timeout=20,
                    )
                    if resp.status_code in (200, 201):
                        data = resp.json()
                        recovered_count = data.get("files_extracted", 0)
                        method_used = f"recovery_service ({base_url})"
                        logger.info("Restored via %s: %d files to %s", base_url, recovered_count, dest)
                        break
                except Exception as exc:
                    logger.debug("Restore attempt failed on %s: %s", base_url, exc)
        except ImportError:
            pass

        # 2. Local fallback if recovery service did not extract files or was unreachable
        if recovered_count == 0 and self.backup_dir.exists():
            candidates = sorted(
                [d for d in self.backup_dir.iterdir() if d.is_dir() and d.name != "important"],
                reverse=True,
            )
            if backup_id:
                matched = [d for d in candidates if backup_id in d.name]
                source_backup = matched[0] if matched else (candidates[0] if candidates else None)
            else:
                source_backup = candidates[0] if candidates else None

            if source_backup and source_backup.exists():
                for item in source_backup.rglob("*"):
                    if item.is_file():
                        try:
                            rel = item.relative_to(source_backup)
                            target_file = dest / rel
                            target_file.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(item, target_file)
                            recovered_count += 1
                        except Exception as e:
                            logger.error("Failed to restore file %s: %s", item, e)
                method_used = f"local_archive ({source_backup.name})"
                logger.info("Restored locally from %s: %d files to %s", source_backup, recovered_count, dest)

        result = {
            "backup_id": backup_id or "latest",
            "destination": str(dest),
            "files_recovered": recovered_count,
            "method": method_used,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Log event to Defendra server
        try:
            self.client.send_log(
                f"File recovery completed: {recovered_count} files restored to {dest} via {method_used}",
                category="backup",
                severity="info",
                source="backup_manager",
                raw_payload=result,
            )
        except Exception as e:
            logger.error("Failed to log recovery event: %s", e)

        return result

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
