from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class UserRole(str, Enum):
    admin = "admin"
    user = "user"


class DeviceStatus(str, Enum):
    online = "online"
    offline = "offline"
    isolated = "isolated"


class LogSeverity(str, Enum):
    info = "info"
    warning = "warning"
    error = "error"
    critical = "critical"


class AlertSeverity(str, Enum):
    low = "low"
    medium = "medium"
    critical = "critical"


class AlertStatus(str, Enum):
    open = "open"
    acknowledged = "acknowledged"
    resolved = "resolved"


class QueueStatus(str, Enum):
    pending = "pending"
    synced = "synced"
    failed = "failed"


# ---------------------------------------------------------------------------
# Plain dataclasses used as in-memory representations of Firestore documents
# ---------------------------------------------------------------------------

@dataclass
class UserDoc:
    id: str
    email: str
    full_name: str
    hashed_password: str
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_login_at: datetime | None = None
    last_login_ip: str | None = None
    is_online: bool = False

    @staticmethod
    def from_firestore(doc_id: str, data: dict) -> "UserDoc":
        return UserDoc(
            id=doc_id,
            email=data["email"],
            full_name=data["full_name"],
            hashed_password=data["hashed_password"],
            role=data.get("role", UserRole.user.value),
            is_active=data.get("is_active", True),
            created_at=_to_datetime(data.get("created_at")),
            updated_at=_to_datetime(data.get("updated_at")),
            last_login_at=_to_datetime(data.get("last_login_at")),
            last_login_ip=data.get("last_login_ip"),
            is_online=bool(data.get("is_online", False)),
        )


@dataclass
class DeviceDoc:
    id: str
    hostname: str
    ip_address: str
    mac_address: str | None
    os_name: str | None
    agent_version: str | None
    status: str
    cpu_usage: float
    ram_usage: float
    location: str | None
    last_seen: datetime | None
    created_at: datetime
    updated_at: datetime
    user_id: str | None = None
    user_email: str | None = None
    user_full_name: str | None = None

    @staticmethod
    def from_firestore(doc_id: str, data: dict) -> "DeviceDoc":
        return DeviceDoc(
            id=doc_id,
            hostname=data["hostname"],
            ip_address=data["ip_address"],
            mac_address=data.get("mac_address"),
            os_name=data.get("os_name"),
            agent_version=data.get("agent_version"),
            status=data.get("status", DeviceStatus.offline.value),
            cpu_usage=data.get("cpu_usage", 0.0),
            ram_usage=data.get("ram_usage", 0.0),
            location=data.get("location"),
            last_seen=_to_datetime(data.get("last_seen")),
            created_at=_to_datetime(data.get("created_at")),
            updated_at=_to_datetime(data.get("updated_at")),
            user_id=data.get("user_id"),
            user_email=data.get("user_email"),
            user_full_name=data.get("user_full_name"),
        )


@dataclass
class LogDoc:
    id: str
    device_id: str
    category: str
    severity: str
    source: str | None
    message: str
    raw_payload: dict[str, Any] | None
    created_at: datetime

    @staticmethod
    def from_firestore(doc_id: str, data: dict) -> "LogDoc":
        return LogDoc(
            id=doc_id,
            device_id=data["device_id"],
            category=data["category"],
            severity=data.get("severity", LogSeverity.info.value),
            source=data.get("source"),
            message=data["message"],
            raw_payload=data.get("raw_payload"),
            created_at=_to_datetime(data.get("created_at")),
        )


@dataclass
class AlertDoc:
    id: str
    device_id: str | None
    title: str
    description: str
    severity: str
    status: str
    rule_name: str | None
    created_at: datetime
    acknowledged_at: datetime | None
    resolved_at: datetime | None

    @staticmethod
    def from_firestore(doc_id: str, data: dict) -> "AlertDoc":
        return AlertDoc(
            id=doc_id,
            device_id=data.get("device_id"),
            title=data["title"],
            description=data["description"],
            severity=data.get("severity", AlertSeverity.low.value),
            status=data.get("status", AlertStatus.open.value),
            rule_name=data.get("rule_name"),
            created_at=_to_datetime(data.get("created_at")),
            acknowledged_at=_to_datetime(data.get("acknowledged_at")),
            resolved_at=_to_datetime(data.get("resolved_at")),
        )


@dataclass
class QueueDoc:
    id: str
    device_id: str
    payload: dict
    status: str
    retry_count: int
    last_error: str | None
    created_at: datetime
    synced_at: datetime | None

    @staticmethod
    def from_firestore(doc_id: str, data: dict) -> "QueueDoc":
        return QueueDoc(
            id=doc_id,
            device_id=data["device_id"],
            payload=data.get("payload", {}),
            status=data.get("status", QueueStatus.pending.value),
            retry_count=data.get("retry_count", 0),
            last_error=data.get("last_error"),
            created_at=_to_datetime(data.get("created_at")),
            synced_at=_to_datetime(data.get("synced_at")),
        )


@dataclass
class AuditLogDoc:
    id: str
    user_id: str | None
    action: str
    resource_type: str | None
    resource_id: str | None
    ip_address: str | None
    user_agent: str | None
    created_at: datetime

    @staticmethod
    def from_firestore(doc_id: str, data: dict) -> "AuditLogDoc":
        return AuditLogDoc(
            id=doc_id,
            user_id=data.get("user_id"),
            action=data["action"],
            resource_type=data.get("resource_type"),
            resource_id=data.get("resource_id"),
            ip_address=data.get("ip_address"),
            user_agent=data.get("user_agent"),
            created_at=_to_datetime(data.get("created_at")),
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_datetime(value) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    # Firestore DatetimeWithNanoseconds is a datetime subclass — already handled above
    return value
