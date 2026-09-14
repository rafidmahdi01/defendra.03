import csv
from datetime import datetime, timezone
from io import StringIO

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from google.cloud.firestore import Client

from auth.dependencies import get_current_user
from database.firebase import get_firestore
from models.models import LogDoc, UserDoc
from models.schemas import LogCreate, LogRead, MessageResponse
from services.alert_engine import generate_alert_from_log
from services.access_scope import device_ids_for_user, is_admin_user
from utils.config import get_settings
from websocket.manager import manager


router = APIRouter(prefix="/logs", tags=["Logs"])
settings = get_settings()


def _doc_to_read(log: LogDoc) -> LogRead:
    return LogRead(
        id=log.id,
        device_id=log.device_id,
        category=log.category,
        severity=log.severity,
        source=log.source,
        message=log.message,
        raw_payload=log.raw_payload,
        created_at=log.created_at,
    )


@router.post("", response_model=LogRead, status_code=status.HTTP_201_CREATED)
async def create_log(payload: LogCreate, db: Client = Depends(get_firestore)):
    if not db.collection("devices").document(payload.device_id).get().exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")

    now = datetime.now(timezone.utc)
    ref = db.collection("logs").document()
    ref.set({**payload.model_dump(), "created_at": now})
    log = LogDoc.from_firestore(ref.id, ref.get().to_dict())

    alert = generate_alert_from_log(db, log)
    await manager.broadcast("log.created", {"id": log.id, "device_id": log.device_id, "severity": log.severity})
    if alert:
        await manager.broadcast("alert.created", {"id": alert.id, "severity": alert.severity, "title": alert.title})
    return _doc_to_read(log)


@router.get("", response_model=list[LogRead])
def list_logs(
    device_id: str | None = None,
    severity: str | None = None,
    category: str | None = None,
    limit: int = Query(default=100, le=500),
    db: Client = Depends(get_firestore),
    _: UserDoc = Depends(get_current_user),
):
    query = db.collection("logs").order_by("created_at", direction="DESCENDING")
    if not is_admin_user(_):
        device_ids = device_ids_for_user(db, _)
        if not device_ids:
            return []
        query = query.where("device_id", "in", list(device_ids)[:10])
    if device_id:
        query = query.where("device_id", "==", device_id)
    if severity:
        query = query.where("severity", "==", severity)
    if category:
        query = query.where("category", "==", category)
    docs = list(query.limit(limit).stream())
    return [_doc_to_read(LogDoc.from_firestore(d.id, d.to_dict())) for d in docs]


@router.get("/search", response_model=list[LogRead])
def search_logs(
    q: str,
    limit: int = Query(default=100, le=500),
    db: Client = Depends(get_firestore),
    _: UserDoc = Depends(get_current_user),
):
    q_lower = q.lower()
    query = db.collection("logs").order_by("created_at", direction="DESCENDING")
    if not is_admin_user(_):
        device_ids = device_ids_for_user(db, _)
        if not device_ids:
            return []
        query = query.where("device_id", "in", list(device_ids)[:10])
    all_docs = query.limit(limit * 10).stream()
    results = []
    for d in all_docs:
        data = d.to_dict()
        if (
            q_lower in (data.get("message") or "").lower()
            or q_lower in (data.get("category") or "").lower()
            or q_lower in (data.get("source") or "").lower()
        ):
            results.append(_doc_to_read(LogDoc.from_firestore(d.id, data)))
            if len(results) >= limit:
                break
    return results


@router.get("/export")
def export_logs(db: Client = Depends(get_firestore), _: UserDoc = Depends(get_current_user)):
    query = db.collection("logs").order_by("created_at", direction="DESCENDING")
    if not is_admin_user(_):
        device_ids = device_ids_for_user(db, _)
        if not device_ids:
            docs = []
        else:
            docs = query.where("device_id", "in", list(device_ids)[:10]).limit(settings.log_export_limit).stream()
    else:
        docs = query.limit(settings.log_export_limit).stream()
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["id", "device_id", "category", "severity", "source", "message", "created_at"])
    for d in docs:
        data = d.to_dict()
        writer.writerow(
            [
                d.id,
                data.get("device_id"),
                data.get("category"),
                data.get("severity"),
                data.get("source"),
                data.get("message"),
                data.get("created_at"),
            ]
        )
    return Response(
        buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=security-logs.csv"},
    )


@router.delete("", response_model=MessageResponse)
async def clear_logs(
    db: Client = Depends(get_firestore),
    _: UserDoc = Depends(get_current_user),
):
    """Delete all security logs (used by dashboard Clear All)."""
    deleted = 0
    batch = db.batch()
    batch_count = 0
    query = db.collection("logs")
    if not is_admin_user(_):
        device_ids = device_ids_for_user(db, _)
        if not device_ids:
            return MessageResponse(message="Cleared 0 log(s)")
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
    await manager.broadcast("logs.cleared", {"count": deleted})
    return MessageResponse(message=f"Cleared {deleted} log(s)")
