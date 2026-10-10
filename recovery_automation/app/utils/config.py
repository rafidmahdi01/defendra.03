"""
Central configuration for the Recovery & Automation module.

Loads settings from environment variables and optional `.env` file.
Does not depend on the main Defendra backend config.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Module root: recovery_automation/
MODULE_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Application settings with sensible defaults for local development."""

    model_config = SettingsConfigDict(
        env_file=(MODULE_ROOT / ".env", MODULE_ROOT.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Service
    recovery_host: str = Field(default="0.0.0.0", alias="RECOVERY_HOST")
    recovery_port: int = Field(default=8001, alias="RECOVERY_PORT")
    recovery_debug: bool = Field(default=False, alias="RECOVERY_DEBUG")

    # Defendra API integration
    defendra_api_url: str = Field(
        default="http://127.0.0.1:8000", alias="DEFENDRA_API_URL"
    )
    defendra_api_token: str = Field(default="", alias="DEFENDRA_API_TOKEN")
    defendra_api_email: str = Field(default="", alias="DEFENDRA_API_EMAIL")
    defendra_api_password: str = Field(default="", alias="DEFENDRA_API_PASSWORD")

    # Backup
    backup_root: str = Field(default="backups", alias="BACKUP_ROOT")
    backup_default_paths: str = Field(
        default="./data,./config", alias="BACKUP_DEFAULT_PATHS"
    )
    backup_schedule_enabled: bool = Field(
        default=False, alias="BACKUP_SCHEDULE_ENABLED"
    )
    backup_schedule_cron: str = Field(
        default="0 2 * * *", alias="BACKUP_SCHEDULE_CRON"
    )
    backup_retention_days: int = Field(default=30, alias="BACKUP_RETENTION_DAYS")

    # JWT (must match main Defendra API settings)
    jwt_secret_key: str = Field(default="your-secret-key-change-in-production", alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")

    # Firebase Cloud Storage
    firebase_service_account_json: str = Field(default="", alias="FIREBASE_SERVICE_ACCOUNT_JSON")
    firebase_storage_bucket: str = Field(default="", alias="FIREBASE_STORAGE_BUCKET")

    # AWS S3
    aws_access_key_id: str = Field(default="", alias="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: str = Field(default="", alias="AWS_SECRET_ACCESS_KEY")
    aws_region: str = Field(default="us-east-1", alias="AWS_REGION")
    s3_bucket: str = Field(default="", alias="S3_BUCKET")
    s3_prefix: str = Field(default="defendra-backups/", alias="S3_PREFIX")
    s3_upload_enabled: bool = Field(default=False, alias="S3_UPLOAD_ENABLED")

    # Rclone placeholder
    rclone_remote: str = Field(default="", alias="RCLONE_REMOTE")
    rclone_enabled: bool = Field(default=False, alias="RCLONE_ENABLED")

    # SMTP
    smtp_host: str = Field(default="", alias="SMTP_HOST")
    smtp_port: int = Field(default=587, alias="SMTP_PORT")
    smtp_user: str = Field(default="", alias="SMTP_USER")
    smtp_password: str = Field(default="", alias="SMTP_PASSWORD")
    smtp_from: str = Field(default="recovery@defendra.local", alias="SMTP_FROM")
    smtp_to: str = Field(default="", alias="SMTP_TO")
    smtp_use_tls: bool = Field(default=True, alias="SMTP_USE_TLS")

    # Telegram placeholder
    telegram_bot_token: str = Field(default="", alias="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str = Field(default="", alias="TELEGRAM_CHAT_ID")
    telegram_enabled: bool = Field(default=False, alias="TELEGRAM_ENABLED")

    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_file: str = Field(default="logs/app.log", alias="LOG_FILE")

    @property
    def backup_root_path(self) -> Path:
        root = Path(self.backup_root)
        return root if root.is_absolute() else MODULE_ROOT / root

    @property
    def log_file_path(self) -> Path:
        path = Path(self.log_file)
        return path if path.is_absolute() else MODULE_ROOT / path

    @property
    def default_backup_paths(self) -> list[str]:
        return [p.strip() for p in self.backup_default_paths.split(",") if p.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return cached settings singleton."""
    return Settings()
