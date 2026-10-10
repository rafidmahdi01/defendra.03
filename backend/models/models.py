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
    # Isolation fields
    isolated_at: datetime | None = None
    isolated_by_user_id: str | None = None
    isolated_by_email: str | None = None
    isolation_reason: str | None = None
    isolation_type: str | None = None
    isolation_grace_period: int | None = None
    can_auto_recover: bool = False
    recovered_at: datetime | None = None
    recovered_by_user_id: str | None = None
    recovered_by_email: str | None = None

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
            # Isolation fields
            isolated_at=_to_datetime(data.get("isolated_at")),
            isolated_by_user_id=data.get("isolated_by_user_id"),
            isolated_by_email=data.get("isolated_by_email"),
            isolation_reason=data.get("isolation_reason"),
            isolation_type=data.get("isolation_type"),
            isolation_grace_period=data.get("isolation_grace_period"),
            can_auto_recover=bool(data.get("can_auto_recover", False)),
            recovered_at=_to_datetime(data.get("recovered_at")),
            recovered_by_user_id=data.get("recovered_by_user_id"),
            recovered_by_email=data.get("recovered_by_email"),
        )


@dataclass
class LogDoc:
    id: str
    device_id: str | None
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
            device_id=data.get("device_id"),
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


@dataclass
class DeviceSwitchRequestDoc:
    id: str
    user_id: str
    user_email: str
    user_full_name: str
    old_device_id: str
    old_hostname: str
    new_hostname: str
    new_platform: str | None
    new_ip_address: str | None
    status: str  # pending, approved, rejected
    requested_at: datetime
    reviewed_at: datetime | None = None
    reviewed_by_user_id: str | None = None
    reviewed_by_email: str | None = None
    rejection_reason: str | None = None

    @staticmethod
    def from_firestore(doc_id: str, data: dict) -> "DeviceSwitchRequestDoc":
        return DeviceSwitchRequestDoc(
            id=doc_id,
            user_id=data["user_id"],
            user_email=data["user_email"],
            user_full_name=data["user_full_name"],
            old_device_id=data["old_device_id"],
            old_hostname=data["old_hostname"],
            new_hostname=data["new_hostname"],
            new_platform=data.get("new_platform"),
            new_ip_address=data.get("new_ip_address"),
            status=data.get("status", "pending"),
            requested_at=_to_datetime(data.get("requested_at")),
            reviewed_at=_to_datetime(data.get("reviewed_at")),
            reviewed_by_user_id=data.get("reviewed_by_user_id"),
            reviewed_by_email=data.get("reviewed_by_email"),
            rejection_reason=data.get("rejection_reason"),
        )


@dataclass
class IsolationAuditDoc:
    id: str
    event: str  # device.isolated or device.recovered
    device_id: str
    device_hostname: str
    device_user_id: str
    device_user_email: str
    action_by_user_id: str
    action_by_email: str
    isolation_type: str | None = None  # network_only or full_shutdown
    grace_period_seconds: int | None = None
    reason: str | None = None
    timestamp: datetime | None = None

    @staticmethod
    def from_firestore(doc_id: str, data: dict) -> "IsolationAuditDoc":
        return IsolationAuditDoc(
            id=doc_id,
            event=data["event"],
            device_id=data["device_id"],
            device_hostname=data["device_hostname"],
            device_user_id=data["device_user_id"],
            device_user_email=data["device_user_email"],
            action_by_user_id=data["action_by_user_id"],
            action_by_email=data["action_by_email"],
            isolation_type=data.get("isolation_type"),
            grace_period_seconds=data.get("grace_period_seconds"),
            reason=data.get("reason"),
            timestamp=_to_datetime(data.get("timestamp")),
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
