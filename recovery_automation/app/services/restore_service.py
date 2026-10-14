"""
Restore system: selected backup, latest backup, emergency recovery workflow.
"""

import shutil
import zipfile
from pathlib import Path
from typing import Any

from app.integrations.api_client import get_api_client
from app.integrations.firebase_client import FirebaseStorageClient
from app.integrations.firebase_storage import FirebaseBackupClient
from app.services.backup_service import BackupService
from app.utils.config import get_settings
from app.utils.helper import archive_path, read_metadata, utc_now_iso
from app.utils.logger import get_logger

logger = get_logger("restore_service")


class RestoreService:
    """Restore from local (or Firebase/S3) backup archives."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.backup_service = BackupService()
        self.firebase = FirebaseStorageClient()
        self.s3 = FirebaseBackupClient()
        self.api = get_api_client()

    def restore_backup(
        self,
        backup_id: str,
        target_dir: str | None = None,
        restore_to_original: bool = True,
    ) -> dict[str, Any]:
        """Restore a specific backup ZIP to target directory or original location."""
        meta = read_metadata(backup_id)
        if not meta:
            raise FileNotFoundError(f"Backup metadata not found: {backup_id}")

        zip_path = archive_path(backup_id)
        # If local ZIP missing, attempt Firebase Storage download first, then S3
        if not zip_path.exists():
            if self.firebase.enabled:
                device_id = meta.get("device_id") or ""
                logger.info("Local ZIP missing; attempting Firebase Storage download for %s (device %s)", backup_id, device_id)
                self.firebase.download_backup(device_id, backup_id, zip_path)
            if not zip_path.exists() and self.s3.enabled:
                logger.info("Local ZIP missing; attempting S3 download for %s", backup_id)
                self.s3.download_backup(backup_id, zip_path)

        if not zip_path.exists():
            raise FileNotFoundError(f"Backup archive not found: {backup_id}")

        # Determine target destinations
        destinations: list[Path] = []
        if target_dir:
            destinations.append(Path(target_dir))
        else:
            # When target_dir is omitted, restore directly back to original paths so files are in backing up files!
            if restore_to_original and meta.get("paths"):
                for orig in meta.get("paths", []):
                    p = Path(orig)
                    # If orig was client/backups/{timestamp}, the actual source being backed up is client/data/important
                    if "backups" in p.parts:
                        # Find client root and data/important
                        client_idx = None
                        for idx, part in enumerate(p.parts):
                            if part.lower() == "client":
                                client_idx = idx
                                break
                        if client_idx is not None:
                            client_root = Path(*p.parts[: client_idx + 1])
                            client_important = client_root / "data" / "important"
                            if client_important not in destinations:
                                destinations.append(client_important)
                    if p.exists() or p.parent.exists():
                        if p not in destinations:
                            destinations.append(p)

            # Always ensure a fallback destination
            fallback_dir = self.settings.backup_root_path / "restored" / backup_id
            if not destinations:
                destinations.append(fallback_dir)

        # Extract archive
        extracted = 0
        restored_destinations: list[str] = []

        with zipfile.ZipFile(zip_path, "r") as zf:
            namelist = zf.namelist()

            for dest in destinations:
                dest.mkdir(parents=True, exist_ok=True)
                restored_destinations.append(str(dest))

                # Identify if there is a common top-level directory wrapper (e.g. "20261014_120000/" or "important/")
                top_dirs = {name.split("/")[0] for name in namelist if "/" in name}
                single_wrapper = len(top_dirs) == 1 and all("/" in name for name in namelist if not name.endswith("/"))
                wrapper_prefix = f"{next(iter(top_dirs))}/" if single_wrapper else ""

                for member in namelist:
                    if member.endswith("/"):
                        continue

                    # If writing to a designated folder like data/important, strip the wrapper prefix so files sit cleanly inside
                    rel_name = member[len(wrapper_prefix):] if (wrapper_prefix and member.startswith(wrapper_prefix)) else member
                    target_file = dest / rel_name
                    target_file.parent.mkdir(parents=True, exist_ok=True)

                    with zf.open(member, "r") as source_fp, open(target_file, "wb") as dest_fp:
                        shutil.copyfileobj(source_fp, dest_fp)
                    extracted += 1

        primary_target = restored_destinations[0] if restored_destinations else str(self.settings.backup_root_path / "restored" / backup_id)
        result = {
            "backup_id": backup_id,
            "restored_at": utc_now_iso(),
            "target": primary_target,
            "destinations": restored_destinations,
            "files_extracted": extracted,
            "status": "completed",
        }
        logger.info("Restored backup %s -> %s (%d files)", backup_id, restored_destinations, extracted)

        self.api.update_dashboard(
            event="backup.restored",
            payload=result,
        )
        return result

    def restore_latest(self, target_dir: str | None = None, restore_to_original: bool = True) -> dict[str, Any]:
        """Restore the most recent backup."""
        backups = self.backup_service.list_backups()
        if not backups:
            raise FileNotFoundError("No backups available")
        latest = backups[0]
        return self.restore_backup(latest["backup_id"], target_dir=target_dir, restore_to_original=restore_to_original)

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
