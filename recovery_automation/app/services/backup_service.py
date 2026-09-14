"""
Backup system: ZIP compression, local storage, optional S3, scheduled jobs.
"""

import zipfile
from pathlib import Path
from typing import Any

from app.integrations.s3_client import S3BackupClient
from app.utils.config import get_settings
from app.utils.helper import (
    archive_path,
    generate_backup_id,
    prune_old_backups,
    resolve_safe_paths,
    utc_now_iso,
    write_metadata,
)
from app.utils.logger import get_logger

logger = get_logger("backup_service")


class BackupService:
    """Create and list compressed backups."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.s3 = S3BackupClient()
        self.settings.backup_root_path.mkdir(parents=True, exist_ok=True)

    def create_backup(
        self,
        paths: list[str] | None = None,
        label: str | None = None,
        device_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Backup selected files/folders into a ZIP under backups/.
        Optionally uploads to S3 and records rclone placeholder status.
        """
        backup_id = generate_backup_id()
        if paths:
            targets = resolve_safe_paths(paths)
            if not targets:
                raise ValueError(
                    "No backup sources matched the paths you sent. Each path must exist on "
                    "the PC where the backup service runs. Remove quotation marks around paths, "
                    "check drive letters/spelling (including Unicode in names), then try again."
                )
        else:
            targets = resolve_safe_paths(self.settings.default_backup_paths)

        if not targets:
            # Create minimal manifest backup when default paths yield nothing (dev workflow)
            manifest_dir = self.settings.backup_root_path / "_manifest"
            manifest_dir.mkdir(parents=True, exist_ok=True)
            manifest_file = manifest_dir / f"{backup_id}.txt"
            manifest_file.write_text(
                f"Defendra recovery manifest\nbackup_id={backup_id}\n",
                encoding="utf-8",
            )
            targets = [manifest_dir]

        zip_path = archive_path(backup_id)
        file_count = 0

        logger.info("Creating backup %s from %d path(s)", backup_id, len(targets))
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for target in targets:
                if target.is_file():
                    zf.write(target, arcname=target.name)
                    file_count += 1
                elif target.is_dir():
                    for item in target.rglob("*"):
                        if item.is_file():
                            arcname = str(item.relative_to(target.parent))
                            zf.write(item, arcname=arcname)
                            file_count += 1

        size_bytes = zip_path.stat().st_size
        s3_uri = self.s3.upload_backup(zip_path, backup_id)
        rclone_status = self._rclone_sync_placeholder(zip_path)

        meta = {
            "backup_id": backup_id,
            "label": label or "manual",
            "device_id": device_id,
            "created_at": utc_now_iso(),
            "paths": [str(p) for p in targets],
            "file_count": file_count,
            "size_bytes": size_bytes,
            "archive": str(zip_path.name),
            "s3_uri": s3_uri,
            "rclone_status": rclone_status,
        }
        write_metadata(backup_id, meta)
        removed = prune_old_backups(self.settings.backup_retention_days)
        if removed:
            logger.info("Pruned %d old backup(s)", removed)

        logger.info("Backup complete: %s (%d bytes)", backup_id, size_bytes)
        return meta

    def list_backups(self) -> list[dict[str, Any]]:
        """Return metadata for all local backups, newest first."""
        root = self.settings.backup_root_path
        backups: list[dict[str, Any]] = []
        for meta_file in sorted(root.glob("*.meta.json"), reverse=True):
            try:
                import json

                data = json.loads(meta_file.read_text(encoding="utf-8"))
                zip_file = archive_path(data.get("backup_id", ""))
                data["exists"] = zip_file.exists()
                backups.append(data)
            except (OSError, json.JSONDecodeError) as exc:
                logger.error("Invalid metadata %s: %s", meta_file, exc)
        return backups

    def clear_all_backups(self) -> dict[str, Any]:
        """Remove all local backup ZIP archives and metadata files."""
        root = self.settings.backup_root_path
        deleted = 0
        for meta_file in list(root.glob("*.meta.json")):
            backup_id = meta_file.stem.replace(".meta", "")
            try:
                import json

                data = json.loads(meta_file.read_text(encoding="utf-8"))
                backup_id = data.get("backup_id", backup_id)
            except (OSError, json.JSONDecodeError):
                pass
            try:
                meta_file.unlink(missing_ok=True)
                archive_path(backup_id).unlink(missing_ok=True)
                deleted += 1
            except OSError as exc:
                logger.error("Failed to delete backup %s: %s", backup_id, exc)
        logger.info("Cleared %d backup(s) from local storage", deleted)
        return {"deleted": deleted, "status": "completed"}

    def _rclone_sync_placeholder(self, zip_path: Path) -> str:
        """
        Rclone sync placeholder — logs intent without executing destructive sync.
        Set RCLONE_ENABLED=true and RCLONE_REMOTE in .env for future wiring.
        """
        if not self.settings.rclone_enabled or not self.settings.rclone_remote:
            return "disabled"
        remote = self.settings.rclone_remote
        logger.info(
            "[RCLONE PLACEHOLDER] Would sync %s -> %s (not executed in simulation mode)",
            zip_path,
            remote,
        )
        return f"simulated:{remote}"

    def run_scheduled_backup(self) -> dict[str, Any]:
        """Invoked by scheduler thread."""
        logger.info("Running scheduled backup")
        return self.create_backup(label="scheduled")

    def sync_centralized_backups(self) -> dict[str, Any]:
        """
        Server-side centralization: Sync all device backups to cloud storage.
        Called periodically to ensure all user PC backups are replicated to cloud.
        Returns: Summary of synced backups.
        """
        logger.info("Starting centralized backup sync to cloud storage")
        backups = self.list_backups()
        synced_count = 0
        failed_count = 0
        total_size = 0

        for backup in backups:
            backup_id = backup.get("backup_id")
            zip_file = archive_path(backup_id)

            if not zip_file.exists():
                logger.warning("Backup file not found: %s", backup_id)
                failed_count += 1
                continue

            try:
                # Check if already in S3
                existing_s3_uri = backup.get("s3_uri")
                if existing_s3_uri and existing_s3_uri != "not_uploaded":
                    logger.info("Backup %s already in cloud: %s", backup_id, existing_s3_uri)
                    synced_count += 1
                    total_size += backup.get("size_bytes", 0)
                    continue

                # Upload to S3
                logger.info("Uploading backup %s to cloud...", backup_id)
                s3_uri = self.s3.upload_backup(zip_file, backup_id)

                if s3_uri and s3_uri != "not_uploaded":
                    # Update metadata
                    backup["s3_uri"] = s3_uri
                    backup["cloud_synced_at"] = utc_now_iso()
                    write_metadata(backup_id, backup)
                    synced_count += 1
                    total_size += backup.get("size_bytes", 0)
                    logger.info("Backup %s synced to cloud: %s", backup_id, s3_uri)
                else:
                    failed_count += 1
                    logger.error("Failed to upload backup %s to S3", backup_id)

            except Exception as e:
                failed_count += 1
                logger.error("Error syncing backup %s: %s", backup_id, e)

        result = {
            "status": "completed",
            "total_backups": len(backups),
            "synced_to_cloud": synced_count,
            "failed": failed_count,
            "total_size_bytes": total_size,
            "timestamp": utc_now_iso(),
        }
        logger.info("Centralized backup sync complete: %s", result)
        return result

    def get_device_backups(self, device_id: str) -> list[dict[str, Any]]:
        """Get all backups for a specific device."""
        all_backups = self.list_backups()
        return [b for b in all_backups if b.get("device_id") == device_id]

    def get_backup_stats(self) -> dict[str, Any]:
        """Get statistics about all backups (cloud vs local)."""
        backups = self.list_backups()
        cloud_count = sum(1 for b in backups if b.get("s3_uri") and b.get("s3_uri") != "not_uploaded")
        local_only_count = len(backups) - cloud_count
        total_size = sum(b.get("size_bytes", 0) for b in backups)
        device_ids = set(b.get("device_id") for b in backups if b.get("device_id"))

        return {
            "total_backups": len(backups),
            "cloud_backed": cloud_count,
            "local_only": local_only_count,
            "total_size_bytes": total_size,
            "unique_devices": len(device_ids),
            "devices": list(device_ids),
        }
