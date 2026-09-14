from datetime import date, datetime, timedelta, timezone

from google.cloud.firestore import Client

from models.models import UserDoc
from services.access_scope import device_docs_for_user, device_ids_for_user, is_admin_user


def _device_docs_for_user(db: Client, user: UserDoc | None) -> list[dict]:
    return device_docs_for_user(db, user)


def _logs_query_for_user(db: Client, user: UserDoc | None):
    query = db.collection("logs")
    if is_admin_user(user):
        return query
    device_ids = device_ids_for_user(db, user)
    if not device_ids:
        return query.where("device_id", "==", "__none__")
    return query.where("device_id", "in", list(device_ids)[:10])


def _alerts_query_for_user(db: Client, user: UserDoc | None):
    query = db.collection("alerts")
    if is_admin_user(user):
        return query
    device_ids = device_ids_for_user(db, user)
    if not device_ids:
        return query.where("device_id", "==", "__none__")
    return query.where("device_id", "in", list(device_ids)[:10])


def get_overview(db: Client, user: UserDoc | None = None) -> dict:
    today_start = datetime.combine(date.today(), datetime.min.time()).replace(tzinfo=timezone.utc)

    device_rows = _device_docs_for_user(db, user)
    total_devices = len(device_rows)
    active_devices = sum(1 for row in device_rows if row.get("status") == "online")
    offline_devices = sum(1 for row in device_rows if row.get("status") == "offline")
    
    try:
        alert_query = _alerts_query_for_user(db, user).where("status", "==", "open").where("severity", "==", "critical")
        critical_alerts = len(list(alert_query.stream()))
    except Exception:
        critical_alerts = 0
    
    try:
        logs_today = len(list(_logs_query_for_user(db, user).where("created_at", ">=", today_start).stream()))
    except Exception:
        logs_today = 0
    
    try:
        pending_queue = len(list(db.collection("connectivity_queue").where("status", "==", "pending").stream()))
    except Exception:
        pending_queue = 0

    return {
        "total_devices": total_devices,
        "active_devices": active_devices,
        "offline_devices": offline_devices,
        "critical_alerts": critical_alerts,
        "logs_today": logs_today,
        "pending_queue": pending_queue,
    }


def get_trends(db: Client, days: int = 7, user: UserDoc | None = None) -> list[dict]:
    start = datetime.now(timezone.utc) - timedelta(days=days - 1)
    rows = []
    for offset in range(days):
        day_start = datetime.combine(
            (start + timedelta(days=offset)).date(), datetime.min.time()
        ).replace(tzinfo=timezone.utc)
        day_end = day_start + timedelta(days=1)

        try:
            logs_count = len(
                list(
                    _logs_query_for_user(db, user)
                    .where("created_at", ">=", day_start)
                    .where("created_at", "<", day_end)
                    .stream()
                )
            )
        except Exception:
            logs_count = 0

        try:
            alerts_count = len(
                list(
                    _alerts_query_for_user(db, user)
                    .where("created_at", ">=", day_start)
                    .where("created_at", "<", day_end)
                    .stream()
                )
            )
        except Exception:
            alerts_count = 0

        try:
            critical_count = len(
                list(
                    _alerts_query_for_user(db, user)
                    .where("created_at", ">=", day_start)
                    .where("created_at", "<", day_end)
                    .where("severity", "==", "critical")
                    .stream()
                )
            )
        except Exception:
            critical_count = 0

        rows.append(
            {
                "label": day_start.strftime("%b %d"),
                "logs": logs_count,
                "alerts": alerts_count,
                "critical": critical_count,
            }
        )
    return rows
