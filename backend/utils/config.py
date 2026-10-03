from pathlib import Path
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve `.env` from the backend package root so Firebase/JWT load correctly even when
# uvicorn's cwd is not `backend/` (common when launching from IDEs or process managers).
_BACKEND_DIR = Path(__file__).resolve().parent.parent
_CLIENT_AGENT_ENV = _BACKEND_DIR.parent / "client_agent" / ".env"

_ENV_FILES: tuple[str, ...] = (
    str(_BACKEND_DIR / ".env"),
    *(
        (str(_CLIENT_AGENT_ENV.resolve()),)
        if _CLIENT_AGENT_ENV.is_file()
        else ()
    ),
)


class Settings(BaseSettings):
    app_name: str = "Defendra.AI"
    environment: str = "development"
    debug: bool = False

    # Firebase — use either a service account JSON **or** the local Firestore emulator.
    firebase_credentials_path: str = Field(
        default="",
        description="Absolute path to the Firebase service account JSON key file.",
    )
    firebase_credentials_json: str = Field(
        default="",
        description="Base64-encoded Firebase service account JSON (alternative to file path).",
    )
    firestore_emulator_host: str = Field(
        default="",
        description='Local emulator, e.g. "127.0.0.1:8080". Sets FIRESTORE_EMULATOR_HOST for firebase-admin.',
    )
    firebase_project_id: str = Field(
        default="defendraai",
        description="GCP project id (required for emulator; can match your Firebase project in production).",
    )

    @field_validator("firebase_credentials_path", mode="after")
    @classmethod
    def strip_cred_path(cls, v: str) -> str:
        if not v:
            return ""
        return v.strip().strip('"').strip("'")

    @field_validator("firestore_emulator_host", mode="after")
    @classmethod
    def strip_emulator_host(cls, v: str) -> str:
        if not v:
            return ""
        return v.strip().strip('"').strip("'")

    jwt_secret_key: str = "change-this-secret-before-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    heartbeat_timeout_seconds: int = 120
    log_export_limit: int = 10000

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    notification_from_email: str = "alerts@example.com"

    # Hugging Face Inference API — used by Sentinel chat in the dashboard
    huggingface_api_key: str = Field(
        default="", description="Access token from https://huggingface.co/settings/tokens."
    )
    huggingface_model: str = Field(
        default="Qwen/Qwen2.5-7B-Instruct",
        description="Hugging Face chat model id.",
    )
    huggingface_provider: str = Field(
        default="featherless-ai",
        description="Hugging Face Inference Provider for the selected model.",
    )
    huggingface_llm_enabled: bool = Field(
        default=True,
        description="If false or no token is configured, Sentinel uses the Firestore snapshot.",
    )

    model_config = SettingsConfigDict(
        env_file=_ENV_FILES,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


def get_settings() -> Settings:
    return Settings()
