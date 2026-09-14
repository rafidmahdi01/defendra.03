from dataclasses import replace

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from google.cloud.firestore import Client

from auth.dependencies import get_current_user, require_admin
from database.firebase import get_firestore
from models.models import DeviceDoc, UserDoc
from models.schemas import (
    DeviceCreate,
    DeviceHeartbeat,
    DeviceRead,
    DeviceUpdate,
    MessageResponse,
    WorkstationLinkRequest,
)
from services.location_service import resolve_device_location
from websocket.manager import manager


router = APIRouter(prefix="/devices", tags=["Devices"])


def _is_admin(user: UserDoc) -> bool:
    return (user.role or "").lower() == "admin"


def _owner_fields(user: UserDoc) -> dict[str, str]:
    return {
        "user_id": user.id,
        "user_email": user.email,
        "user_full_name": user.full_name,
    }


def _doc_to_read(d: DeviceDoc) -> DeviceRead:
    user_name = d.user_full_name or d.user_email
    return DeviceRead(
        id=d.id,
        hostname=d.hostname,
        ip_address=d.ip_address,
        mac_address=d.mac_address,
        os_name=d.os_name,
        agent_version=d.agent_version,
        location=d.location,
        status=d.status,
        cpu_usage=d.cpu_usage,
        ram_usage=d.ram_usage,
        last_seen=d.last_seen,
        created_at=d.created_at,
        user_id=d.user_id,
        user_email=d.user_email,
        user_full_name=d.user_full_name,
        user_name=user_name,
    )


def _ensure_location(db: Client, device: DeviceDoc, *, request_ip: str | None = None) -> DeviceDoc:
    """Fill missing location from IP and persist so the dashboard stops showing placeholders."""
    if (device.location or "").strip():
        return device

    resolved = resolve_device_location(ip_address=device.ip_address, request_ip=request_ip)
    if not resolved or resolved == "Location unavailable":
        return device

    now = datetime.now(timezone.utc)
    db.collection("devices").document(device.id).update({"location": resolved, "updated_at": now})
    return replace(device, location=resolved, updated_at=now)


def _ensure_owner(db: Client, device: DeviceDoc) -> DeviceDoc:
    """Backfill missing owner display fields from the users collection."""
    if device.user_full_name or device.user_email:
        return device
    if not device.user_id:
        return device

    snap = db.collection("users").document(device.user_id).get()
    if not snap.exists:
        return device

    data = snap.to_dict() or {}
    full_name = data.get("full_name")
    email = data.get("email")
    if not full_name and not email:
        return device

    updates = {}
    if full_name:
        updates["user_full_name"] = full_name
    if email:
        updates["user_email"] = email
    if updates:
        now = datetime.now(timezone.utc)
        updates["updated_at"] = now
        db.collection("devices").document(device.id).update(updates)
        return replace(
            device,
            user_full_name=full_name or device.user_full_name,
            user_email=email or device.user_email,
            updated_at=now,
        )
    return device


def _prepare_device_for_read(db: Client, device: DeviceDoc) -> DeviceDoc:
    device = _ensure_owner(db, device)
    return _ensure_location(db, device)


def _load_device(db: Client, device_id: str) -> DeviceDoc:
    ref = db.collection("devices").document(device_id)
    snap = ref.get()
    if not snap.exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    return DeviceDoc.from_firestore(device_id, snap.to_dict() or {})


def _require_device_access(device: DeviceDoc, user: UserDoc) -> None:
    if _is_admin(user):
        return
    if device.user_id and device.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to access this device")


def _list_devices_for_user(db: Client, user: UserDoc) -> list[DeviceDoc]:
    if _is_admin(user):
        docs = db.collection("devices").stream()
    else:
        docs = db.collection("devices").where("user_id", "==", user.id).stream()
    devices = [DeviceDoc.from_firestore(d.id, d.to_dict() or {}) for d in docs]
    devices.sort(key=lambda d: (d.last_seen is None, d.last_seen or datetime.min.replace(tzinfo=timezone.utc)), reverse=True)
    return devices


@router.get("", response_model=list[DeviceRead])
def list_devices(db: Client = Depends(get_firestore), current_user: UserDoc = Depends(get_current_user)):
    """Admins see all fleet devices; regular users see only their linked PCs."""
    devices = [_prepare_device_for_read(db, d) for d in _list_devices_for_user(db, current_user)]
    return [_doc_to_read(d) for d in devices]


