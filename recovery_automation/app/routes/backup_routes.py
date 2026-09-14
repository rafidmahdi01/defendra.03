"""Backup API routes."""

from fastapi import APIRouter, HTTPException, status

from app.models.schemas import BackupCreateRequest, BackupRestoreRequest, ScheduleConfigRequest
from app.services.backup_service import BackupService
from app.services.restore_service import RestoreService
from app.services.scheduler import get_scheduler
from app.utils.logger import get_logger

logger = get_logger("backup_routes")

router = APIRouter(prefix="/backup", tags=["Backup"])

_backup = BackupService()
_restore = RestoreService()


@router.post("/create", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_backup(payload: BackupCreateRequest) -> dict:
    """Create a new ZIP backup of selected paths."""
    try:
        result = _backup.create_backup(
            paths=payload.paths,
            label=payload.label,
            device_id=payload.device_id,
        )
        return result
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Backup creation failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.get("/list", response_model=list)
def list_backups() -> list:
    """List all local backups with metadata."""
    return _backup.list_backups()


@router.delete("", response_model=dict)
def clear_backups() -> dict:
    """Delete all local backup archives and metadata."""
    try:
        return _backup.clear_all_backups()
    except Exception as exc:
        logger.exception("Backup history clear failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.post("/restore", response_model=dict)
def restore_backup(payload: BackupRestoreRequest) -> dict:
    """Restore a specific backup or the latest if backup_id is omitted."""
    try:
        if payload.backup_id:
            return _restore.restore_backup(
                payload.backup_id,
                target_dir=payload.target_dir,
            )
        return _restore.restore_latest(target_dir=payload.target_dir)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Restore failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.get("/schedule", response_model=dict)
def get_schedule() -> dict:
    """Get current auto-backup schedule configuration."""
    return get_scheduler().status()


@router.post("/schedule", response_model=dict, status_code=status.HTTP_200_OK)
def set_schedule(payload: ScheduleConfigRequest) -> dict:
    """Configure the auto-backup schedule (interval in minutes)."""
    return get_scheduler().configure(
        enabled=payload.enabled,
        interval_minutes=payload.interval_minutes,
        paths=payload.paths,
        label=payload.label or "scheduled",
    )


@router.delete("/schedule", response_model=dict)
def stop_schedule() -> dict:
    """Stop the auto-backup schedule."""
    get_scheduler().stop()
    return {"message": "Scheduler stopped", "enabled": False}


@router.post("/sync-centralized", response_model=dict, status_code=status.HTTP_200_OK)
def sync_centralized_backups() -> dict:
    """
    Server-side: Sync all device backups to cloud storage.
    Ensures every user PC backup is replicated to S3/cloud.
    """
    try:
        result = _backup.sync_centralized_backups()
        return result
    except Exception as exc:
        logger.exception("Centralized backup sync failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.get("/device/{device_id}", response_model=list)
def get_device_backups(device_id: str) -> list:
    """Get all backups for a specific device."""
    try:
        return _backup.get_device_backups(device_id)
    except Exception as exc:
        logger.exception("Failed to retrieve device backups")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.get("/stats", response_model=dict)
def get_backup_stats() -> dict:
    """Get backup statistics (cloud vs local, device count, etc.)."""
    try:
        return _backup.get_backup_stats()
    except Exception as exc:
        logger.exception("Failed to retrieve backup stats")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
