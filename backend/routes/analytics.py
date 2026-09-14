from fastapi import APIRouter, Depends, Query
from google.cloud.firestore import Client

from auth.dependencies import get_current_user
from database.firebase import get_firestore
from models.models import UserDoc
from models.schemas import OverviewStats, TrendPoint
from services.access_scope import device_ids_for_user, is_admin_user
from services.analytics_service import get_overview, get_trends


router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/overview", response_model=OverviewStats)
def overview(db: Client = Depends(get_firestore), current_user: UserDoc = Depends(get_current_user)):
    return get_overview(db, current_user)


@router.get("/trends", response_model=list[TrendPoint])
def trends(
    days: int = Query(default=7, ge=1, le=30),
    db: Client = Depends(get_firestore),
    current_user: UserDoc = Depends(get_current_user),
):
    return get_trends(db, days, current_user)


@router.get("/dashboard")
def dashboard_snapshot(db: Client = Depends(get_firestore), current_user: UserDoc = Depends(get_current_user)):
    if is_admin_user(current_user):
        recent_logs = [
            d.to_dict() | {"id": d.id}
            for d in db.collection("logs").order_by("created_at", direction="DESCENDING").limit(8).stream()
        ]
        recent_alerts = [
            d.to_dict() | {"id": d.id}
            for d in db.collection("alerts").order_by("created_at", direction="DESCENDING").limit(8).stream()
        ]
        device_docs = db.collection("devices").order_by("hostname").limit(20).stream()
    else:
        device_ids = device_ids_for_user(db, current_user)
        if device_ids:
            recent_logs = [
                d.to_dict() | {"id": d.id}
                for d in db.collection("logs")
                .where("device_id", "in", list(device_ids)[:10])
                .order_by("created_at", direction="DESCENDING")
                .limit(8)
                .stream()
            ]
            recent_alerts = [
                d.to_dict() | {"id": d.id}
                for d in db.collection("alerts")
                .where("device_id", "in", list(device_ids)[:10])
                .order_by("created_at", direction="DESCENDING")
                .limit(8)
                .stream()
            ]
        else:
            recent_logs = []
            recent_alerts = []
        device_docs = (
            db.collection("devices")
            .where("user_id", "==", current_user.id)
            .limit(20)
            .stream()
        )
    devices = [d.to_dict() | {"id": d.id} for d in device_docs]
    return {
        "overview": get_overview(db, current_user),
        "trends": get_trends(db, 7, current_user),
        "recent_logs": recent_logs,
        "recent_alerts": recent_alerts,
        "devices": devices,
    }
