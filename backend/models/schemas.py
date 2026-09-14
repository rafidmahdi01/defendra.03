from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=150)


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)
    role: str = "user"


class UserRead(UserBase):
    id: str
    role: str
    is_active: bool
    created_at: datetime
    last_login_at: datetime | None = None
    last_login_ip: str | None = None
    is_online: bool = False

    model_config = {"from_attributes": True}


class UserAdminRead(UserRead):
    """Admin view of fleet users including live login status."""


class UserLoginSnapshot(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    is_online: bool = False
    last_login_at: datetime | None = None
    last_login_ip: str | None = None


class UserLoginEvent(BaseModel):
    user_id: str | None = None
    email: str | None = None
    full_name: str | None = None
    ip_address: str | None = None
    created_at: datetime


class UserActivitySummary(BaseModel):
    """Admin-only view of non-admin user logins and fleet activity."""

    users: list[UserLoginSnapshot]
    login_events: list[UserLoginEvent]


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user: UserRead


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class EmailScannerSettingsRead(BaseModel):
    email_address: str | None = None
    is_configured: bool = False


class EmailScannerSettingsSecretRead(EmailScannerSettingsRead):
    email_password: str | None = None


class EmailScannerSettingsWrite(BaseModel):
    email_address: EmailStr
    email_password: str = Field(min_length=1, max_length=256)


class WorkstationLinkRequest(BaseModel):
    hostname: str = Field(min_length=1, max_length=200)
    platform: str | None = None
    os_name: str | None = None
    agent_version: str | None = None
    ip_address: str | None = None
    location: str | None = None


class DeviceCreate(BaseModel):
    hostname: str
    ip_address: str
    mac_address: str | None = None
    os_name: str | None = None
    agent_version: str | None = None
    location: str | None = None


class DeviceUpdate(BaseModel):
    hostname: str | None = None
    ip_address: str | None = None
    mac_address: str | None = None
    os_name: str | None = None
    agent_version: str | None = None
    location: str | None = None
    status: str | None = None
    cpu_usage: float | None = Field(default=None, ge=0, le=100)
    ram_usage: float | None = Field(default=None, ge=0, le=100)


class DeviceHeartbeat(BaseModel):
    cpu_usage: float = Field(default=0, ge=0, le=100)
    ram_usage: float = Field(default=0, ge=0, le=100)
    status: str = "online"
    ip_address: str | None = None
    location: str | None = None


class DeviceRead(DeviceCreate):
    id: str
    status: str
    cpu_usage: float
    ram_usage: float
    last_seen: datetime | None
    created_at: datetime
    user_id: str | None = None
    user_email: str | None = None
    user_full_name: str | None = None
    user_name: str | None = None

    model_config = {"from_attributes": True}


class LogCreate(BaseModel):
    device_id: str
    category: str
    severity: str = "info"
    source: str | None = None
    message: str
    raw_payload: dict[str, Any] | None = None


class LogRead(LogCreate):
    id: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AlertCreate(BaseModel):
    device_id: str | None = None
    title: str
    description: str
    severity: str = "low"
    status: str = "open"
    rule_name: str | None = None


class AlertUpdate(BaseModel):
    status: str | None = None
    severity: str | None = None
    title: str | None = None
    description: str | None = None


class AlertRead(AlertCreate):
    id: str
    created_at: datetime
    acknowledged_at: datetime | None
    resolved_at: datetime | None

    model_config = {"from_attributes": True}


class OfflineSyncItem(LogCreate):
    queued_at: datetime | None = None


class OfflineSyncRequest(BaseModel):
    device_id: str
    logs: list[OfflineSyncItem]


class OverviewStats(BaseModel):
    total_devices: int
    active_devices: int
    offline_devices: int
    critical_alerts: int
    logs_today: int
    pending_queue: int


class TrendPoint(BaseModel):
    label: str
    logs: int
    alerts: int
    critical: int


class MessageResponse(BaseModel):
    message: str


class SentinelChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=12000)
