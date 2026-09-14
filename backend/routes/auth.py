from datetime import datetime, timezone
import base64
import hashlib
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, status
from google.cloud.firestore import Client
from cryptography.fernet import Fernet, InvalidToken

from auth.dependencies import get_current_user, get_optional_current_user, require_admin
from auth.security import create_access_token, hash_password, verify_password
from database.firebase import get_firestore
from models.models import UserDoc
from models.schemas import (
    EmailScannerSettingsRead,
    EmailScannerSettingsSecretRead,
    EmailScannerSettingsWrite,
    LoginRequest,
    MessageResponse,
    Token,
    UserActivitySummary,
    UserAdminRead,
    UserCreate,
    UserLoginEvent,
    UserLoginSnapshot,
    UserRead,
)
from services.audit_service import record_audit
from utils.config import get_settings
from utils.firestore_retry import firestore_call_with_retry
from websocket.manager import manager


router = APIRouter(prefix="/auth", tags=["Authentication"])
settings = get_settings()
_EMAIL_SETTINGS_FIELD = "email_scanner_settings"


def _normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def _session_is_active(user: UserDoc, now: datetime | None = None) -> bool:
    """Online if flagged and last login is within the JWT session window."""
    if not user.is_online or not user.last_login_at:
        return False
    now = now or datetime.now(timezone.utc)
    last = user.last_login_at
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    elapsed = (now - last).total_seconds()
    return elapsed < settings.access_token_expire_minutes * 60


def _user_to_read(user: UserDoc) -> UserRead:
    return UserRead(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
        last_login_ip=user.last_login_ip,
        is_online=_session_is_active(user),
    )


def _user_to_admin_read(user: UserDoc) -> UserAdminRead:
    return UserAdminRead(**_user_to_read(user).model_dump())


def _is_non_admin_user(user: UserDoc) -> bool:
    return (user.role or "").lower() != "admin"


def _email_settings_cipher() -> Fernet:
    secret = (settings.jwt_secret_key or "change-this-secret-before-production").encode("utf-8")
    digest = hashlib.sha256(secret).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def _email_settings_to_read(data: dict | None) -> EmailScannerSettingsRead:
    data = data or {}
    email_address = (data.get("email_address") or "").strip()
    password_enc = (data.get("email_password_enc") or "").strip()
    return EmailScannerSettingsRead(
        email_address=email_address or None,
        is_configured=bool(email_address and password_enc and "@" in email_address),
    )


def _email_settings_to_secret_read(data: dict | None) -> EmailScannerSettingsSecretRead:
    data = data or {}
    email_address = (data.get("email_address") or "").strip()
    password_enc = (data.get("email_password_enc") or "").strip()
    if not email_address or not password_enc:
        return EmailScannerSettingsSecretRead(email_address=email_address or None, is_configured=False, email_password=None)
    try:
        email_password = _email_settings_cipher().decrypt(password_enc.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError):
        email_password = None
    return EmailScannerSettingsSecretRead(
        email_address=email_address or None,
        is_configured=bool(email_address and email_password and "@" in email_address),
        email_password=email_password,
    )


def _save_email_scanner_settings_for_user(
    db: Client,
    user_id: str,
    email_address: str,
    email_password: str,
) -> EmailScannerSettingsRead:
    encrypted_password = _email_settings_cipher().encrypt(email_password.encode("utf-8")).decode("utf-8")
    now = datetime.now(timezone.utc)
    ref = db.collection("users").document(user_id)
    if not ref.get().exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    ref.update(
        {
            "email_scanner_address": email_address,
            "email_scanner_password_enc": encrypted_password,
            "updated_at": now,
        }
    )
    return _email_settings_to_read(
        {
            "email_address": email_address,
            "email_password_enc": encrypted_password,
        }
    )


