"""Pydantic request/response models for Recovery & Automation APIs."""

from typing import Any

from pydantic import BaseModel, Field


class BackupCreateRequest(BaseModel):
    paths: list[str] | None = Field(
        default=None,
        description="Paths to include in backup (defaults from env)",
    )
    label: str | None = Field(default="manual", description="Human-readable backup label")
    device_id: str | None = Field(default=None, description="Associated device id")
    user_email: str | None = Field(default=None, description="Email of user creating backup")


class BackupRestoreRequest(BaseModel):
    backup_id: str | None = Field(
        default=None,
        description="Backup to restore; omit for latest",
    )
    target_dir: str | None = Field(
        default=None,
        description="Restore destination directory",
    )


class ThreatDetectedRequest(BaseModel):
    device_id: str = Field(..., examples=["PC-01"])
    threat_type: str = Field(..., examples=["ransomware"])
    severity: str = Field(default="critical", examples=["critical"])
    enable_limp_mode: bool = Field(
        default=False,
        description="Force limp mode even if severity is not critical",
    )


class NotificationRequest(BaseModel):
    subject: str
    message: str
    channels: list[str] | None = Field(
        default=None,
        description="console, email, telegram",
    )
    metadata: dict[str, Any] | None = None


class EmergencyRecoveryRequest(BaseModel):
    device_id: str
    create_snapshot: bool = True


class IsolationRequest(BaseModel):
    device_id: str
    reason: str = "manual"
    block_network: bool = True
    quarantine: bool = True


class ScheduleConfigRequest(BaseModel):
    enabled: bool = Field(..., description="Enable or disable the auto-backup schedule")
    interval_minutes: int = Field(
        default=60,
        ge=1,
        description="How often to run a backup (minimum 1 minute)",
    )
    paths: list[str] | None = Field(
        default=None,
        description="Paths to include; omit to use server defaults",
    )
    label: str | None = Field(default="scheduled", description="Label for scheduled backups")


class MessageResponse(BaseModel):
    message: str
    data: dict[str, Any] | None = None
