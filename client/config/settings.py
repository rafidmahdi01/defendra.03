"""Central configuration loaded from environment / .env file."""

from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_CLIENT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_CLIENT_ROOT / ".env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(_CLIENT_ROOT / ".env"), extra="ignore")

    # Server
    server_url: str = Field(default="http://127.0.0.1:8000", alias="SERVER_URL")
    api_email: str = Field(default="", alias="API_EMAIL")
    api_password: str = Field(default="", alias="API_PASSWORD")
    api_token: str = Field(default="", alias="API_TOKEN")

    # Device identity
    device_name: str = Field(default="", alias="DEVICE_NAME")
    device_location: str = Field(default="", alias="DEVICE_LOCATION")
    agent_version: str = Field(default="2.0.0", alias="AGENT_VERSION")

    # Intervals (seconds)
    heartbeat_interval: int = Field(default=30, alias="HEARTBEAT_INTERVAL")
    behavior_interval: int = Field(default=15, alias="BEHAVIOR_INTERVAL")
    usb_poll_interval: int = Field(default=5, alias="USB_POLL_INTERVAL")
    email_scan_interval: int = Field(default=60, alias="EMAIL_SCAN_INTERVAL")
    command_poll_interval: int = Field(default=20, alias="COMMAND_POLL_INTERVAL")
    backup_interval: int = Field(default=3600, alias="BACKUP_INTERVAL")
    network_check_interval: int = Field(default=10, alias="NETWORK_CHECK_INTERVAL")

    # Paths (relative to client root)
    data_dir: Path = Field(default=_CLIENT_ROOT / "data")
    logs_dir: Path = Field(default=_CLIENT_ROOT / "logs")
    backup_dir: Path = Field(default=_CLIENT_ROOT / "backups")
    quarantine_dir: Path = Field(default=_CLIENT_ROOT / "quarantine")
    offline_queue_file: Path = Field(default=_CLIENT_ROOT / "data" / "offline_queue.json")
    device_id_file: Path = Field(default=_CLIENT_ROOT / "data" / "device_id.txt")

    # Feature toggles
    enable_popup_alerts: bool = Field(default=False, alias="ENABLE_POPUP_ALERTS")
    cpu_alert_threshold: float = Field(default=85.0, alias="CPU_ALERT_THRESHOLD")

    @property
    def api_base(self) -> str:
        return f"{self.server_url.rstrip('/')}/api"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    for path in (
        settings.data_dir,
        settings.logs_dir,
        settings.backup_dir,
        settings.quarantine_dir,
    ):
        path.mkdir(parents=True, exist_ok=True)
    return settings
