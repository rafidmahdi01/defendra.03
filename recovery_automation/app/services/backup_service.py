"""
Backup system: ZIP compression, local storage, Firebase + optional S3, scheduled jobs.

Auto-detects device_id from system hostname if not provided.
Includes enterprise data filters (file size limits, extension blocklists, and system directory exclusions).
"""

import os
import platform
import zipfile
from pathlib import Path
from typing import Any

from app.integrations.firebase_client import FirebaseStorageClient
from app.integrations.firebase_storage import FirebaseBackupClient
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

# ---------------------------------------------------------------------------
# Enterprise Backup Filtering Constants
# ---------------------------------------------------------------------------

MAX_FILE_SIZE_MB: int = 50
MAX_FILE_SIZE_BYTES: int = MAX_FILE_SIZE_MB * 1024 * 1024

# Set of extensions to ignore heavy, non-essential, or temporary files
BLOCKED_EXTENSIONS: set[str] = {
    # Heavy media files
    ".mp4",
    ".mkv",
    ".avi",
    ".mov",
    ".wmv",
    ".flv",
    ".webm",
    ".m4v",
    ".mp3",
    ".wav",
    # Disk images & virtual machines
    ".iso",
    ".img",
    ".vmdk",
    ".vhd",
    ".vhdx",
    ".qcow2",
    ".dmg",
    # Executables, binaries & system installers
    ".exe",
    ".dll",
    ".sys",
    ".msi",
    ".cab",
    ".com",
    ".scr",
    ".bat",
    ".cmd",
    # Outlook data, temporary files, swap & crash dumps
    ".ost",
    ".pst",
    ".tmp",
    ".temp",
    ".bak",
    ".swp",
    ".dmp",
    ".log",
}

# System directories and hidden folders explicitly excluded from backups
EXCLUDED_DIR_NAMES: set[str] = {
    "windows",
    "program files",
    "program files (x86)",
    "programdata",
    "appdata",
    "application data",
    "local settings",
    "$recycle.bin",
    "system volume information",
    "recycler",
    "winnt",
    "temp",
    "tmp",
}

# Linux/Unix system root paths to exclude if running on POSIX systems
EXCLUDED_POSIX_ROOTS: tuple[str, ...] = (
    "/proc",
    "/sys",
    "/dev",
    "/etc",
    "/usr",
    "/bin",
    "/sbin",
    "/var/log",
    "/tmp",
)


def is_excluded_directory(dir_path: Path) -> bool:
    """
    Check if a directory path should be excluded based on system directory names,
    hidden AppData folders, dot-prefixed hidden directories, or POSIX system roots.
    """
    try:
        path_str = str(dir_path).replace("\\", "/")

        # POSIX system path check
        for posix_root in EXCLUDED_POSIX_ROOTS:
            if path_str == posix_root or path_str.startswith(posix_root + "/"):
                return True

        for part in dir_path.parts:
            part_lower = part.lower().strip()
            # Skip root drive specifiers like 'C:\' or '/'
            if not part_lower or part_lower.endswith(":") or part_lower == "/":
                continue

            # Explicitly exclude known system and temp directory names (e.g. C:\Windows, Program Files, AppData)
            if part_lower in EXCLUDED_DIR_NAMES:
                return True

            # Exclude hidden directories (starting with '.', e.g. .git, .cache, .vscode)
            if part_lower.startswith(".") and len(part_lower) > 1 and not part_lower.startswith(".."):
                return True

        return False
    except Exception as exc:
        logger.warning("Error checking exclusion for directory %s: %s", dir_path, exc)
        return True  # Exclude on error for safety


def should_include_file(file_path: Path) -> bool:
    """
    Validate whether an individual file should be included in the backup ZIP archive.

    Filters enforced:
    1. Parent directory exclusions (C:\\Windows, Program Files, hidden AppData, etc.)
    2. Extension Blocklist (.mp4, .iso, .exe, .ost, .tmp, etc.)
    3. File Size Limit (MAX_FILE_SIZE_MB = 50MB)
    4. Safe file attribute stat check (prevents OS-level permission crashes)
    """
    try:
        # 1. Check if containing directory or any parent is excluded
        if is_excluded_directory(file_path.parent):
            logger.debug("Skipping file in excluded directory path: %s", file_path)
            return False

        # 2. Check Extension Blocklist
        ext = file_path.suffix.lower()
        if ext in BLOCKED_EXTENSIONS:
            logger.info("Skipping file with blocked extension '%s': %s", ext, file_path)
            return False

        # 3. Check File Size Limit with exception guard against locked/unreadable files
        try:
            file_size = file_path.stat().st_size
        except (PermissionError, OSError) as perm_err:
            logger.warning("Skipping locked or unreadable file %s: %s", file_path, perm_err)
            return False

        if file_size > MAX_FILE_SIZE_BYTES:
            size_mb = file_size / (1024 * 1024)
            logger.info(
                "Skipping large file (%s, size: %.2f MB > %d MB limit)",
                file_path.name,
                size_mb,
                MAX_FILE_SIZE_MB,
            )
            return False

        return True

    except Exception as exc:
        logger.warning("Skipping file due to unexpected error during inspection %s: %s", file_path, exc)
        return False


