"""Recovery, isolation, and limp-mode routes."""

from fastapi import APIRouter, HTTPException, status

from app.models.schemas import EmergencyRecoveryRequest, IsolationRequest
from app.services.isolation_service import IsolationService
from app.services.limp_mode_service import LimpModeService
from app.services.restore_service import RestoreService
from app.utils.logger import get_logger

logger = get_logger("recovery_routes")

router = APIRouter(prefix="/recovery", tags=["Recovery"])

_restore = RestoreService()
_isolation = IsolationService()
_limp = LimpModeService()


@router.post("/emergency", response_model=dict)
def emergency_recovery(payload: EmergencyRecoveryRequest) -> dict:
    """Run emergency recovery workflow for a device."""
    try:
        return _restore.emergency_recovery(
            payload.device_id,
            create_snapshot=payload.create_snapshot,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Emergency recovery failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.post("/isolate", response_model=dict)
def isolate_device(payload: IsolationRequest) -> dict:
    """Simulate device isolation (safe mode)."""
    return _isolation.isolate_device(
        payload.device_id,
        reason=payload.reason,
        block_network=payload.block_network,
        quarantine=payload.quarantine,
    )


@router.post("/isolate/{device_id}/release", response_model=dict)
def release_isolation(device_id: str) -> dict:
    """Release simulated isolation."""
    return _isolation.release_device(device_id)


@router.get("/isolate/{device_id}", response_model=dict)
def isolation_status(device_id: str) -> dict:
    return _isolation.get_status(device_id)


@router.post("/limp-mode/enable", response_model=dict)
def enable_limp_mode(reason: str = "manual") -> dict:
    return _limp.enable(reason=reason)


@router.post("/limp-mode/disable", response_model=dict)
def disable_limp_mode() -> dict:
    return _limp.disable()


@router.get("/limp-mode/status", response_model=dict)
def limp_mode_status() -> dict:
    return _limp.status()


@router.get("/status", response_model=dict)
def recovery_status() -> dict:
    """Overall recovery module status."""
    return {
        "module": "recovery_automation",
        "limp_mode": _limp.status(),
        "isolated_devices": _isolation.list_isolated(),
        "backup_count": len(_restore.backup_service.list_backups()),
    }
