from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from google.cloud.firestore import Client
from pydantic import BaseModel, Field

from auth.dependencies import get_current_user, require_admin
from database.firebase import get_firestore
from models.models import UserDoc


router = APIRouter(prefix="/whitelist", tags=["Whitelist"])


class WhitelistCreate(BaseModel):
    process: str = Field(min_length=1, max_length=100)
    note: str = Field(default="", max_length=200)


class WhitelistRead(BaseModel):
    id: str
    process: str
    note: str
    added_at: datetime
    added_by: str


@router.get("", response_model=list[WhitelistRead])
def list_whitelist(
    db: Client = Depends(get_firestore),
    _: UserDoc = Depends(require_admin),
):
    docs = list(db.collection("whitelist").order_by("added_at", direction="DESCENDING").stream())
    return [
        WhitelistRead(
            id=d.id,
            process=d.to_dict().get("process", ""),
            note=d.to_dict().get("note", ""),
            added_at=d.to_dict().get("added_at"),
            added_by=d.to_dict().get("added_by", ""),
        )
        for d in docs
    ]


@router.post("", response_model=WhitelistRead, status_code=status.HTTP_201_CREATED)
def add_to_whitelist(
    payload: WhitelistCreate,
    db: Client = Depends(get_firestore),
    user: UserDoc = Depends(require_admin),
):
    process = payload.process.strip().lower()
    existing = list(db.collection("whitelist").where("process", "==", process).limit(1).stream())
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Process already whitelisted")

    now = datetime.now(timezone.utc)
    ref = db.collection("whitelist").document()
    ref.set({"process": process, "note": payload.note, "added_at": now, "added_by": user.id})
    return WhitelistRead(id=ref.id, process=process, note=payload.note, added_at=now, added_by=user.id)


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_from_whitelist(
    entry_id: str,
    db: Client = Depends(get_firestore),
    _: UserDoc = Depends(require_admin),
):
    ref = db.collection("whitelist").document(entry_id)
    if not ref.get().exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")
    ref.delete()