class BackupService:
    """Create and list compressed backups."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.s3 = FirebaseBackupClient()
        self.firebase = FirebaseStorageClient()
        self.settings.backup_root_path.mkdir(parents=True, exist_ok=True)

    def _get_device_id(self, provided_device_id: str | None = None) -> str:
        """
        Get device ID for backup. Priority:
        1. Explicitly provided device_id (from request)
        2. Auto-detected from system hostname
        
        Returns sanitized device_id suitable for storage paths.
        """
        if provided_device_id and provided_device_id.strip():
            device_id = provided_device_id.strip()
            logger.info("Using provided device_id: %s", device_id)
            return device_id
        
        # Auto-detect from system hostname
        hostname = platform.node() or "unknown-device"
        # Sanitize: replace spaces and special chars with hyphens
        device_id = hostname.lower().replace(" ", "-").replace("_", "-")
        # Remove any remaining non-alphanumeric chars except hyphens
        device_id = "".join(c if c.isalnum() or c == "-" else "" for c in device_id)
        
        logger.info("Auto-detected device_id from hostname: %s (original: %s)", device_id, hostname)
        return device_id

    def create_backup(
        self,
        paths: list[str] | None = None,
        label: str | None = None,
        device_id: str | None = None,
        user_email: str | None = None,
    ) -> dict[str, Any]:
        """
        Backup selected files/folders into a ZIP under backups/.
        Auto-detects device_id from system hostname if not provided.
        Uploads to Firebase (primary) and S3 (optional).
        
        Args:
            paths: List of paths to backup
            label: Backup label
            device_id: Device identifier
            user_email: Email of user creating the backup (for filtering)
        """
        backup_id = generate_backup_id()
        
        # Auto-detect device_id if not provided
        device_id = self._get_device_id(device_id)
        
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

        def _on_walk_error(error: OSError) -> None:
            logger.warning(
                "Permission or OS error accessing directory %s: %s",
                getattr(error, "filename", "unknown"),
                error,
            )

        logger.info("Creating backup %s from %d path(s) for device: %s", backup_id, len(targets), device_id)
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for target in targets:
                try:
                    if is_excluded_directory(target):
                        logger.info("Skipping excluded target directory scope: %s", target)
                        continue

                    if target.is_file():
                        if should_include_file(target):
                            zf.write(target, arcname=target.name)
                            file_count += 1
                    elif target.is_dir():
                        for root, dirnames, filenames in os.walk(
                            target, topdown=True, onerror=_on_walk_error, followlinks=False
                        ):
                            root_path = Path(root)

                            # Prune excluded directories in-place to prevent os.walk from entering system/AppData folders
                            kept_dirs = []
                            for d in dirnames:
                                child_dir = root_path / d
                                if is_excluded_directory(child_dir):
                                    logger.debug("Pruning excluded sub-directory from traversal: %s", child_dir)
                                else:
                                    kept_dirs.append(d)
                            dirnames[:] = kept_dirs

                            # Evaluate each file in current directory
                            for filename in filenames:
                                item = root_path / filename
                                if should_include_file(item):
                                    try:
                                        if target.parent == target:
                                            arcname = str(item.relative_to(target))
                                        else:
                                            arcname = str(item.relative_to(target.parent))
                                        zf.write(item, arcname=arcname)
                                        file_count += 1
                                    except (PermissionError, OSError) as write_err:
                                        logger.warning(
                                            "Skipping file due to OS permission error while archiving %s: %s",
                                            item,
                                            write_err,
                                        )
                                    except Exception as write_err:
                                        logger.warning("Failed to archive file %s: %s", item, write_err)

                except (PermissionError, OSError) as target_err:
                    logger.warning("Permission error while processing target path %s: %s", target, target_err)
                except Exception as target_err:
                    logger.warning("Unexpected error while processing target path %s: %s", target, target_err)

        size_bytes = zip_path.stat().st_size
        
        # Upload to Firebase Storage (primary cloud storage) - always has device_id now
        firebase_uri = self.firebase.upload_backup(zip_path, device_id, backup_id)
        
        # Upload to S3 (legacy/optional secondary storage)
        s3_uri = self.s3.upload_backup(zip_path, backup_id)
        rclone_status = self._rclone_sync_placeholder(zip_path)

        meta = {
            "backup_id": backup_id,
            "label": label or "manual",
            "device_id": device_id,
            "user_email": user_email,
            "created_at": utc_now_iso(),
            "paths": [str(p) for p in targets],
            "file_count": file_count,
            "size_bytes": size_bytes,
            "archive": str(zip_path.name),
            "firebase_uri": firebase_uri,
            "s3_uri": s3_uri,
            "rclone_status": rclone_status,
        }
        write_metadata(backup_id, meta)
        removed = prune_old_backups(self.settings.backup_retention_days)
        if removed:
            logger.info("Pruned %d old backup(s)", removed)

        logger.info("Backup complete: %s (%d bytes)", backup_id, size_bytes)
        return meta

    def list_backups(
        self, 
        device_id: str | None = None,
        user_email: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Return metadata for all local backups, newest first.
        
        Args:
            device_id: If provided, filter to show only backups for this device.
            user_email: If provided, filter to show only backups created by this user.
            Both None: show all backups (admin view).
        
        Note: Admin-downloaded backups are stored separately and excluded from this list.
        """
        root = self.settings.backup_root_path
        backups: list[dict[str, Any]] = []
        for meta_file in sorted(root.glob("*.meta.json"), reverse=True):
            try:
                import json

                data = json.loads(meta_file.read_text(encoding="utf-8"))
                
                # Filter by device_id if specified
                if device_id and data.get("device_id") != device_id:
                    continue
                
                # Filter by user_email if specified
                if user_email and data.get("user_email") != user_email:
                    continue
                
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