@router.get("/user-activity", response_model=UserActivitySummary)
def get_user_activity(
    db: Client = Depends(get_firestore),
    _: UserDoc = Depends(require_admin),
):
    """
    Admin-only: login status and history for dashboard users (role=user).

    Admin accounts are excluded so regular users' activity is monitored without
    exposing administrator login details to this view.
    """
    docs = db.collection("users").stream()
    fleet_users = [
        u for u in (UserDoc.from_firestore(d.id, d.to_dict()) for d in docs) if _is_non_admin_user(u)
    ]
    fleet_users.sort(key=lambda u: u.full_name.lower())

    users_out = [
        UserLoginSnapshot(
            id=u.id,
            email=u.email,
            full_name=u.full_name,
            is_online=_session_is_active(u),
            last_login_at=u.last_login_at,
            last_login_ip=u.last_login_ip,
        )
        for u in fleet_users
    ]

    users_by_id = {u.id: u for u in fleet_users}
    login_events: list[UserLoginEvent] = []

    try:
        audit_docs = (
            db.collection("audit_logs")
            .order_by("created_at", direction="DESCENDING")
            .limit(50)
            .stream()
        )
    except Exception:
        audit_docs = db.collection("audit_logs").stream()

    for doc in audit_docs:
        data = doc.to_dict() or {}
        if data.get("action") != "auth.login":
            continue

        role = (data.get("user_role") or "").lower()
        user_id = data.get("user_id")

        if role == "admin":
            continue
        if not role and user_id:
            known = users_by_id.get(user_id)
            if known is None:
                snap = db.collection("users").document(user_id).get()
                if snap.exists and (snap.to_dict() or {}).get("role") == "admin":
                    continue

        created = data.get("created_at")
        if created is None:
            continue

        login_events.append(
            UserLoginEvent(
                user_id=user_id,
                email=data.get("user_email"),
                full_name=data.get("user_full_name"),
                ip_address=data.get("ip_address"),
                created_at=created,
            )
        )
        if len(login_events) >= 15:
            break

    return UserActivitySummary(users=users_out, login_events=login_events)


@router.get("/email-scanner-settings", response_model=EmailScannerSettingsRead)
def get_my_email_scanner_settings(current_user: UserDoc = Depends(get_current_user), db: Client = Depends(get_firestore)):
    snap = db.collection("users").document(current_user.id).get()
    if not snap.exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return _email_settings_to_read(snap.to_dict())


@router.get("/users/{user_id}/email-scanner-settings", response_model=EmailScannerSettingsRead)
def get_user_email_scanner_settings(
    user_id: str,
    db: Client = Depends(get_firestore),
    _: UserDoc = Depends(require_admin),
):
    snap = db.collection("users").document(user_id).get()
    if not snap.exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return _email_settings_to_read(snap.to_dict())


@router.get("/me/email-scanner-settings/secret", response_model=EmailScannerSettingsSecretRead)
def get_my_email_scanner_secret(
    current_user: UserDoc = Depends(get_current_user),
    db: Client = Depends(get_firestore),
):
    snap = db.collection("users").document(current_user.id).get()
    if not snap.exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return _email_settings_to_secret_read(snap.to_dict())


@router.post("/users/{user_id}/email-scanner-settings", response_model=EmailScannerSettingsRead)
def save_user_email_scanner_settings(
    user_id: str,
    payload: EmailScannerSettingsWrite,
    db: Client = Depends(get_firestore),
    _: UserDoc = Depends(require_admin),
):
    return _save_email_scanner_settings_for_user(db, user_id, payload.email_address.strip(), payload.email_password)


