from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from google.cloud.firestore import Client

from database.firebase import get_firestore
from models.models import LogDoc
from models.schemas import MessageResponse, OfflineSyncRequest
from services.alert_engine import generate_alert_from_log
from websocket.manager import manager


router = APIRouter(prefix="/sync", tags=["Connectivity"])


@router.post("/offline-logs", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def sync_offline_logs(payload: OfflineSyncRequest, db: Client = Depends(get_firestore)):
    if not db.collection("devices").document(payload.device_id).get().exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")

    now = datetime.now(timezone.utc)
    synced = 0

    for item in payload.logs:
        queue_ref = db.collection("connectivity_queue").document()
        queue_ref.set(
            {
                "device_id": payload.device_id,
                "payload": item.model_dump(mode="json"),
                "status": "pending",
                "retry_count": 0,
                "last_error": None,
                "created_at": now,
                "synced_at": None,
            }
        )
        try:
            log_data = {**item.model_dump(exclude={"queued_at"}), "created_at": now}
            log_ref = db.collection("logs").document()
            log_ref.set(log_data)
            log = LogDoc.from_firestore(log_ref.id, log_ref.get().to_dict())
            generate_alert_from_log(db, log)
            queue_ref.update({"status": "synced", "synced_at": now})
            synced += 1
        except Exception as exc:
            existing = queue_ref.get().to_dict() or {}
            queue_ref.update(
                {
                    "status": "failed",
                    "retry_count": existing.get("retry_count", 0) + 1,
                    "last_error": str(exc),
                }
            )

    db.collection("devices").document(payload.device_id).update(
        {"status": "online", "last_seen": now, "updated_at": now}
    )
    await manager.broadcast("sync.completed", {"device_id": payload.device_id, "synced": synced})
    return {"message": f"Synced {synced} offline log entries"}
