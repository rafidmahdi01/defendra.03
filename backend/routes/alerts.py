from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from google.cloud.firestore import Client

from auth.dependencies import get_current_user
from database.firebase import get_firestore
from models.models import AlertDoc, UserDoc
from models.schemas import AlertCreate, AlertRead, AlertUpdate, MessageResponse
from services.access_scope import device_ids_for_user, is_admin_user
from websocket.manager import manager


router = APIRouter(prefix="/alerts", tags=["Alerts"])


def _doc_to_read(a: AlertDoc) -> AlertRead:
    return AlertRead(
        id=a.id,
        device_id=a.device_id,
        title=a.title,
        description=a.description,
        severity=a.severity,
        status=a.status,
        rule_name=a.rule_name,
        created_at=a.created_at,
        acknowledged_at=a.acknowledged_at,
        resolved_at=a.resolved_at,
    )


@router.get("", response_model=list[AlertRead])
def list_alerts(
    status_filter: str | None = Query(default=None, alias="status"),
    severity: str | None = None,
    limit: int = Query(default=100, le=500),
    db: Client = Depends(get_firestore),
    _: UserDoc = Depends(get_current_user),
):
    query = db.collection("alerts").order_by("created_at", direction="DESCENDING")
    if not is_admin_user(_):
        device_ids = device_ids_for_user(db, _)
        if not device_ids:
            return []
        query = query.where("device_id", "in", list(device_ids)[:10])
    if status_filter:
        query = query.where("status", "==", status_filter)
    if severity:
        query = query.where("severity", "==", severity)
    docs = list(query.limit(limit).stream())
    return [_doc_to_read(AlertDoc.from_firestore(d.id, d.to_dict())) for d in docs]


@router.post("", response_model=AlertRead, status_code=status.HTTP_201_CREATED)
async def create_alert(
    payload: AlertCreate,
    db: Client = Depends(get_firestore),
    _: UserDoc = Depends(get_current_user),
):
    now = datetime.now(timezone.utc)
    ref = db.collection("alerts").document()
    ref.set(
        {
            **payload.model_dump(),
            "created_at": now,
            "acknowledged_at": None,
            "resolved_at": None,
        }
    )
    alert = AlertDoc.from_firestore(ref.id, ref.get().to_dict())
    await manager.broadcast("alert.created", {"id": alert.id, "severity": alert.severity, "title": alert.title})
    return _doc_to_read(alert)


@router.put("/{alert_id}", response_model=AlertRead)
async def update_alert(
    alert_id: str,
    payload: AlertUpdate,
    db: Client = Depends(get_firestore),
    _: UserDoc = Depends(get_current_user),
):
    ref = db.collection("alerts").document(alert_id)
    if not ref.get().exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")

    if not is_admin_user(_):
        device_ids = device_ids_for_user(db, _)
        alert_device_id = (ref.get().to_dict() or {}).get("device_id")
        if not alert_device_id or alert_device_id not in device_ids:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to modify this alert")

    updates = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}
    now = datetime.now(timezone.utc)
    if payload.status == "acknowledged":
        updates["acknowledged_at"] = now
    if payload.status == "resolved":
        updates["resolved_at"] = now

    ref.update(updates)
    alert = AlertDoc.from_firestore(alert_id, ref.get().to_dict())
    await manager.broadcast("alert.updated", {"id": alert.id, "status": alert.status})
    return _doc_to_read(alert)


@router.delete("", response_model=MessageResponse)
async def clear_alerts(
    db: Client = Depends(get_firestore),
    _: UserDoc = Depends(get_current_user),
):
    """Delete all alerts (used by dashboard Clear All)."""
    deleted = 0
    batch = db.batch()
    batch_count = 0
    query = db.collection("alerts")
    if not is_admin_user(_):
        device_ids = device_ids_for_user(db, _)
        if not device_ids:
            return MessageResponse(message="Cleared 0 alert(s)")
        query = query.where("device_id", "in", list(device_ids)[:10])
    for doc in query.stream():
        batch.delete(doc.reference)
        batch_count += 1
        deleted += 1
        if batch_count >= 450:
            batch.commit()
            batch = db.batch()
            batch_count = 0
    if batch_count:
        batch.commit()
    await manager.broadcast("alerts.cleared", {"count": deleted})
    return MessageResponse(message=f"Cleared {deleted} alert(s)")
