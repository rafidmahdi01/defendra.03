from datetime import datetime, timedelta, timezone

from google.cloud.firestore import Client

from utils.config import get_settings


settings = get_settings()


def mark_stale_devices_offline(db: Client) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=settings.heartbeat_timeout_seconds)
    stale_docs = list(
        db.collection("devices")
        .where("status", "==", "online")
        .where("last_seen", "<", cutoff)
        .stream()
    )
    for doc in stale_docs:
        doc.reference.update({"status": "offline", "updated_at": datetime.now(timezone.utc)})
    return len(stale_docs)