@router.get("/users", response_model=list[UserAdminRead])
def list_users(
    db: Client = Depends(get_firestore),
    _: UserDoc = Depends(require_admin),
):
    """Admin-only: all dashboard users with login / online status."""
    docs = db.collection("users").stream()
    users = [UserDoc.from_firestore(d.id, d.to_dict()) for d in docs]
    users.sort(key=lambda u: u.full_name.lower())
    return [_user_to_admin_read(u) for u in users]


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(
    payload: UserCreate,
    request: Request,
    db: Client = Depends(get_firestore),
    current_user: UserDoc | None = Depends(get_optional_current_user),
):
    """Public signup creates a user account. Only admins may assign the admin role."""
    email = _normalize_email(str(payload.email))
    existing = db.collection("users").where("email", "==", email).limit(1).get()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already registered")

    requested_role = (payload.role or "user").lower()
    if current_user and current_user.role == "admin" and requested_role in ("user", "admin"):
        role = requested_role
    else:
        role = "user"

    now = datetime.now(timezone.utc)
    ref = db.collection("users").document()
    ref.set(
        {
            "email": email,
            "full_name": payload.full_name,
            "hashed_password": hash_password(payload.password),
            "role": role,
            "is_active": True,
            "created_at": now,
            "updated_at": now,
            "last_login_at": None,
            "last_login_ip": None,
            "is_online": False,
        }
    )
    user = UserDoc.from_firestore(ref.id, ref.get().to_dict())
    record_audit(db, "user.register", user=user, request=request, resource_type="user", resource_id=user.id)
    return _user_to_read(user)


@router.post("/bootstrap-admin", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def bootstrap_admin(payload: UserCreate, db: Client = Depends(get_firestore)):
    has_users = list(db.collection("users").limit(1).stream())
    if has_users:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bootstrap is available only before users exist",
        )
    email = _normalize_email(str(payload.email))
    now = datetime.now(timezone.utc)
    ref = db.collection("users").document()
    ref.set(
        {
            "email": email,
            "full_name": payload.full_name,
            "hashed_password": hash_password(payload.password),
            "role": "admin",
            "is_active": True,
            "created_at": now,
            "updated_at": now,
            "last_login_at": None,
            "last_login_ip": None,
            "is_online": False,
        }
    )
    user = UserDoc.from_firestore(ref.id, ref.get().to_dict())
    return _user_to_read(user)


@router.post("/login", response_model=Token)
async def login(payload: LoginRequest, request: Request, db: Client = Depends(get_firestore)):
    email = _normalize_email(str(payload.email))
    docs = firestore_call_with_retry(
        lambda: list(db.collection("users").where("email", "==", email).limit(1).stream())
    )
    if not docs:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    snap = docs[0]
    user = UserDoc.from_firestore(snap.id, snap.to_dict())
    if not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    now = datetime.now(timezone.utc)
    ip_address = request.client.host if request.client else None
    snap.reference.update(
        {
            "last_login_at": now,
            "last_login_ip": ip_address,
            "is_online": True,
            "updated_at": now,
        }
    )
    user = UserDoc.from_firestore(
        snap.id,
        {
            **snap.to_dict(),
            "last_login_at": now,
            "last_login_ip": ip_address,
            "is_online": True,
            "updated_at": now,
        },
    )

    token = create_access_token(user.id, {"role": user.role})
    record_audit(db, "auth.login", user=user, request=request)
    await manager.broadcast(
        "user.login",
        {
            "user_id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "last_login_at": now.isoformat(),
            "last_login_ip": ip_address,
            "is_online": True,
        },
    )
    return {"access_token": token, "role": user.role, "user": _user_to_read(user)}


@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: Request,
    db: Client = Depends(get_firestore),
    current_user: UserDoc = Depends(get_current_user),
):
    now = datetime.now(timezone.utc)
    db.collection("users").document(current_user.id).update(
        {"is_online": False, "updated_at": now}
    )
    record_audit(db, "auth.logout", user=current_user, request=request)
    await manager.broadcast(
        "user.logout",
        {
            "user_id": current_user.id,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "is_online": False,
        },
    )
    return MessageResponse(message="Logged out")


@router.get("/me", response_model=UserRead)
def me(current_user: UserDoc = Depends(get_current_user)):
    return _user_to_read(current_user)
