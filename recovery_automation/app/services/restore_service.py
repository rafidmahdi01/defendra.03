"""
Restore system: selected backup, latest backup, emergency recovery workflow.
"""

import shutil
import zipfile
from pathlib import Path
from typing import Any

from app.integrations.api_client import get_api_client
from app.integrations.firebase_storage import FirebaseBackupClient
from app.services.backup_service import BackupService
from app.utils.config import get_settings
from app.utils.helper import archive_path, read_metadata, utc_now_iso
from app.utils.logger import get_logger

logger = get_logger("restore_service")


class RestoreService:
    """Restore from local (or S3) backup archives."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.backup_service = BackupService()
        self.s3 = FirebaseBackupClient()
        self.api = get_api_client()

    def restore_backup(
        self,
        backup_id: str,
        target_dir: str | None = None,
    ) -> dict[str, Any]:
        """Restore a specific backup ZIP to target directory."""
        meta = read_metadata(backup_id)
        if not meta:
            raise FileNotFoundError(f"Backup metadata not found: {backup_id}")

        zip_path = archive_path(backup_id)
        if not zip_path.exists() and self.s3.enabled:
            logger.info("Local ZIP missing; attempting S3 download")
            self.s3.download_backup(backup_id, zip_path)

        if not zip_path.exists():
            raise FileNotFoundError(f"Backup archive not found: {backup_id}")

        restore_root = Path(target_dir) if target_dir else self.settings.backup_root_path / "restored" / backup_id
        restore_root.mkdir(parents=True, exist_ok=True)

        extracted = 0
        with zipfile.ZipFile(zip_path, "r") as zf:
            for member in zf.namelist():
                zf.extract(member, restore_root)
                extracted += 1

        result = {
            "backup_id": backup_id,
            "restored_at": utc_now_iso(),
            "target": str(restore_root),
            "files_extracted": extracted,
            "status": "completed",
        }
        logger.info("Restored backup %s -> %s (%d files)", backup_id, restore_root, extracted)

        self.api.update_dashboard(
            event="backup.restored",
            payload=result,
        )
        return result

    def restore_latest(self, target_dir: str | None = None) -> dict[str, Any]:
        """Restore the most recent backup."""
        backups = self.backup_service.list_backups()
        if not backups:
            raise FileNotFoundError("No backups available")
        latest = backups[0]
        return self.restore_backup(latest["backup_id"], target_dir=target_dir)

    def emergency_recovery(
        self,
        device_id: str,
        *,
        create_snapshot: bool = True,
    ) -> dict[str, Any]:
        """
        Emergency workflow:
        1. Snapshot current state (optional backup)
        2. Restore latest backup
        3. Notify Defendra APIs
        """
        logger.warning("Emergency recovery initiated for device %s", device_id)
        steps: list[dict[str, Any]] = []

        if create_snapshot:
            snap = self.backup_service.create_backup(
                label="emergency_pre_restore",
                device_id=device_id,
            )
            steps.append({"step": "pre_restore_snapshot", "result": snap})

        restore_result = self.restore_latest()
        steps.append({"step": "restore_latest", "result": restore_result})

        self.api.send_alert(
            title="Emergency Recovery Executed",
            description=f"Emergency recovery completed for device {device_id}",
            severity="critical",
            device_id=device_id,
            rule_name="emergency_recovery",
        )
        self.api.update_dashboard(
            event="emergency.recovery.completed",
            device_id=device_id,
            payload={"steps": len(steps)},
        )

        return {
            "device_id": device_id,
            "status": "completed",
            "steps": steps,
            "completed_at": utc_now_iso(),
        }