@router.post("/workstation/link", response_model=DeviceRead)
def link_workstation(
    payload: WorkstationLinkRequest,
    request: Request,
    db: Client = Depends(get_firestore),
    current_user: UserDoc = Depends(get_current_user),
):
    """Register or refresh this desktop as a managed endpoint for the signed-in user."""
    now = datetime.now(timezone.utc)
    owner = _owner_fields(current_user)
    request_ip = request.client.host if request.client else None
    ip_address = payload.ip_address or "127.0.0.1"
    location = resolve_device_location(
        ip_address=ip_address,
        provided=payload.location,
        request_ip=request_ip,
    )

    existing = list(
        db.collection("devices")
        .where("hostname", "==", payload.hostname)
        .where("user_id", "==", current_user.id)
        .limit(1)
        .stream()
    )
    if existing:
        snap = existing[0]
        ref = snap.reference
        data = snap.to_dict() or {}
        ref.update(
            {
                **owner,
                "status": "online",
                "last_seen": now,
                "updated_at": now,
                "os_name": payload.os_name or payload.platform or data.get("os_name"),
                "agent_version": payload.agent_version or data.get("agent_version") or "defendra-desktop",
                "ip_address": ip_address,
                "location": location,
            }
        )
        device = DeviceDoc.from_firestore(ref.id, ref.get().to_dict() or {})
        return _doc_to_read(device)

    ref = db.collection("devices").document()
    ref.set(
        {
            "hostname": payload.hostname,
            "ip_address": ip_address,
            "mac_address": None,
            "os_name": payload.os_name or payload.platform,
            "agent_version": payload.agent_version or "defendra-desktop",
            "location": location,
            "status": "online",
            "cpu_usage": 0.0,
            "ram_usage": 0.0,
            "last_seen": now,
            "created_at": now,
            "updated_at": now,
            **owner,
        }
    )
    device = DeviceDoc.from_firestore(ref.id, ref.get().to_dict() or {})
    return _doc_to_read(device)


@router.post("", response_model=DeviceRead, status_code=status.HTTP_201_CREATED)
async def create_device(
    payload: DeviceCreate,
    request: Request,
    db: Client = Depends(get_firestore),
    current_user: UserDoc = Depends(get_current_user),
):
    now = datetime.now(timezone.utc)
    location = resolve_device_location(
        ip_address=payload.ip_address,
        provided=payload.location,
        request_ip=request.client.host if request.client else None,
    )
    ref = db.collection("devices").document()
    ref.set(
        {
            **payload.model_dump(),
            "location": location,
            **_owner_fields(current_user),
            "status": "offline",
            "cpu_usage": 0.0,
            "ram_usage": 0.0,
            "last_seen": None,
            "created_at": now,
            "updated_at": now,
        }
    )
    device = DeviceDoc.from_firestore(ref.id, ref.get().to_dict() or {})
    await manager.broadcast("device.created", {"id": device.id, "hostname": device.hostname})
    return _doc_to_read(device)


@router.put("/{device_id}", response_model=DeviceRead)
async def update_device(
    device_id: str,
    payload: DeviceUpdate,
    db: Client = Depends(get_firestore),
    current_user: UserDoc = Depends(get_current_user),
):
    device = _load_device(db, device_id)
    _require_device_access(device, current_user)

    ref = db.collection("devices").document(device_id)
    updates = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}
    updates["updated_at"] = datetime.now(timezone.utc)
    ref.update(updates)

    device = DeviceDoc.from_firestore(device_id, ref.get().to_dict() or {})
    await manager.broadcast("device.updated", {"id": device.id, "status": device.status})
    return _doc_to_read(device)


@router.delete("/{device_id}", response_model=MessageResponse)
def delete_device(
    device_id: str,
    db: Client = Depends(get_firestore),
    _: UserDoc = Depends(require_admin),
):
    ref = db.collection("devices").document(device_id)
    if not ref.get().exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    ref.delete()
    return {"message": "Device deleted"}


@router.delete("", response_model=MessageResponse)
async def delete_all_devices(
    db: Client = Depends(get_firestore),
    current_user: UserDoc = Depends(get_current_user),
):
    """Delete all devices. Admins delete all fleet devices; regular users delete only their own devices."""
    devices = _list_devices_for_user(db, current_user)
    
    if not devices:
        return {"message": "No devices to delete"}
    
    # Batch delete for better performance
    batch = db.batch()
    count = 0
    
    for device in devices:
        ref = db.collection("devices").document(device.id)
        batch.delete(ref)
        count += 1
        
        # Firestore batch limit is 500 operations
        if count % 500 == 0:
            batch.commit()
            batch = db.batch()
    
    # Commit remaining operations
    if count % 500 != 0:
        batch.commit()
    
    await manager.broadcast("devices.bulk_deleted", {"count": count, "user_id": current_user.id})
    
    return {"message": f"{count} device{'s' if count != 1 else ''} deleted successfully"}


@router.post("/{device_id}/heartbeat", response_model=DeviceRead)
async def heartbeat(device_id: str, payload: DeviceHeartbeat, request: Request, db: Client = Depends(get_firestore)):
    ref = db.collection("devices").document(device_id)
    if not ref.get().exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")

    now = datetime.now(timezone.utc)
    existing = ref.get().to_dict() or {}
    current_status = (existing.get("status") or "").lower()
    # Keep admin isolation until explicitly recovered via PUT /devices/{id}
    next_status = "isolated" if current_status == "isolated" else payload.status
    ip_address = payload.ip_address or existing.get("ip_address")
    existing_location = (existing.get("location") or "").strip()
    if payload.location and payload.location.strip():
        location = payload.location.strip()
    elif existing_location:
        location = existing_location
    else:
        location = resolve_device_location(
            ip_address=ip_address,
            request_ip=request.client.host if request.client else None,
        )

    ref.update(
        {
            "status": next_status,
            "cpu_usage": payload.cpu_usage,
            "ram_usage": payload.ram_usage,
            "last_seen": now,
            "updated_at": now,
            "location": location,
            **({"ip_address": ip_address} if ip_address else {}),
        }
    )

    device = DeviceDoc.from_firestore(device_id, ref.get().to_dict() or {})
    await manager.broadcast("device.heartbeat", {"id": device.id, "status": device.status})
    return _doc_to_read(device)
