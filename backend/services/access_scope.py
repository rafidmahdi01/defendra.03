from __future__ import annotations

from google.cloud.firestore import Client

from models.models import UserDoc


def is_admin_user(user: UserDoc | None) -> bool:
    return bool(user and (user.role or "").lower() == "admin")


def device_ids_for_user(db: Client, user: UserDoc | None) -> set[str]:
    if is_admin_user(user):
        return set()
    if user is None:
        return set()
    docs = db.collection("devices").where("user_id", "==", user.id).stream()
    return {doc.id for doc in docs}


def device_docs_for_user(db: Client, user: UserDoc | None) -> list[dict]:
    if is_admin_user(user):
        return [doc.to_dict() or {} for doc in db.collection("devices").stream()]
    if user is None:
        return []
    return [
        doc.to_dict() or {}
        for doc in db.collection("devices").where("user_id", "==", user.id).stream()
    ]