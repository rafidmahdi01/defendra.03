"""Compact Firestore snapshot for Sentinel AI system context."""

from google.cloud.firestore import Client

from models.models import UserDoc
from services.access_scope import device_ids_for_user, is_admin_user


def build_sentinel_context(db: Client, user: UserDoc | None = None) -> str:
    lines: list[str] = []
    user_is_admin = is_admin_user(user)
    user_device_ids = device_ids_for_user(db, user)

    try:
        if user_is_admin or user is None:
            dev_docs = list(db.collection("devices").limit(60).stream())
        else:
            dev_docs = [db.collection("devices").document(device_id).get() for device_id in sorted(user_device_ids)[:60]]
            dev_docs = [doc for doc in dev_docs if doc.exists]
        online = sum(1 for s in dev_docs if (s.to_dict() or {}).get("status") == "online")
        lines.append(f"Devices (sample): {len(dev_docs)} documents, ~{online} marked online.")
        for s in dev_docs[:15]:
            d = s.to_dict() or {}
            lines.append(
                f"  • id={s.id} hostname={d.get('hostname', '?')} status={d.get('status')} "
                f"ip={d.get('ip_address')} agent={d.get('agent_version')}"
            )
    except Exception as exc:
        lines.append(f"(Devices unavailable: {exc})")

    try:
        alert_query = db.collection("alerts").order_by("created_at", direction="DESCENDING")
        if not user_is_admin and user is not None:
            if user_device_ids:
                alert_query = alert_query.where("device_id", "in", list(user_device_ids)[:10])
            else:
                alert_query = alert_query.where("device_id", "==", "__none__")
        a_docs = list(alert_query.limit(15).stream())
        lines.append("Recent alerts:")
        for s in a_docs:
            d = s.to_dict() or {}
            desc = str(d.get("description") or "")[:200]
            lines.append(f"  • [{d.get('severity')}] {d.get('title')} — {desc}")
    except Exception as exc:
        lines.append(f"(Alerts unavailable: {exc})")

    try:
        log_query = db.collection("logs").order_by("created_at", direction="DESCENDING")
        if not user_is_admin and user is not None:
            if user_device_ids:
                log_query = log_query.where("device_id", "in", list(user_device_ids)[:10])
            else:
                log_query = log_query.where("device_id", "==", "__none__")
        l_docs = list(log_query.limit(20).stream())
        lines.append("Recent logs:")
        for s in l_docs:
            d = s.to_dict() or {}
            msg = str(d.get("message") or "")[:200]
            lines.append(
                f"  • device={d.get('device_id')} [{d.get('severity')}] {d.get('category')}: {msg}"
            )
    except Exception as exc:
        lines.append(f"(Logs unavailable: {exc})")

    return "\n".join(lines) if lines else "(No Firestore context available.)"
